"""Print one paper/research intent or strategy catalog; never submit orders."""
import argparse,importlib.util,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('market_suite',ROOT/'research/kaos_market_suite_v1/strategies.py');suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path);p.add_argument('--list',action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args()
    if a.list:print(json.dumps(suite.descriptors(),indent=2));return
    if a.input is None:p.error('--input JSON or --list required')
    if a.input.stat().st_size>10_000_000:raise ValueError('Input too large')
    request=json.loads(a.input.read_text())
    if not a.replay:request['nowMs']=int(time.time()*1000)
    result=suite.evaluate(request);result['mode']='historical_replay' if a.replay else 'current_clock_paper_intent';result['eligibleForPerformanceClaims']=False
    print(json.dumps(result,indent=2,allow_nan=False))
if __name__=='__main__':main()
