/**
 * KAOS Sync Client — outbound queue + retry for the KAOS Trading Bot extension.
 *
 * Purpose: reliably ship trade-lifecycle events (signal → order attempt → broker confirmed →
 * result / failed) to the KAOS cloud at `POST /api/v1/trading/events` WITHOUT ever placing a
 * broker order. This is a telemetry / cloud-sync channel only.
 *
 * Guarantees:
 *  - Durable queue persisted in chrome.storage.local, so it survives MV3 service-worker suspension.
 *  - Idempotent: every event carries a stable `eventId`; the server dedupes, and a lost ACK simply
 *    causes a safe retry. Trades are NEVER duplicated on the member dashboard.
 *  - Graceful API downtime: network errors / 5xx trigger capped exponential backoff with jitter.
 *  - Auth-aware: a 401 invokes the refresh hook once; if refresh fails the batch stays queued.
 *
 * This is a classic (non-module) script so it can run inside the existing MV3 service worker via
 * `importScripts('kaos-sync-client.js')`. It also exports for Node unit testing.
 */
(function (root) {
  'use strict';

  var QUEUE_KEY = 'kaos_sync_queue_v1';

  function defaultStorage() {
    // chrome.storage.local wrapper (async). Falls back to an in-memory map off-extension.
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      return {
        get: function (key) {
          return new Promise(function (resolve) {
            chrome.storage.local.get([key], function (r) { resolve(r[key]); });
          });
        },
        set: function (key, val) {
          return new Promise(function (resolve) {
            chrome.storage.local.set(Object.fromEntries([[key, val]]), function () { resolve(); });
          });
        }
      };
    }
    var mem = {};
    return {
      get: function (key) { return Promise.resolve(mem[key]); },
      set: function (key, val) { mem[key] = val; return Promise.resolve(); }
    };
  }

  function uuid() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 'evt-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  }

  function createKaosSyncClient(opts) {
    opts = opts || {};
    var apiBase = (opts.apiBase || '').replace(/\/+$/, '');            // e.g. https://host/api/v1
    var getAuth = opts.getAuth || function () { return Promise.resolve({}); };
    var onAuthExpired = opts.onAuthExpired || function () { return Promise.resolve(null); };
    var storage = opts.storage || defaultStorage();
    var fetchImpl = opts.fetchImpl || (typeof fetch !== 'undefined' ? fetch.bind(root) : null);
    var now = opts.now || function () { return Date.now(); };
    var batchSize = opts.batchSize || 25;
    var maxQueue = opts.maxQueue || 1000;
    var baseBackoffMs = opts.baseBackoffMs || 1000;
    var maxBackoffMs = opts.maxBackoffMs || 60000;
    var scheduleRetry = opts.scheduleRetry || function (ms, fn) { return setTimeout(fn, ms); };
    var autoFlush = opts.autoFlush !== false;

    var queue = [];
    var loaded = false;
    var flushing = false;
    var attempt = 0;
    var pendingRetry = false;

    async function load() {
      if (loaded) return;
      var stored = await storage.get(QUEUE_KEY);
      queue = Array.isArray(stored) ? stored : [];
      loaded = true;
    }

    async function persist() {
      await storage.set(QUEUE_KEY, queue);
    }

    function backoffMs() {
      var raw = Math.min(maxBackoffMs, baseBackoffMs * Math.pow(2, attempt));
      return Math.round(raw / 2 + Math.random() * (raw / 2)); // full-ish jitter
    }

    async function enqueue(evt) {
      await load();
      var e = {
        eventId: evt.eventId || (evt.tradeId && evt.type ? evt.tradeId + ':' + evt.type : uuid()),
        type: evt.type,
        signalId: evt.signalId || null,
        tradeId: evt.tradeId || null,
        payload: evt.payload || {},
        timestamp: evt.timestamp || new Date(now()).toISOString()
      };
      // local guard against re-queuing an identical eventId still pending.
      if (!queue.some(function (q) { return q.eventId === e.eventId; })) {
        queue.push(e);
        if (queue.length > maxQueue) queue = queue.slice(queue.length - maxQueue); // drop oldest
        await persist();
      }
      if (autoFlush) flush();
      return e.eventId;
    }

    // Convenience: a broker-CONFIRMED trade is the one that must reach the dashboard.
    function enqueueTradeConfirmed(trade) {
      return enqueue({ type: 'BROKER_CONFIRMED', tradeId: trade.tradeId || trade.id,
                       signalId: trade.signalId, payload: trade });
    }

    async function _post(events) {
      var auth = (await getAuth()) || {};
      var headers = { 'Content-Type': 'application/json' };
      if (auth.accessToken) headers['Authorization'] = 'Bearer ' + auth.accessToken;
      if (auth.deviceId) headers['X-Device-Id'] = auth.deviceId;
      return fetchImpl(apiBase + '/trading/events', {
        method: 'POST', headers: headers, body: JSON.stringify({ events: events })
      });
    }

    function scheduleFlushRetry() {
      if (pendingRetry) return;
      pendingRetry = true;
      var wait = backoffMs();
      scheduleRetry(wait, function () { pendingRetry = false; flush(); });
    }

    async function flush() {
      await load();
      if (flushing || queue.length === 0 || !fetchImpl) return { skipped: true };
      flushing = true;
      try {
        var batch = queue.slice(0, batchSize);
        var res;
        try {
          res = await _post(batch);
        } catch (netErr) {
          attempt++;
          scheduleFlushRetry();               // offline / DNS / connection refused → retry later
          return { error: 'network', queued: queue.length };
        }

        if (res.status === 401) {
          var fresh = await onAuthExpired();   // try a single token refresh
          if (!fresh) { attempt++; scheduleFlushRetry(); return { error: 'unauthorized', queued: queue.length }; }
          attempt = 0; flushing = false; return flush(); // retry immediately with new token
        }
        if (res.status >= 500 || res.status === 429) {
          attempt++;
          scheduleFlushRetry();
          return { error: 'server_' + res.status, queued: queue.length };
        }
        if (!res.ok) {
          // 4xx (e.g. 403 not authorized / 422 bad body): drop this batch to avoid a poison-pill loop.
          var idsBad = batch.map(function (e) { return e.eventId; });
          queue = queue.filter(function (e) { return idsBad.indexOf(e.eventId) === -1; });
          await persist();
          attempt = 0;
          return { error: 'client_' + res.status, dropped: idsBad.length, queued: queue.length };
        }

        var body = await res.json();
        var settled = {};
        (body.acked || []).forEach(function (id) { settled[id] = 1; });
        (body.duplicates || []).forEach(function (id) { settled[id] = 1; });
        queue = queue.filter(function (e) { return !settled[e.eventId]; });
        await persist();
        attempt = 0;
        flushing = false;
        if (queue.length > 0) return flush(); // drain remaining batches
        return { ok: true, acked: (body.acked || []).length, duplicates: (body.duplicates || []).length };
      } finally {
        flushing = false;
      }
    }

    async function size() { await load(); return queue.length; }
    async function clear() { queue = []; await persist(); }

    return {
      enqueue: enqueue,
      enqueueTradeConfirmed: enqueueTradeConfirmed,
      flush: flush,
      size: size,
      clear: clear,
      _peek: function () { return queue.slice(); }
    };
  }

  var api = { createKaosSyncClient: createKaosSyncClient };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; // Node
  if (root) root.KaosSyncClient = api;                                       // service worker / window
})(typeof self !== 'undefined' ? self : this);
