# KAOS Trading Bot 1.4.7

Cloud/server: restores kaos-cloud.js, kaos-cloud-ui.js, and kaos-cloud-ui.css byte-for-byte
from the user-supplied 1.2.0 build. Removes the experimental 1.4.x cookie/session auth path
and returns KAOS_STARTUP to the direct 1.2 behavior.

Build Strategy: physically moves all known Strategy Builder/editor containers out of Charts
into the dedicated Build Strategy page, including dynamically-created builder containers.

B32.24 trading, Pocket Option bridge, candles and Candidate 7B are unchanged.
