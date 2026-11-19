/**
 * KAOS Learning Client — emits the 104-feature vector + settled outcome of each trade to the
 * KAOS Collective Learning pipeline (`POST /api/v1/ai/learning-samples`) so the server can train
 * real, deployable KAOS AI models on production data.
 *
 * Privacy & rules:
 *  - Sends ONLY market/trade features + outcome. Never name, email, credentials, balances or PII.
 *  - Service learning is mandatory and disclosed; no optional collection switch is presented.
 *  - Idempotent via a stable `sampleId`; the server dedupes so retries never double-count.
 *  - Fire-and-forget with a single retry; a durable queue is intentionally omitted because learning
 *    samples are best-effort telemetry, not orders.
 *
 * Feature vector: the extension already computes the canonical 104-length vector for on-device
 * inference — pass it straight through as `features.x`. The trainer masks disabled features itself.
 */
(function (root) {
  'use strict';

  function uuid() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 's-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  }

  function createKaosLearningClient(opts) {
    opts = opts || {};
    var apiBase = (opts.apiBase || '').replace(/\/+$/, '');   // e.g. https://host/api/v1
    var getAuth = opts.getAuth || function () { return Promise.resolve({}); };
    var hasConsent = function () { return Promise.resolve(true); }; // Required service learning, disclosed in Privacy.
    var fetchImpl = opts.fetchImpl || (typeof fetch !== 'undefined' ? fetch.bind(root) : null);
    var botVersion = opts.botVersion || null;

    async function _post(sample) {
      var auth = (await getAuth()) || {};
      var headers = { 'Content-Type': 'application/json' };
      if (auth.accessToken) headers['Authorization'] = 'Bearer ' + auth.accessToken;
      if (auth.deviceId) headers['X-Device-Id'] = auth.deviceId;
      return fetchImpl(apiBase + '/ai/learning-samples', {
        method: 'POST', headers: headers, body: JSON.stringify(sample)
      });
    }

    /**
     * Emit one learning sample for a settled trade.
     * @param {object} t - {sampleType:'REAL'|'PAPER', platform, asset, assetClass?, timeframe,
     *   expiration, strategy?, strategyVersion?, direction, aiPrediction?, aiConfidence?,
     *   aiModelVersion?, entryPrice?, settlementPrice?, outcome:'WIN'|'LOSS'|'TIE',
     *   featureVector:number[104], sampleId? }
     */
    async function emit(t) {
      if (!fetchImpl) return { skipped: 'no_fetch' };
      try { if (!(await hasConsent())) return { skipped: 'no_consent' }; } catch (e) {}
      var sample = {
        sampleId: t.sampleId || uuid(),
        sampleType: t.sampleType || 'UNKNOWN', accountMode: t.accountMode || 'UNKNOWN',
        platform: t.platform, asset: t.asset, assetClass: t.assetClass || null,
        timeframe: t.timeframe, expiration: t.expiration,
        strategy: t.strategy || null, strategyVersion: t.strategyVersion || null,
        direction: t.direction || null,
        aiPrediction: t.aiPrediction || null, aiConfidence: t.aiConfidence || null,
        aiModelVersion: t.aiModelVersion || null,
        entryPrice: t.entryPrice != null ? t.entryPrice : null,
        settlementPrice: t.settlementPrice != null ? t.settlementPrice : null,
        outcome: t.outcome || null,
        features: { x: t.featureVector || t.x || [] },
        botVersion: t.botVersion || botVersion,
        decisionAt: t.decisionAt || null, settledAt: t.settledAt || null,
        timestamp: t.timestamp || new Date().toISOString()
      };
      for (var attempt = 0; attempt < 2; attempt++) {
        try {
          var res = await _post(sample);
          if (res.status === 403) return { skipped: 'server_no_consent' };
          if (res.ok) return await res.json();
          if (res.status < 500) return { error: 'client_' + res.status }; // don't retry 4xx
        } catch (e) { /* network — fall through to one retry */ }
        await new Promise(function (r) { setTimeout(r, 1500); });
      }
      return { error: 'unreachable' };
    }

    return { emit: emit };
  }

  var api = { createKaosLearningClient: createKaosLearningClient };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.KaosLearningClient = api;
})(typeof self !== 'undefined' ? self : this);
