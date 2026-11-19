"""Write the full frozen comparisons without choosing a post-hoc winner."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/kaos_candidate_v1'

def main():
    spot=json.loads((OUT/'spot_validation.json').read_text());selection=json.loads((OUT/'spot_selection.json').read_text());final=json.loads((OUT/'spot_confirmation.json').read_text());binary=json.loads((OUT/'binary_results.json').read_text())
    lines=['\n## Results\n',f"Spot: **{len(spot)} candidates**, **{selection['eligible_count']} eligible**, selected: **{selection['selected'] or 'none'}**. Confirmation evaluated: **{selection['confirmation_evaluated']}**. Confirmation qualified: **{final['qualified']}**.\n",'The validation table discloses every fixed candidate. Its numbers combine independently sized one-risk-unit trades; they are not percentages or achievable pooled-account returns. Costs include both entry and exit.\n','| Candle | Rule | Target R | Trades | Net R | Mean R/trade | Profit factor | Combined-stress net R | Always-long mean R | Trend-long mean R | Eligible |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for key,r in spot.items():
        tf,family,rr=key.split(':');b=r['base'];s=r['combined_stress'];bench=r['benchmarks']
        fmt=lambda x:'—' if x is None else f'{x:.3f}'
        lines.append(f"| {int(tf)//60}m | {family} | {rr} | {b['trades']:,} | {b['net']:.2f} | {fmt(b['mean_per_trade'])} | {fmt(b['profit_factor'])} | {s['net']:.2f} | {fmt(bench['always_long']['mean_per_trade'])} | {fmt(bench['trend_long']['mean_per_trade'])} | {r['eligible']} |")
    lines.extend(['\n### Pocket Option historical comparison\n',f"**{len(binary['results'])} candidates**. Historical selection: **{binary['historical_selection'] or 'none'}**. Reserved-period outcomes evaluated: **{binary['reserved_evaluated']}**. This table uses assumed 80% payout and one-unit stakes.\n",'| Candle | Rule | Expiry candles | Trades | Decided win rate | Net80 | Combined-stress net80 | Historical gate |','|---|---|---:|---:|---:|---:|---:|---|'])
    for key,r in binary['results'].items():
        tf,family,count=key.split(':');b=r['base'];wr='—' if b['win_rate'] is None else f"{100*b['win_rate']:.2f}%"
        lines.append(f"| {int(tf)//60}m | {family} | {count} | {b['trades']:,} | {wr} | {b['net']:.2f} | {r['combined_stress']['net']:.2f} | {r['historical_gate']} |")
    lines.append('\nPassing code checks verifies the replay mechanics, not investment performance. An unqualified candidate must not be described as a proven strategy or published as a profitable pretrained model. No real-money deployment follows from these artifacts.\n')
    p=OUT/'README.md';original=p.read_text().split('\n## Results\n')[0];p.write_text(original+'\n'.join(lines))
if __name__=='__main__':main()
