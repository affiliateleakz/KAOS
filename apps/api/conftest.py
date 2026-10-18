import os

# Several suites wipe collections; never let them run against a dev or production database.
if not os.environ.get("DB_NAME", "kaos_test").endswith("_test"):
    os.environ["DB_NAME"] = "kaos_test"
