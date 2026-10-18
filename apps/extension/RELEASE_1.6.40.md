# KAOS Trading Bot 1.6.40

- Fixed `ReferenceError: isRunning is not defined`.
- Root cause: OpenAI shadow timer was appended outside the main content-engine closure while referencing closure-local engine state.
- Added a read-only snapshot bridge inside the engine closure and changed the OpenAI timer to consume that bridge.
- Retains the 1.6.39 Dashboard strategy selector fix.
- OpenAI remains shadow/learning only.
