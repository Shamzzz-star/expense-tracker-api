"""Settings for the test suite: a throwaway secret key and no auth rate limiting."""

import os

if not os.environ.get("DJANGO_SECRET_KEY"):
    os.environ["DJANGO_SECRET_KEY"] = "test-only-insecure-key"

from .settings import *  # noqa: E402,F403

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {"auth": None}  # noqa: F405

# Tests don't run collectstatic, so there is no manifest for the production storage to read.
STORAGES = {  # noqa: F405
    **STORAGES,  # noqa: F405
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
