# KAOS -> Devin Handoff (2026-10-18)
This handoff includes the most relevant KAOS artifacts recoverable from the ChatGPT Library in this session. It is NOT a confirmed complete production source tree, nor proof that the newest stored ZIP is the currently deployed website or Chrome extension. Ask the owner to upload any newer Emergent/HackerAI/cPanel/GitHub work before deciding the baseline.

START HERE: `DEVIN_MASTER_PROMPT.txt`. Then `MANIFEST.json`.

Contents: `source_snapshots/` (individual unmerged historical ZIPs, preserved), `data/` (historical KAOS exported OHLC/diagnostic data from earlier conversation), `DEVIN_MASTER_PROMPT.txt`, and `MANIFEST.json`.
Known `.env` and `.env.backup` entries inside api.tradingwithkaos.com.zip are removed. Other embedded secrets may still exist; run independent secret scan before uploading to any repository. Some archives contain binaries or generated assets. Audit before deploying.

Outstanding: actual production deployment access, DNS/domain configuration, Stripe project and products, broker credentials, active repo and remote branch, latest source not uploaded to Library, database schema/migrations, licensing agreements. NEVER ask user to paste credentials in chat.
