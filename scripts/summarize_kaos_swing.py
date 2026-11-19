"""Render all frozen candidates, including failed comparisons."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]/'research/kaos_swing_v1'

def main():
    read=lambda name:json.loads((OUT/name).read_text());swing=read('swing_validation.json');mom=read('momentum_validation.json');ss=read('swing_selection.json');ms=read('momentum_selection.json');sf=read('swing_confirmation.json');mf=read('momentum_confirmation.json')
    fmt=lambda x:'—' if x is None else f'{x:.3f}'
    lines=['\n## Results\n',f"Swing selection: **{ss['selected'] or 'none'}**, confirmation evaluated: **{ss['confirmation_evaluated']}**, confirmation gate passed: **{sf['qualified']}**.\n",'| Candle | Rule | Stop ATR | Trades | Net R | PF | Stress net R | Adjusted lower week mean R | Mean R/trade | Always-long mean R | Trend-long mean R | Eligible |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for key,r in swing.items():
        tf,family,mult=key.split(':');b=r['base'];lines.append(f"| {int(tf)//3600}h | {family} | {mult} | {b['trades']} | {b['netR']:.2f} | {fmt(b['PF'])} | {r['stress']['netR']:.2f} | {fmt(b['lower_week_mean'])} | {fmt(b['meanR'])} | {fmt(r['benchmarks']['always_long']['meanR'])} | {fmt(r['benchmarks']['trend_long']['meanR'])} | {r['eligible']} |")
    if ss['selected']:
        b=sf['base'];lines.append(f"\nSelected swing confirmation on new3asset2025: {b['trades']} trades, net {b['netR']:.2f}R, PF {fmt(b['PF'])}, combined-stress {sf['stress']['netR']:.2f}R, lower weekly mean {fmt(b['lower_week_mean'])}. Gate passed: {sf['qualified']}.\n")
    lines.extend(['\n### Weekly momentum portfolios\n',f"Selection: **{ms['selected'] or 'none'}**, confirmation evaluated: **{ms['confirmation_evaluated']}**, confirmation gate passed: **{mf['qualified']}**.\n",'| Lookback | Slots | Validation return | Drawdown | Matched return | Fully invested return | Stress return | Adjusted lower weekly excess | Eligible |','|---|---:|---:|---:|---:|---:|---:|---:|---|'])
    for key,r in mom.items():
        lookback,top=key.split(':');b=r['base'];lines.append(f"| {lookback}d | {top} | {100*b['strategy']['return']:.2f}% | {100*b['strategy']['max_drawdown']:.2f}% | {100*b['matched']['return']:.2f}% | {100*b['passive']['return']:.2f}% | {100*r['stress']['strategy']['return']:.2f}% | {fmt(None if b['lower_weekly_excess'] is None else 100*b['lower_weekly_excess'])}% | {r['eligible']} |")
    if ms['selected']:
        b=mf['base'];lines.append(f"\nSelected momentum confirmation on new3asset2025: net {100*b['strategy']['return']:.2f}%, drawdown {100*b['strategy']['max_drawdown']:.2f}%, matched basket {100*b['matched']['return']:.2f}%, combined-stress {100*mf['stress']['strategy']['return']:.2f}%. Gate passed: {mf['qualified']}.\n")
    lines.append('\nPositive historical P&L is distinct from passing the full gate. No failed candidate is promoted using a different profitable metric. Passing verification tests confirms implementation invariants, not predictive accuracy or future profits.\n')
    p=OUT/'README.md';p.write_text(p.read_text().split('\n## Results\n')[0]+'\n'.join(lines))
if __name__=='__main__':main()
