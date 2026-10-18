"""Research-only SEC 13F-HR holdings snapshots from publicly accessible filings.

Never infer same-day buying, stock ticker from CUSIP, or directional signal.
Manager-specific and filing-date-limited; not comprehensive 13F market coverage.
"""
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from urllib.request import Request, urlopen

from collector_common import utc
from sec_edgar_filings import get_submissions, accepted_time, ACCESSION_RE, EDGAR_ARCHIVES

CIK_RE = re.compile(r'^\d{1,10}$')
XML_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\.xml$', re.I)
CUSIP_RE = re.compile(r'^[0-9A-Za-z]{9}$')
MAX_XML = 8_000_000
MAX_INDEX = 2_000_000


def validate_managers(raw):
    if not isinstance(raw, list) or len(raw) > 20:
        raise ValueError('institutional_managers must be <=20 entries')
    result, seen = [], set()
    for entry in raw:
        if not isinstance(entry, dict) or set(entry) != {'name', 'cik'}:
            raise ValueError('Manager needs exactly name and cik')
        name, cik = entry['name'], entry['cik']
        if isinstance(cik, int) and not isinstance(cik, bool):
            cik = str(cik)
        if not isinstance(cik, str) or not CIK_RE.fullmatch(cik):
            raise ValueError('Invalid SEC manager CIK')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c) < 32 for c in name):
            raise ValueError('Invalid SEC manager name')
        cik = cik.zfill(10)
        if cik in seen:
            raise ValueError('Duplicate SEC manager CIK')
        seen.add(cik)
        result.append({'name': name.strip(), 'cik': cik})
    return result


def _archive_url(cik, accession, name):
    if not re.fullmatch(r'\d{10}', cik) or not ACCESSION_RE.fullmatch(accession):
        raise ValueError('Invalid SEC filing identifier')
    if name != 'index.json' and not XML_NAME.fullmatch(name):
        raise ValueError('Invalid SEC document name')
    return EDGAR_ARCHIVES + str(int(cik)) + '/' + accession.replace('-', '') + '/' + name


def _get_limited(url, user_agent, max_size, opener=urlopen):
    if not url.startswith(EDGAR_ARCHIVES):
        raise ValueError('Unexpected SEC URL')
    if not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+', user_agent or ''):
        raise ValueError('SEC_USER_AGENT must include a real contact address')
    with opener(Request(url, headers={'User-Agent': user_agent, 'Accept-Encoding': 'identity'}), timeout=30) as r:
        data = r.read(max_size + 1)
    if len(data) > max_size:
        raise ValueError('SEC document over size limit')
    return data


def find_information_tables(index_payload):
    if not isinstance(index_payload, dict):
        raise ValueError('SEC archive index must be JSON object')
    items = (index_payload.get('directory') or {}).get('item') or []
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ValueError('Unexpected SEC index entries')
    files = []
    for item in items[:1000]:
        name = item.get('name') if isinstance(item, dict) else None
        if isinstance(name, str) and XML_NAME.fullmatch(name) and name.lower() != 'primary_doc.xml':
            files.append(name)
    # Filing packages often call the table infotable.xml or informationtable.xml.
    files.sort(key=lambda n: (not ('infotable' in n.lower() or 'informationtable' in n.lower()), n))
    return files[:4]


def _children(parent, name):
    return [x for x in parent if x.tag.rsplit('}', 1)[-1] == name]


def _field(parent, name):
    values = _children(parent, name)
    return (values[0].text or '').strip() if values else ''


def parse_information_table(content):
    if not isinstance(content, (bytes, str)) or len(content) > MAX_XML:
        raise ValueError('Invalid 13F XML')
    b = content if isinstance(content, bytes) else content.encode()
    if b'<!DOCTYPE' in b.upper() or b'<!ENTITY' in b.upper():
        raise ValueError('Disallowed XML declaration')
    root = ET.fromstring(content)
    if root.tag.rsplit('}', 1)[-1].lower() != 'informationtable':
        raise ValueError('Not a 13F information table')
    out = []
    for item in _children(root, 'infoTable')[:5000]:
        cusip = _field(item, 'cusip').upper().replace(' ', '')
        if not CUSIP_RE.fullmatch(cusip):
            continue
        issuer = _field(item, 'nameOfIssuer')[:100]
        security = _field(item, 'titleOfClass')[:80]
        call_put = _field(item, 'putCall').upper()
        raw_value = _field(item, 'value')
        shares_node = _children(item, 'shrsOrPrnAmt')
        amount = _field(shares_node[0], 'sshPrnamt') if shares_node else ''
        amt_type = _field(shares_node[0], 'sshPrnamtType') if shares_node else ''
        try:
            value = Decimal(raw_value)
            if not value.is_finite() or value < 0: continue
        except (InvalidOperation, ValueError):
            continue
        out.append({'cusip': cusip, 'issuer': issuer, 'security': security,
                    'value_as_filed': str(value), 'shares_as_filed': amount,
                    'shares_type': amt_type, 'put_call': call_put})
    return out


