# KAOS 1.6.46 — Native XGBoost trainer integration
- Added Windows Python/XGBoost Chrome native messaging host with explicit installer and Chrome extension ID authorization.
- Fixed native host name to valid lowercase `com.kaos.aidata` in extension and Windows registry manifest.
- Native host trains from actual labeled 104-feature KAOS rows projected to 88 native wire features, produces JavaScript tree format, and reports chronological 20% holdout accuracy.
- Not a pretrained model: historic candle replay features cannot be safely substituted for the extension's 104-feature vectors. No evidence of 65% win rate. Does not enable real-money AI execution.
- Windows installation must be performed locally; it cannot be installed on the user's computer from this environment.
