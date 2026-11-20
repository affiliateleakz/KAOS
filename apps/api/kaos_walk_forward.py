"""KAOS predeclared expanding-window walk-forward robustness check.

Runs only on real archived inputs supplied by the owner-only endpoint. Multiple
folds are descriptive robustness checks, not an untouched final holdout or
permission to choose the best-performing model after seeing the test.
"""
from math import isfinite
from kaos_multifactor_baseline import (
    dataset, train_logistic, metrics, evidence_coverage,
    TECHNICAL_INDICES, ALL_INDICES,
)


def walk_forward(candles, observations, *, symbol,asset_class,seconds,source,
                 horizon=5,cost_bps=10.0,folds=3,min_train=75,min_test=20):
    if type(folds) is not int or folds not in (2,3,4,5):
        raise ValueError("folds must be 2..5")
    if type(min_train) is not int or min_train<50 or type(min_test) is not int or min_test<15:
        raise ValueError("insufficient minimum partition size")
    if type(cost_bps) not in (int,float) or not isfinite(cost_bps) or not 0<=cost_bps<=250:
        raise ValueError("Invalid cost")
    data=dataset(candles,observations,symbol=symbol,asset_class=asset_class,
                 seconds=seconds,source=source,horizon=horizon)
    n=len(data)
    # A fixed expanding training window followed by disjoint test windows.
    # The first half is training-only. No validation-based tuning in this
    # descriptive experiment. Number of folds and parameters are predeclared.
    start=max(min_train,n//2)
    window=(n-start)//folds
    if window<min_test:
        return {"status":"insufficient_walk_forward_history","samples":n,
                "research_only":True,"folds_completed":0,"orders_enabled":False}
    results=[]
    for fold in range(folds):
        first=start+fold*window
        last=start+(fold+1)*window if fold<folds-1 else n
        boundary=data[first]["decision_ms"]
        train=[r for r in data[:first] if r["label_end_ms"]<=boundary]
        test=data[first:last]
        if len(train)<min_train or len(test)<min_test:
            return {"status":"insufficient_walk_forward_history","samples":n,
                    "research_only":True,"folds_completed":len(results),
                    "orders_enabled":False}
        technical=train_logistic(train,feature_indices=TECHNICAL_INDICES)
        technical_score=metrics(technical,test,cost_bps=cost_bps)
        train_coverage=evidence_coverage(train)
        test_coverage=evidence_coverage(test)
        available=(train_coverage["samples_with_observed_evidence"]>=min_test and
                   test_coverage["samples_with_observed_evidence"]>=min_test)
        combined_score=None
        if available:
            combined=train_logistic(train,feature_indices=ALL_INDICES)
            combined_score=metrics(combined,test,cost_bps=cost_bps)
        results.append({
            "fold":fold+1,
            "train_samples":len(train),"test_samples":len(test),
            "train_last_outcome_ms":train[-1]["label_end_ms"],
            "test_first_decision_ms":test[0]["decision_ms"],
            "test_last_outcome_ms":test[-1]["label_end_ms"],
            "train_evidence_coverage":train_coverage,
            "test_evidence_coverage":test_coverage,
            "multifactor_comparison_available":available,
            "technical_only":technical_score,"multifactor":combined_score,
            "multifactor_minus_technical_accuracy":round(
                combined_score["accuracy_all"]-technical_score["accuracy_all"],5
            ) if combined_score else None,
            "technical_minus_multifactor_brier":round(
                technical_score["brier_score"]-combined_score["brier_score"],6
            ) if combined_score else None,
        })
    # Require evidence coverage in EVERY fold to make any robust-improvement
    # claim. Still never claim predictive success based solely on these runs.
    comparable=[r for r in results if r["multifactor_comparison_available"]]
    all_comparable=len(comparable)==folds
    improvements=sum(r["multifactor_minus_technical_accuracy"]>0 for r in comparable)
    brier_improvements=sum(r["technical_minus_multifactor_brier"]>0 for r in comparable)
    return {
        "status":"research_walk_forward_completed",
        "symbol":symbol,"asset_class":asset_class,"seconds":seconds,
        "source":source,"horizon_bars":horizon,"cost_bps_assumed":cost_bps,
        "samples":n,"folds_completed":len(results),
        "folds_with_usable_intelligence":len(comparable),
        "all_folds_comparable":all_comparable,
        "accuracy_improvement_fold_count":improvements if all_comparable else None,
        "brier_improvement_fold_count":brier_improvements if all_comparable else None,
        "independent_validation_passed":False,
        "folds":results,
        "research_only":True,"orders_enabled":False,"options_validated":False,
        "notes":[
            "Expanding past-only training, disjoint chronological test folds",
            "Historical outcomes cannot be replayed as live execution or option returns",
            "Multiple checked folds do not replace an independent untouched future test",
            "Sparse first-seen news/social evidence prevents an all-fold comparison",
        ],
    }
