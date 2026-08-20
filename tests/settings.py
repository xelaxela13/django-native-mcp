from pathlib import Path
from tempfile import gettempdir

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = "tests-only"
USE_TZ = True
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django_native_mcp",
    "tests.test_apps.inventory.apps.InventoryConfig",
    "tests.test_apps.empty.apps.EmptyConfig",
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
