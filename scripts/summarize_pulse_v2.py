"""Disclose all frozen class/config comparisons and separate binary payouts."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]/'research/kaos_pulse_v2'

def main():
    read=lambda name:json.loads((OUT/name).read_text());r=read('price_results.json');b=read('baselines.json');binary=read('binary_results.json');sel=read('selection.json');final=read('confirmation.json')
    fmt=lambda x:'—' if x is None else f'{x:.3f}'
    p=OUT/'README.md';text=p.read_text().split('\n## Results\n')[0];lines=['\n## Results\n',f"Completed24price-class/config comparisons plus8uniquebinaryconfigurations. Primarycrypto selection: **{sel['selected'] or 'none'}**. Confirmation evaluated: **{sel['confirmation_evaluated']}**; finalqualified: **{final['qualified']}**. There is no qualified production release.\n"]
    for kind,variants in r.items():
        lines.extend([f'\n### {kind}\n','| TF | EMA200 guard | Target ATR | Trades | Net R | PF | Mean net bps/trade | Combined-stress R | Gate |','|---|---|---:|---:|---:|---:|---:|---:|---|'])
        for key,x in variants.items():
            tf,g,t=key.split(':');m=x['base'];lines.append(f"| {int(tf)//3600}h | {g[-1]} | {t[-1]} | {m['trades']} | {m['netR']:.2f} | {fmt(m['PF'])} | {fmt(m['meanNetBps'])} | {x['stress']['netR']:.2f} | {x['gate']} |")
        lines.extend(['\nBoth corrected original controls:\n','| TF | Baseline | Trades | Net R | PF | Mean net bps/trade |','|---|---|---:|---:|---:|---:|'])
        for tf,versions in b[kind].items():
            for name,x in versions.items():
                m=x['base'];lines.append(f"| {int(tf)//3600}h | {name} | {m['trades']} | {m['netR']:.2f} | {fmt(m['PF'])} | {fmt(m['meanNetBps'])} |")
    lines.extend(['\n### Fixed-expiry Pocket Option history\n','These outcomes use observedfive-secondentry/settlementopens, not target/stop exits. Payouts are assumptions, tiesrefund. None of the reserved later quotes were scored.\n','| Candle | Trend guard | Expiry candles | Trades | Decided WR | Net70 | Net80 | Net90 | Net92 | Combined-stress net80 | Gate |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|'])
    for key,x in binary['results'].items():
        tf,g,e=key.split(':');m=x['base'];wr='—' if m['win_rate'] is None else f"{100*m['win_rate']:.2f}%";net=m['net_payouts']
        lines.append(f"| {tf}s | {g[-1]} | {e[-1]} | {m['trades']} | {wr} | {net['0.7']:.2f} | {net['0.8']:.2f} | {net['0.9']:.2f} | {net['0.92']:.2f} | {x['stress']['net']:.2f} | {x['descriptive_gate']} |")
    lines.extend(['\nOriginal-entry binary controls:\n','| Candle | Expiry candles | Trades | Decided WR | Net80 | Stress net80 |','|---|---:|---:|---:|---:|---:|'])
    for key,x in binary['baselines'].items():
        tf,e=key.split(':');m=x['base'];wr='—' if m['win_rate'] is None else f"{100*m['win_rate']:.2f}%";lines.append(f"| {tf}s | {e} | {m['trades']} | {wr} | {m['net']:.2f} | {x['stress']['net']:.2f} |")
    lines.append('\nThe first fixed hourly unguarded3ATR-target stock configuration improved PF from1.121 to1.208 and mean netbps/trade from2.065 to2.213, but had only34trades and a negative confidence lower bound. Four-hour stock gains used only10trades or fewer. Those are weak retrospective leads, not proven improvements. Crypto and forex candidates lost after modeled costs; binary revision results were below80%payoutbreakeven and weaker than the original entry. Tighter risk controls do not establish better entry alpha. No losing variant or market was removed.\n')
    p.write_text(text+'\n'.join(lines))
if __name__=='__main__':main()
