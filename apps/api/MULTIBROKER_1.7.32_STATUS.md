# KAOS Multi-Broker v1.7.32 — development

Built on v1.7.31. Adds `kaos_broker_registry.py` fail-closed adapter registry and `kaos_paper_adapter.py` simulated broker adapter, with 9 new tests in `test_kaos_broker_registry.py`. The registry validates broker identity, order capabilities, expiry and source position rules, and report identity. Live order dispatch is explicitly blocked, including for adapters that advertise live capabilities, pending server-owned authorization, reservations and risk controls. Paper orders return SUBMITTED and do not pretend to be exchange fills.

Verification: 18 broker tests passed (9 prior + 9 new), Python source compilation and ZIP integrity. No external broker connected, no exchange orders placed, and no Asura deployment. The Coinbase automatic strategy-to-order and exit execution work remains incomplete; other brokers require separate authenticated adapters, exchange integration and testing.

Do not deploy over production or enable live orders.
