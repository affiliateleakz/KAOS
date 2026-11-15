"""KAOS 3.0 evidence data health. Research freshness, NOT provider SLA status."""
from datetime import datetime, timezone
from kaos_opportunity import utc

SOURCE_AGE_MINUTES = {
    'technical': 45, 'options_flow': 60, 'liquidity': 60,
    'social': 120, 'news': 180, 'filing': 10080, 'macro': 180,
    'insider': 10080, 'institutional': 10080, 'politician': 10080,
    'onchain': 90, 'dark_pool': 1440, 'short_interest': 10080,
}


def provider(event_id):
    value = str(event_id or '').split(':', 1)[0].lower()
    return value if value in {'alpaca', 'tradier', 'binance-spot', 'dexscreener', 'gdelt', 'sec', 'sec-form4-txn', 'eth-mainnet', 'sec13f', 'bsky-social', 'bsky-search', 'option-volume-rise', 'reddit', 'x', 'bluesky', 'facebook', 'news', 'market', 'sec', 'ethereum', 'government', 'yahoo-news'} else 'other'


def summarize_health(records, now=None, max_records=5000):
    now = utc(now or datetime.now(timezone.utc))
    grouped = {}
    total = 0
    for record in records:
        try:
            observed = utc(record['observed_at'])
            source = str(record['source'])
            kind = str(record['asset_class'])
        except (KeyError, ValueError, TypeError):
            continue
        total += 1
        provider_name = provider(record.get('event_id'))
        key = (provider_name, kind, source)
        row = grouped.setdefault(key, {
            'provider': provider_name, 'asset_class': kind, 'source': source,
            'observations_in_sample': 0, 'last_observed_at': observed})
        row['observations_in_sample'] += 1
        if observed > row['last_observed_at']:
            row['last_observed_at'] = observed
    output = []
    for row in grouped.values():
        age = (now - row['last_observed_at']).total_seconds() / 60
        threshold = SOURCE_AGE_MINUTES.get(row['source'], 60)
        row['last_observed_at'] = row['last_observed_at'].isoformat()
        row['age_minutes'] = round(max(0, age), 1)
        row['state'] = ('recent_observation' if 0 <= age <= threshold
                        else 'stale_or_market_closed')
        output.append(row)
    output.sort(key=lambda item: (item['state'] != 'recent_observation', item['provider'], item['asset_class']))
    return {
        'mode': 'research_only',
        'status_meaning': 'Recency of data observations, not provider connectivity or trading-market hours',
        'sample_observations': total,
        'sample_truncated': total >= max_records,
        'sources': output,
        'feed_guarantees': False,
    }