def recent_filing(cik, payload, now=None, max_age_days=7):
    now = utc(now or datetime.now(timezone.utc))
    if not isinstance(payload, dict) or int(payload.get('cik', -1)) != int(cik):
        raise ValueError('SEC manager CIK mismatch')
    recent = ((payload.get('filings') or {}).get('recent') or {})
    forms = recent.get('form') or []
    nums = recent.get('accessionNumber') or []
    dates = recent.get('filingDate') or []
    accepted = recent.get('acceptanceDateTime') or []
    report_dates = recent.get('reportDate') or []
    if not all(isinstance(v, list) for v in [forms, nums, dates, accepted, report_dates]):
        raise ValueError('Bad SEC filing arrays')
    if not len(forms) == len(nums) == len(dates) or len(accepted) not in (0, len(forms)):
        raise ValueError('Misaligned SEC filing records')
    for i, form in enumerate(forms):
        if form != '13F-HR' or not isinstance(nums[i], str) or not ACCESSION_RE.fullmatch(nums[i]):
            continue  # exclude amendments until explicit reconciliation is supported
        published, precision = accepted_time(accepted[i] if accepted else None, dates[i])
        if not timedelta(0) <= now - published <= timedelta(days=max_age_days):
            continue
        period = report_dates[i] if i < len(report_dates) else ''
        return {'accession': nums[i], 'published_at': published, 'precision': precision,
                'period': str(period)[:10]}
    return None


def observe_holdings(manager, filing, holdings, source_url, now=None, max_holdings=25):
    now = utc(now or datetime.now(timezone.utc))
    published = filing['published_at']
    # One reported holding is an end-of-quarter position, not a trade event.
    selected = sorted(holdings, key=lambda r: Decimal(r['value_as_filed']), reverse=True)[:max_holdings]
    observations = []
    for holding_index, holding in enumerate(selected):
        ident = holding['cusip']
        desc = (f"SEC 13F-HR holding snapshot: {manager['name']} reported {holding['issuer']} "
                f"(CUSIP {ident}, class {holding['security']}, {holding['put_call'] or 'no PUT/CALL flag'}) "
                f"for report period {filing['period'] or 'not provided'}, filed at {published.date().isoformat()}. "
                f"Reported value {holding['value_as_filed']} (13F as-filed units), "
                f"quantity {holding['shares_as_filed']} {holding['shares_type']}. "
                'This delayed quarter-end position is NOT a live buy, sale, net flow, or directional prediction; '
                'CUSIP is deliberately not converted to a ticker.')
        observations.append({'asset': 'CUSIP:' + ident, 'asset_class': 'stock',
                             'source': 'institutional', 'direction': 'neutral', 'strength': 0.15,
                             'event_id': 'sec13f:' + manager['cik'] + ':' + filing['accession'] + ':' + ident + ':' + str(holding_index),
                             'observed_at': now.isoformat(), 'published_at': published.isoformat(),
                             'source_url': source_url, 'summary': desc[:1200]})
    return observations


def run(managers, *, user_agent=None, now=None, opener=urlopen, pause_seconds=1.0):
    managers = validate_managers(managers)
    if not managers: return [], []
    user_agent = user_agent or os.getenv('SEC_USER_AGENT', '')
    if not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+', user_agent):
        return [], [{'provider': 'sec13f', 'reason': 'missing_valid_SEC_USER_AGENT'}]
    now = utc(now or datetime.now(timezone.utc))
    results, errors = [], []
    for i, manager in enumerate(managers):
        if i and pause_seconds: time.sleep(pause_seconds)
        try:
            submission = get_submissions(manager['cik'], user_agent, opener=opener)
            filing = recent_filing(manager['cik'], submission, now)
            if filing is None: continue
            # SEC returned manager identity takes precedence over a configured label.
            actual_name = submission.get('name')
            verified_manager = dict(manager)
            if isinstance(actual_name, str) and actual_name.strip():
                verified_manager['name'] = actual_name.strip()[:80]
            else:
                verified_manager['name'] += ' (configured label; SEC name not present)'
            index_url = _archive_url(manager['cik'], filing['accession'], 'index.json')
            doc = json.loads(_get_limited(index_url, user_agent, MAX_INDEX, opener=opener))
            filenames = find_information_tables(doc)
            if not filenames: raise ValueError('13F information table XML not found in filing index')
            parsed = None
            for filename in filenames:
                url = _archive_url(manager['cik'], filing['accession'], filename)
                try:
                    if pause_seconds: time.sleep(pause_seconds)
                    rows = parse_information_table(_get_limited(url, user_agent, MAX_XML, opener=opener))
                    parsed = (rows, url)
                    break
                except (ValueError, ET.ParseError):
                    continue
            if parsed is None: raise ValueError('13F information table XML could not be parsed')
            results.extend(observe_holdings(verified_manager, filing, *parsed, now=now))
        except Exception as exc:
            errors.append({'provider': 'sec13f', 'manager_cik': manager['cik'],
                           'reason': type(exc).__name__ + ': ' + str(exc)[:160]})
    return results, errors
