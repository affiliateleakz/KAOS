import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('commerce_check',Path(__file__).resolve().parents[1]/'check_commerce_readiness.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)


def test_live_readiness_never_accepts_empty_or_test_credentials():
    assert not any(check.configuration_checks({}).values())
    result=check.configuration_checks({'STRIPE_SECRET_KEY':'sk_test_fixture','STRIPE_CONNECT_SECRET_KEY':'sk_test_fixture'})
    assert not result['Stripe live membership key configured']
    assert not result['Stripe Connect live key configured']


def test_configuration_report_contains_only_checks_not_keys():
    report=check.configuration_checks({'STRIPE_SECRET_KEY':'sk_live_fixture','STRIPE_WEBHOOK_SECRET':'whsec_fixture',
        'STRIPE_CONNECT_SECRET_KEY':'sk_live_fixture','KAOS_STRIPE_CONNECT_ENABLED':'true','KAOS_AFFILIATE_TXN_MODE':'required'})
    assert all(report.values())
    assert all(isinstance(value,bool) for value in report.values())
    assert 'sk_live' not in str(report)
