from pathlib import Path
from tempfile import gettempdir

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = "tests-only"
USE_TZ = True
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "django_native_mcp",
    "tests.test_apps.inventory.apps.InventoryConfig",
    "tests.test_apps.empty.apps.EmptyConfig",
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(Path(gettempdir()) / "django-native-mcp-tests.sqlite3"),
    }
}
MIGRATION_MODULES = {"inventory": None}
DJANGO_NATIVE_MCP = {"APP": "tests.configured:app", "AUTODISCOVER": True}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
