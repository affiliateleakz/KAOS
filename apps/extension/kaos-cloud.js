/**
 * KAOS Cloud — the authoritative cloud/auth/license layer for the KAOS Trading Bot.
 *
 * Runs inside the MV3 service worker (loaded via importScripts in background.js). It owns EVERYTHING
 * that talks to the KAOS website/backend and is deliberately separate from broker execution:
 *   • KAOS login / session / token refresh / logout
 *   • Membership verification            (GET /api/v1/extension/me -> license)
 *   • Entitlement / license verification (license.authorized + entitlements)
 *   • Device registration / authorization (POST /api/v1/devices/register, 403 => not authorized)
 *   • Bot version check                  (GET /api/v1/bot/release)
 *   • Strategy/config retrieval          (GET /api/v1/bot/config)
 *   • Platform selection + Remember/Switch (local, GET /api/v1/platforms)
 *   • AI prediction requests             (POST /api/v1/ai/predict)   [learning-only]
 *   • Collective Learning consent        (POST /api/v1/ai/consent)
 *
 * Cloud connectivity (KAOS) is NEVER confused with broker connectivity (Pocket Option). Trade sync
 * and learning-sample submission are handled by kaos-sync-client.js / kaos-learning-client.js.
 */
(function (root) {
  'use strict';

  var API_HOST_KEY = 'kaos_api_host';
  // Default KAOS host — override at runtime (Cloud Status → host) or via KAOS_SET_HOST.
  var DEFAULT_API_HOST = 'https://api.tradingwithkaos.com';
  var TOK = 'kaos_tokens', USER = 'kaos_user', DEV = 'installId',
      PLAT = 'kaos_platform', REMEMBER = 'kaos_remember_platform',
      CONSENT = 'collectiveLearning', STATE = 'kaos_cloud_state';

  function sget(keys) { return new Promise(function (r) { chrome.storage.local.get(keys, function (d) { r(d || {}); }); }); }
  function sset(obj) { return new Promise(function (r) { chrome.storage.local.set(obj, function () { r(); }); }); }
  function uuid() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 'id-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  async function apiHost() {
    var d = await sget([API_HOST_KEY]);
    var saved = String(d[API_HOST_KEY] || '').replace(/\/+$/, '');
    var bad = !saved ||
      saved === 'https://tradingwithkaos.com' ||
      saved === 'http://tradingwithkaos.com' ||
      saved === 'https://www.tradingwithkaos.com' ||
      saved === 'http://www.tradingwithkaos.com';
    if (bad) {
      saved = DEFAULT_API_HOST;
      await sset(kv(API_HOST_KEY, saved));
    }
    return saved;
  }
  async function apiBase() { return (await apiHost()) + '/api/v1'; }
  async function setApiHost(h) { await sset(kv(API_HOST_KEY, String(h || '').replace(/\/+$/, ''))); }

  function kv(k, v) { var o = {}; o[k] = v; return o; }

  async function getTokens() { var d = await sget([TOK]); return d[TOK] || {}; }
  function normalizeTokens(t) {
    t=t||{};
    return {
      accessToken: t.accessToken || t.access_token || t.access || null,
      refreshToken: t.refreshToken || t.refresh_token || t.refresh || null
    };
  }
  async function setTokens(t) { await sset(kv(TOK, normalizeTokens(t))); }
  async function apiJson(response, label) {
    var text = await response.text();
    var body;
    try { body = JSON.parse(text); } catch (_) {
      var challenged = /bot verification|lsrecaptcha|recaptcha|captcha|verify you are human/i.test(text);
      var error = new Error(challenged ?
        'KAOS hosting returned a bot-verification page instead of the API. Contact KAOS support; the hosting firewall must allow API requests.' :
        label + ' returned an invalid API response (HTTP ' + response.status + '). Contact KAOS support.');
      error.kind = challenged ? 'HOSTING_VERIFICATION' : 'INVALID_API_RESPONSE';
      error.httpStatus = response.status;
      throw error;
    }
    if (!body || typeof body !== 'object' || Array.isArray(body)) {
      var invalid = new Error(label + ' returned an invalid JSON object. Contact KAOS support.');
      invalid.kind = 'INVALID_API_RESPONSE'; throw invalid;
    }
    return body;
  }
  async function health() {
    var host=await apiHost(), urls=[host+'/api',host+'/api/'];
    var last=null;
    for (var i=0;i<urls.length;i++) {
      try {
        var ctrl=typeof AbortController!=='undefined'?new AbortController():null;
        var timer=ctrl?setTimeout(function(){try{ctrl.abort();}catch(_){}},6000):null;
        var r=await fetch(urls[i],{method:'GET',cache:'no-store',signal:ctrl?ctrl.signal:undefined});
        if(timer)clearTimeout(timer);
        var body=await apiJson(r,'KAOS health check');
        if(r.ok && (body.status==='ok'||body.runtime==='native-wsgi')) return {ok:true,httpStatus:r.status,url:urls[i],body:body};
        last={ok:false,httpStatus:r.status,url:urls[i],error:'KAOS health check did not report a healthy API'};
      } catch(e) { last={ok:false,error:String(e&&e.message||e),url:urls[i]}; }
    }
    return last||{ok:false,error:'health check failed'};
  }
  async function installId() { var d = await sget([DEV]); if (d[DEV]) return d[DEV]; var id = uuid(); await sset(kv(DEV, id)); return id; }

  async function authHeaders() {
    var t = await getTokens(), did = await installId();
    var h = { 'Content-Type': 'application/json', 'X-Device-Id': did };
    if (t.accessToken) h['Authorization'] = 'Bearer ' + t.accessToken;
    return h;
  }

  async function refresh() {
    var t = await getTokens();
    if (!t.refreshToken) return false;
    try {
      var res = await fetch((await apiBase()) + '/auth/refresh', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken: t.refreshToken })
      });
      if (!res.ok) return false;
      var j = await res.json();
      await setTokens(j);
      return true;
    } catch (e) { return false; }
  }

  // Authenticated fetch with a SINGLE refresh-on-401. Throws typed errors: OFFLINE / SESSION_EXPIRED.
  async function authFetch(path, opts, retried) {
    opts = opts || {};
    var base = await apiBase();
    var headers = Object.assign(await authHeaders(), opts.headers || {});
    var res;
    try { res = await fetch(base + path, Object.assign({}, opts, { headers: headers })); }
    catch (e) { var er = new Error('offline'); er.kind = 'OFFLINE'; throw er; }
    if (res.status === 401) {
      if (!retried && await refresh()) return authFetch(path, opts, true);
      var e2 = new Error('session expired'); e2.kind = 'SESSION_EXPIRED'; throw e2;
    }
    return res;
  }

  async function login(email, password) {
    var res;
    try {
      res = await fetch((await apiBase()) + '/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, password: password })
      });
    } catch (e) { var eo = new Error('KAOS cloud offline'); eo.kind = 'OFFLINE'; throw eo; }
    if (!res.ok) {
      var detail = '';
      try { var failed = await res.json(); detail = String(failed.detail || failed.error || failed.message || ''); } catch (_) {}
      // A missing v1 route is a runtime mismatch, not bad credentials. Never
      // retry passwords against guessed legacy routes or accept cookie-only auth.
      if (res.status === 404) {
        var server = await health();
        var runtime = server.body && server.body.runtime;
        var incompatible = new Error(runtime === 'native-wsgi' ?
          'This KAOS server runs the legacy API and does not support extension sign-in. A validated server compatibility update is required.' :
          'This KAOS server does not provide extension sign-in. Check the API host and server version.');
        incompatible.kind = 'INCOMPATIBLE_SERVER';
        incompatible.httpStatus = 404;
        throw incompatible;
      }
      var safe = detail.slice(0, 180);
      var label = res.status === 401 ? 'Invalid email or password' :
                  res.status === 403 ? (safe || 'Account access denied') :
                  res.status === 404 ? 'KAOS login endpoint not found on server' :
                  res.status >= 500 ? 'KAOS server error (' + res.status + ')' :
                  'KAOS login rejected (HTTP ' + res.status + ')';
      var e = new Error(label); e.kind = res.status === 401 ? 'BAD_CREDENTIALS' : 'LOGIN_FAILED'; e.httpStatus = res.status; throw e;
    }
    var j;
    j = await apiJson(res, 'KAOS login server');
    var normalized = normalizeTokens(j);
    if (!normalized.accessToken) throw new Error('KAOS login response did not contain an access token');
    await setTokens(j);
    await sset(kv(USER, j.user || null));
    await installId();
    return j.user;
  }

  async function googleLogin() {
    if (!chrome.identity || !chrome.identity.getAuthToken) throw new Error('Chrome Identity API is unavailable');
    var storeItem='gbobopmnjgeeegniphckfpalhnebapjm';
    if (chrome.runtime.id && chrome.runtime.id!==storeItem) throw new Error('Google sign-in requires the official KAOS extension ID '+storeItem+'. For an unpacked build, use this listing’s public key; do not create another store item.');
    var base=await apiBase();
    async function request(path,options) {
      var controller=new AbortController();
      var timer=setTimeout(function(){controller.abort();},15000);
      try { return await fetch(base+path,Object.assign({},options,{signal:controller.signal})); }
      catch (_) { throw new Error('KAOS API is unavailable during Google sign-in. Try email sign-in or contact KAOS support.'); }
      finally { clearTimeout(timer); }
    }
    var configResponse=await request('/extension/google/config',{method:'GET',cache:'no-store'});
    // Earlier KAOS backends support the verified token exchange but not this
    // optional diagnostic endpoint. A missing diagnostic must not block sign-in.
    // Authentication still requires the same Google-verified server exchange.
    if (configResponse.status!==404) {
      var config=await apiJson(configResponse,'KAOS Google configuration');
      if (!configResponse.ok || !config.configured || !config.client_id) throw new Error('KAOS extension Google sign-in is not configured on the server. Contact KAOS support or use email sign-in.');
      var oauth=(chrome.runtime.getManifest()||{}).oauth2;
      if (!oauth || oauth.client_id!==config.client_id) throw new Error('The KAOS server and extension use different Google OAuth clients. Contact KAOS support.');
    }
    for (var attempt=0;attempt<2;attempt++) {
      var tokenResponse;
      try { tokenResponse=await chrome.identity.getAuthToken({interactive:true}); }
      catch (error) {
        var message=String(error&&error.message||error);
        if (/cancel|did not approve|not grant/i.test(message)) throw new Error('Google sign-in was cancelled. Try again or use email sign-in.');
        if (/client|oauth|not signed in/i.test(message)) throw new Error('Chrome could not authorize Google sign-in. Check that you are signed into Chrome and contact KAOS support to verify the OAuth client for this extension ID.');
        throw new Error('Chrome Google sign-in failed: '+message.slice(0,180));
      }
      var accessToken=typeof tokenResponse==='string'?tokenResponse:tokenResponse&&tokenResponse.token;
      if (!accessToken) throw new Error('Google did not return an access token');
      var res=await request('/extension/google/access-token',{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({access_token:accessToken})
      });
      var data=await apiJson(res,'KAOS Google sign-in');
      if (res.status===401 && attempt===0 && chrome.identity.removeCachedAuthToken) {
        await chrome.identity.removeCachedAuthToken({token:accessToken});
        continue;
      }
      if (!res.ok) throw new Error(String(data.detail||'Google login failed (HTTP '+res.status+')').slice(0,180));
      if (!normalizeTokens(data).accessToken) throw new Error('Google login response missing KAOS access token');
      await setTokens(data);
      await sset(kv(USER,data.user||null));
      await installId();
      return data.user;
    }
  }

  async function logout() {
    try { await authFetch('/auth/logout', { method: 'POST' }); } catch (e) {}
    await setTokens({});
    await sset({ kaos_user: null, kaos_cloud_state: 'LOGGED_OUT' });
    return true;
  }

  async function me() {
    var res = await authFetch('/extension/me', { method: 'GET' });
    if (!res.ok) { var failed=await res.json().catch(function(){return {};}); var e = new Error(typeof failed.detail==='string'?failed.detail.slice(0,240):'Session check failed'); e.kind = res.status===403?'DEVICE_NOT_AUTHORIZED':'API_ERROR'; e.httpStatus=res.status; throw e; }
    return res.json();
  }

  async function registerDevice() {
    var did = await installId();
    var nav = (typeof navigator !== 'undefined' && navigator) || {};
    var res = await authFetch('/devices/register', {
      method: 'POST',
      body: JSON.stringify({
        deviceName: 'KAOS Bot · ' + (nav.platform || 'browser'),
        installId: did,
        extensionVersion: (chrome.runtime.getManifest && chrome.runtime.getManifest().version) || '1.0'
      })
    });
    if (!res.ok) {
      var failed = await res.json().catch(function () { return {}; });
      var detail = typeof failed.detail === 'string' ? failed.detail.slice(0, 240) : '';
      var error = new Error(detail || 'Device registration failed (HTTP ' + res.status + ')');
      error.kind = res.status === 403 ? 'DEVICE_NOT_AUTHORIZED' : 'API_ERROR';
      error.httpStatus = res.status;
      throw error;
    }
    return res.json();
  }

  async function botConfig() { try { var r = await authFetch('/bot/config', { method: 'GET' }); return r.ok ? r.json() : null; } catch (e) { return null; } }
  async function release() { try { var r = await authFetch('/bot/release', { method: 'GET' }); return r.ok ? r.json() : null; } catch (e) { return null; } }
  async function platforms() { try { var r = await authFetch('/platforms', { method: 'GET' }); return r.ok ? r.json() : []; } catch (e) { return []; } }
  async function setConsent() { await sset(kv(CONSENT,true)); return {collectiveLearningConsent:true,sharedLearningRequired:true}; }
  async function getConsent() { return true; }
  async function predict(featureVector, ctx) {
    try {
      var r = await authFetch('/ai/predict', { method: 'POST', body: JSON.stringify(Object.assign({ featureVector: featureVector }, ctx || {})) });
      return r.ok ? r.json() : null;
    } catch (e) { return null; }
  }

  async function selectPlatform(id, remember) { await sset({ kaos_platform: id, kaos_remember_platform: !!remember }); return { platform: id, remember: !!remember }; }
  async function switchPlatform() { await sset({ kaos_remember_platform: false }); return { switched: true }; }
  async function getPlatform() { var d = await sget([PLAT, REMEMBER]); return { platform: d[PLAT] || null, remember: !!d[REMEMBER] }; }

  // Map the server license into a single cloud status the UI can render.
  function classifyLicense(lic) {
    if (!lic) return { ok: false, status: 'LICENSE_INVALID', reasons: [] };
    var reasons = lic.reasons || [];
    if (reasons.indexOf('device_revoked') >= 0) return { ok: false, status: 'DEVICE_NOT_AUTHORIZED', reasons: reasons };
    if (!lic.authorized) return { ok: false, status: 'LICENSE_INVALID', reasons: reasons };
    return { ok: true, status: 'CONNECTED', reasons: reasons };
  }

  // Full startup orchestration:
  // OPEN → LOGIN/restore → membership → entitlement → device → platform selection → dashboard.
  async function startup(lightweight) {
    var t = await getTokens();
    if (!t.accessToken && !t.refreshToken) return { step: 'LOGIN', status: 'LOGGED_OUT' };
    // Register first: server license lookup requires a device associated with this member.
    // Device registration is server-authoritative and refuses revoked or over-limit IDs.
    var device = null;
    if (!lightweight) {
    try { device = await registerDevice(); }
    catch (e) {
      if (e.kind === 'SESSION_EXPIRED') return { step: 'LOGIN', status: 'SESSION_EXPIRED' };
      if (e.kind === 'OFFLINE') return { step: 'OFFLINE', status: 'OFFLINE', serverOnline: false };
      return { step: 'BLOCKED', status: e.kind === 'DEVICE_NOT_AUTHORIZED' ?
               'DEVICE_NOT_AUTHORIZED' : 'DEVICE_REGISTRATION_FAILED',
               detail: String(e && e.message || 'Device registration failed') };
    }
    if (!device || !device.id || device.revoked)
      return { step: 'BLOCKED', status: 'DEVICE_REGISTRATION_FAILED',
               detail: 'Device registration returned an invalid or revoked device' };
    }
    var info;
    try { info = await me(); }
    catch (e) {
      if(e.kind==='DEVICE_NOT_AUTHORIZED')return {step:'BLOCKED',status:'DEVICE_NOT_AUTHORIZED',detail:e.message};
      if(e.kind==='API_ERROR')return {step:'OFFLINE',status:'OFFLINE',detail:e.message,httpStatus:e.httpStatus};
      if (e.kind === 'OFFLINE') {
        var hs=await health();
        if (hs && hs.ok) {
          // The KAOS server is demonstrably online. Do not lie to the UI by calling
          // this SERVER OFFLINE; this is an account/auth endpoint problem.
          return { step:'LOGIN', status:'ACCOUNT_CONNECTION_ERROR', serverOnline:true, health:hs,
                   detail:'Server health is online but the authenticated extension session could not be restored.' };
        }
        return { step:'OFFLINE', status:'OFFLINE', serverOnline:false, health:hs };
      }
      return { step:'LOGIN', status:'SESSION_EXPIRED', serverOnline:true };
    }
    await sset({ kaosEntitlements: info.entitlements || null });
    var cl = classifyLicense(info.license);
    if (!cl.ok) return { step: 'BLOCKED', status: cl.status, license: info.license, user: info.user, entitlements: info.entitlements };


    var plat = await getPlatform();
    // Membership/auth/device establish cloud connectivity. Optional config/release
    // endpoints must never downgrade a valid session to OFFLINE.
    var cfg = null, rel = null;
    if (!lightweight) {
    try { cfg = await botConfig(); } catch (e) { cfg = { optionalError: String(e && e.message || e) }; }
    if (cfg && typeof cfg.collectiveLearningConsent === 'boolean') await sset(kv(CONSENT, cfg.collectiveLearningConsent));
    try { rel = await release(); } catch (e) { rel = { optionalError: String(e && e.message || e) }; }
    }
    await sset(kv(STATE, 'CONNECTED'));
    var base = { status: 'CONNECTED', user: info.user, license: info.license, entitlements: info.entitlements,
                 platform: plat.platform, remember: plat.remember, config: cfg, release: rel, device: device };
    // Once a platform has been explicitly selected/connected, stay on the dashboard.
    // The remember flag controls persistence preference; it must not force the user
    // back through the platform chooser during the same authenticated session.
    if (plat.platform) return Object.assign({ step: 'DASHBOARD' }, base);
    return Object.assign({ step: 'PLATFORM' }, base);
  }

  root.KaosCloud = {
    login: login, googleLogin: googleLogin, logout: logout, me: me, startup: startup, sessionStatus: function(){return startup(true);}, registerDevice: registerDevice,
    botConfig: botConfig, release: release, platforms: platforms, setConsent: setConsent, getConsent: getConsent,
    predict: predict, selectPlatform: selectPlatform, switchPlatform: switchPlatform, getPlatform: getPlatform,
    getTokens: getTokens, setApiHost: setApiHost, apiHost: apiHost, apiBase: apiBase,
    authFetch: authFetch, installId: installId, classifyLicense: classifyLicense, refresh: refresh, health: health
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.KaosCloud;
})(typeof self !== 'undefined' ? self : this);
