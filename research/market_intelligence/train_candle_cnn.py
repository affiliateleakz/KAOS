"""KAOS original PyTorch OHLCV-sequence CNN experiment (research only).

Inspired conceptually by matrix-vs-image comparisons from
hardyqr/CNN-for-Stock-Market-Prediction-PyTorch; no upstream code, weights,
or datasets are included. Run only on archived, completed candles.
"""
import argparse
import json
import math
from pathlib import Path


def validate_and_split(dataset, minimum=180):
    """Validate timestamps and construct non-overlapping label-time splits.

    Fail closed on mixed sources, identity, horizons, invalid sequences or
    future-label crossings. Never randomly split overlapping time windows.
    """
    if dataset.get("status") != "research_only_untrained":
        raise ValueError("unexpected dataset status")
    shape = dataset.get("feature_shape")
    if not (isinstance(shape, list) and len(shape) == 2 and
            type(shape[0]) is int and shape[0] >= 5 and shape[1] == 5):
        raise ValueError("unexpected OHLCV feature shape")
    records = dataset.get("rows") or []
    if len(records) < minimum:
        raise ValueError("insufficient labeled windows")
    rows = sorted(records, key=lambda r: r["decision_ms"])
    keys = ("symbol", "price_source", "seconds", "lookback_bars", "horizon_bars")
    identities = {tuple(r.get(k) for k in keys) for r in rows}
    if len(identities) != 1:
        raise ValueError("mixed market, source or horizon")
    identity = tuple(dataset.get(k) for k in keys)
    if identities != {identity}:
        raise ValueError("dataset metadata mismatch")
    seen=set()
    for row in rows:
        decision=row.get("decision_ms")
        label_end=row.get("label_end_ms")
        if (type(decision) is not int or type(label_end) is not int or
                decision >= label_end or decision in seen):
            raise ValueError("invalid or duplicate timestamps")
        seen.add(decision)
        tensor=row.get("tensor_ohlcv")
        if (row.get("research_only") is not True or not isinstance(tensor,list) or
                len(tensor) != shape[0] or any(
                not isinstance(bar,list) or len(bar)!=5 or
                any(type(v) not in (int,float) or not math.isfinite(v) for v in bar)
                for bar in tensor)):
            raise ValueError("invalid chart input tensor")
        if type(row.get("label_up")) is not int or row["label_up"] not in (0,1):
            raise ValueError("invalid forward label")
        if (type(row.get("future_return_proxy")) not in (int,float)
                or not math.isfinite(row["future_return_proxy"])):
            raise ValueError("invalid forward return")

    n=len(rows)
    v0,t0=int(n*.6),int(n*.8)
    # Purge any training/validation label that overlaps the next split's
    # first decision. This avoids common lookahead on overlapping windows.
    train=[i for i in range(v0) if rows[i]["label_end_ms"] < rows[v0]["decision_ms"]]
    validation=[i for i in range(v0,t0)
                if rows[i]["label_end_ms"] < rows[t0]["decision_ms"]]
    test=list(range(t0,n))
    if min(len(train),len(validation),len(test)) < 25:
        raise ValueError("insufficient data after chronological purge")
    if len({rows[i]["label_up"] for i in train})<2:
        raise ValueError("training labels contain only one class")
    return rows, train, validation, test


def evaluate(dataset, *, epochs=12, cost_bps=10.0):
    if type(epochs) is not int or not 1 <= epochs <= 60:
        raise ValueError("epochs must be between 1 and 60")
    if type(cost_bps) not in (int,float) or not math.isfinite(cost_bps) or cost_bps<0:
        raise ValueError("invalid transaction cost")
    rows,tr,va,te=validate_and_split(dataset)
    try:
        import numpy as np
        import torch
        from torch import nn
    except ImportError as exc:
        raise RuntimeError("Install numpy and torch in an isolated research environment") from exc
    torch.manual_seed(42)
    # Independent small 1D CNN baseline; not copied or loaded from external repo.
    class CandleCNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.net=nn.Sequential(
                nn.Conv1d(5,16,3,padding=1),nn.ReLU(),
                nn.Conv1d(16,16,3,padding=1),nn.ReLU(),
                nn.AdaptiveAvgPool1d(1),nn.Flatten(),nn.Linear(16,1)
            )
        def forward(self,x):
            return self.net(x).squeeze(1)

    x=np.asarray([r["tensor_ohlcv"] for r in rows],dtype=np.float32).transpose(0,2,1)
    y=np.asarray([r["label_up"] for r in rows],dtype=np.float32)
    model=CandleCNN()
    opt=torch.optim.Adam(model.parameters(),lr=.001)
    loss_fn=nn.BCEWithLogitsLoss()
    X=torch.from_numpy(x)
    Y=torch.from_numpy(y)
    best_val=float("inf")
    best_weights=None
    # Only validation controls the selected epoch. Test is evaluated once.
    for _ in range(epochs):
        model.train()
        for start in range(0,len(tr),64):
            batch=tr[start:start+64]
            opt.zero_grad()
            loss=loss_fn(model(X[batch]),Y[batch])
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            val_loss=float(loss_fn(model(X[va]),Y[va]))
            if val_loss < best_val:
                best_val=val_loss
                best_weights={k:v.detach().clone() for k,v in model.state_dict().items()}
    model.load_state_dict(best_weights)
    model.eval()
    with torch.no_grad():
        probs=torch.sigmoid(model(X[te])).numpy()
    truth=y[te]
    accuracy=float(np.mean((probs>=.5)==truth))
    baseline=float(max(np.mean(truth),1-np.mean(truth)))
    # Directional proxy is descriptive, assumes all samples and allows overlap.
    signed=np.where(probs>=.5,1.,-1.)
    forward=np.asarray([rows[i]["future_return_proxy"] for i in te])
    net=signed*forward-cost_bps/10000.0
    return {
        "status":"research_only_not_deployed",
        "model":"kaos_original_ohlcv_conv1d",
        "symbol":rows[0]["symbol"],"source":rows[0]["price_source"],
        "seconds":rows[0]["seconds"],"lookback_bars":rows[0]["lookback_bars"],
        "horizon_bars":rows[0]["horizon_bars"],
        "split_samples":{"train":len(tr),"validation":len(va),"test":len(te)},
        "train_last_label_ms":rows[tr[-1]]["label_end_ms"],
        "validation_first_decision_ms":rows[va[0]]["decision_ms"],
        "validation_last_label_ms":rows[va[-1]]["label_end_ms"],
        "test_first_decision_ms":rows[te[0]]["decision_ms"],
        "validation_best_log_loss":best_val,
        "test_accuracy":accuracy,"test_majority_baseline_accuracy":baseline,
        "test_all_direction_net_return_mean_proxy":float(np.mean(net)),
        "test_all_direction_net_win_fraction_proxy":float(np.mean(net>0)),
        "cost_bps_assumed":cost_bps,
        "notices":[
            "Test results are descriptive and do not establish a real trading edge",
            "Overlapping theoretical decisions are not executable trade simulations",
            "Proxy price returns omit real fills, latency, spread variation and slippage",
            "No screenshot interpretation, production model, signal or order permissions",
        ],
    }


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--epochs",type=int,default=12)
    parser.add_argument("--cost-bps",type=float,default=10.)
    args=parser.parse_args()
    report=evaluate(json.loads(Path(args.input).read_text()),
                    epochs=args.epochs,cost_bps=args.cost_bps)
    Path(args.output).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"test_accuracy":report["test_accuracy"]}))
