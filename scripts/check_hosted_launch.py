"""Read-only public API checks. No login, charges, emails or settings changes."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

STORE_ID = 'gbobopmnjgeeegniphckfpalhnebapjm'
EXPECTED = {'free': (0, None, 1, 1), 'pro': (2995, 'month', 4, 3),
            'pro_yearly': (29995, 'year', 4, 3),
            'ultimate': (9995, 'month', 4, 5), 'ultimate_yearly': (99595, 'year', 4, 5)}
PROFILES = {'api': 'KAOS-Launch-Check/1.0', 'store': 'KAOS-Store-Readiness/1.0'}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise argparse.ArgumentTypeError('Use an HTTPS origin without credentials, path or query')
    return value.rstrip('/')


def fetch(url, user_agent, website, timeout):
    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': user_agent,
                                    'Origin': website})
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            body = response.read(131073)
            content_type = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
            result = {'status': response.status, 'contentType': content_type,
                      'corsMatchesWebsite': response.headers.get('Access-Control-Allow-Origin') == website}
            if len(body) > 131072:
                return {**result, 'error': 'response_too_large'}, None
            if content_type != 'application/json':
                challenge = b'bot verification' in body.lower() or b'lsrecaptcha' in body.lower()
                return {**result, 'error': 'bot_verification' if challenge else 'non_json_response'}, None
            try:
                value = json.loads(body)
            except (ValueError, UnicodeError):
                return {**result, 'error': 'invalid_json'}, None
            if response.status != 200 or not isinstance(value, dict):
                return {**result, 'error': 'unexpected_response'}, None
            return result, value
    except HTTPError as exc:
        return {'error': 'http_error', 'status': exc.code}, None
    except (URLError, OSError, TimeoutError):
        return {'error': 'connection_failed_or_timed_out'}, None


def catalog_issues(value):
    plans = value.get('plans')
    if not isinstance(plans, list) or any(not isinstance(p, dict) for p in plans):
        return ['invalid_catalog']
    issues = []
    for plan_id, (amount, interval, charts, devices) in EXPECTED.items():
        matches = [p for p in plans if p.get('id') == plan_id]
        if len(matches) != 1:
            issues.append(plan_id + ':missing_or_duplicate')
            continue
        plan = matches[0]
        entitlements = plan.get('entitlements') or {}
        if not isinstance(entitlements, dict):
            entitlements = {}
        if (plan.get('amount'), plan.get('interval'), plan.get('currency')) != (amount, interval, 'usd'):
            issues.append(plan_id + ':price_or_interval')
        if (entitlements.get('chartLimit'), entitlements.get('deviceLimit')) != (charts, devices):
            issues.append(plan_id + ':chart_or_device_limit')
    if any(p.get('id') not in EXPECTED for p in plans):
        issues.append('unexpected_plan_ids')
    return issues


def check(api, website, timeout=10):
    manifest = json.loads((Path(__file__).resolve().parents[1] / 'apps/extension/manifest.json').read_text())
    rows = []
    for profile, agent in PROFILES.items():
        for path in ('/api', '/api/billing/memberships', '/api/v1/extension/google/config'):
            row, value = fetch(api + path, agent, website, timeout)
            row.update(profile=profile, path=path)
            if value is not None:
                if path == '/api':
                    row['payloadMatches'] = value.get('status') == 'ok' and value.get('service') == 'KAOS Trading API'
                elif path.endswith('/memberships'):
                    row['catalogIssues'] = catalog_issues(value)
                    row['payloadMatches'] = not row['catalogIssues']
                    row['checkoutEnabled'] = value.get('checkoutEnabled') is True
                    row['mode'] = value.get('mode') if value.get('mode') in ('live', 'sandbox', 'test') else 'unknown'
                else:
                    row['payloadMatches'] = (value.get('configured') is True
                        and value.get('store_item_id') == STORE_ID
                        and value.get('client_id') == manifest.get('oauth2', {}).get('client_id'))
            row['passed'] = not row.get('error') and row.get('payloadMatches') is True and row.get('corsMatchesWebsite') is True
            rows.append(row)
    passed = all(row['passed'] for row in rows)
    return {'state': 'public_checks_passed' if passed else 'blocked', 'checks': rows,
            'launchCertified': False, 'changesMade': False,
            'note': 'GET checks only. Checkout, signed webhooks, actual Google login and email delivery remain unverified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-host', type=origin, default='https://api.tradingwithkaos.com')
    parser.add_argument('--website', type=origin, default='https://tradingwithkaos.com')
    args = parser.parse_args()
    report = check(args.api_host, args.website)
    print(json.dumps(report, indent=2))
    return 0 if report['state'] == 'public_checks_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
