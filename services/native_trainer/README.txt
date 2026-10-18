WINDOWS SETUP: Unzip the entire release to a permanent folder. In chrome://extensions enable Developer mode and note KAOS extension ID. Open PowerShell in native_trainer and run:
  powershell -ExecutionPolicy Bypass -File .\install_windows.ps1 -ExtensionId YOUR_32_CHARACTER_EXTENSION_ID
Requires Python 3.10+ and network access to install numpy/xgboost. Restart Chrome. Do not move folder after registration. Only works with Google Chrome's native messaging registry; Edge requires a separate registration.
The trainer trains from the extension's real 104-feature labeled samples (88-feature native wire projection), with chronological holdout. It DOES NOT bootstrap an already-trained 104-feature model from raw candle data, does not prove 65% win rate, and does not authorize live trades.
