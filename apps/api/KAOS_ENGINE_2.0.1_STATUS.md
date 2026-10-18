# KAOS Trading Engine 2.0.1 — Durable Paper Journal

Added `kaos_paper_journal.py` and `kaos_durable_paper_pipeline.py`: SQLite-backed transactional paper order reservations scoped by user/broker/account/client order ID. Successful paper submission reports survive process restarts; unfinished/ambiguous reservations remain UNKNOWN and require manual reconciliation rather than blind replay. The pipeline remains **paper-only**.

Fixed the paper adapter to scope order IDs by account, preventing cross-account report identity collisions. Added six tests for restart replay, conflicting ID, unknown reservation, risk-before-reservation, account isolation, and live adapter rejection.

61 offline unittest cases passed in this build. No Coinbase or other live broker integration was executed; no production deployment was performed. This is not a production-ready release. SQLite journal is intended for single-host paper development, not as the final distributed MongoDB live reservation system.
