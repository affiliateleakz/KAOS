"""Render a fixed, non-cherry-picked view of the full study matrix."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'research/all_timeframes_v1'

def main():
    result=json.loads((DIR/'summary.json').read_text())
    labels={5:'5 seconds',10:'10 seconds',15:'15 seconds',30:'30 seconds',60:'1 minute',120:'2 minutes',180:'3 minutes',300:'5 minutes',600:'10 minutes',900:'15 minutes',1800:'30 minutes',3600:'1 hour',14400:'4 hours',86400:'Daily'}
    text=['\n## Results\n',f"Completed **{result['configurations']} configurations**. Validation-selected configuration: **{result['selected_on_validation'] or 'none met the frozen qualification gate'}**. No replacement configuration is selected from October results.\n",'The table below always shows **mid intensity with one-candle expiry**, rather than choosing each row’s best-performing setting. Short intervals use the already-seen descriptive pool; minute and higher use chronological validation. It is not a like-for-like comparison across data sources. Net figures use one-unit stakes; zero trades means insufficient evidence.\n','| Candle duration | Sample | Trades | Win rate | Net at 80% | Net at 90% | Delayed net at 90% |','|---|---|---:|---:|---:|---:|---:|']
    for tf,label in labels.items():
        phase='descriptive' if tf<60 else 'validation';bucket=result['short' if tf<60 else 'long'];r=bucket[f'{tf}:mid:1_candle'][phase];b=r['base'];wr=f"{b['win_rate']*100:.2f}%" if b['win_rate'] is not None else '—'
        text.append(f"| {label} | {phase} | {b['trades']:,} | {wr} | {b['net']['0.8']:.2f} | {b['net']['0.9']:.2f} | {r['delayed']['net']['0.9']:.2f} |")
    text.extend(['\n### Five-minute detail\n','Every five-minute configuration below is disclosed. These are exploratory comparisons, not twelve independently validated edges. Only the globally preselected validation candidate, if any, can pass the frozen confirmation gate.\n','| Intensity | Expiry | Validation trades | Validation win rate | Validation net90 | Confirmation trades | Confirmation win rate | Confirmation net90 | Confirmation delayed net90 |','|---|---|---:|---:|---:|---:|---:|---:|---:|'])
    for level in ['low','mid','high']:
        for expiry in ['source_adaptive','1_candle','2_candles','3_candles']:
            r=result['long'][f'300:{level}:{expiry}'];v=r['validation']['base'];c=r['confirmation']['base']
            fmt=lambda b:f"{100*b['win_rate']:.2f}%" if b['win_rate'] is not None else '—'
            text.append(f"| {level} | {expiry} | {v['trades']:,} | {fmt(v)} | {v['net']['0.9']:.2f} | {c['trades']:,} | {fmt(c)} | {c['net']['0.9']:.2f} | {r['confirmation']['delayed']['net']['0.9']:.2f} |")
    text.append('\nThe full matrix includes development, validation, and confirmation figures, every intensity/expiry combination, missing-resolution counts, and all payout scenarios. No profitable guarantee, broker execution claim, or live approval follows from this study.\n')
    path=DIR/'README.md';original=path.read_text().split('\n## Results\n')[0];path.write_text(original+'\n'.join(text))
if __name__=='__main__':main()
