import pytest
from django.test import override_settings

from django_native_mcp.checks import check_django_native_mcp
from django_native_mcp.conf import load_configured_app
from django_native_mcp.exceptions import AppNotConfigured


def test_load_configured_app_and_autodiscovery() -> None:
    app = load_configured_app()
    assert app.name == "configured"
    assert set(app.tools) == {"system.echo", "inventory.get_item"}


@override_settings(DJANGO_NATIVE_MCP={})
def test_empty_configuration_is_optional_for_system_checks() -> None:
    assert check_django_native_mcp() == []
    with pytest.raises(AppNotConfigured):
        load_configured_app()


@override_settings(DJANGO_NATIVE_MCP={"AUTODISCOVER": True})
def test_check_reports_missing_app_path() -> None:
    errors = check_django_native_mcp()
    assert [error.id for error in errors] == ["django_native_mcp.E001"]


@override_settings(DJANGO_NATIVE_MCP={"APP": "tests.missing:app"})
def test_check_reports_invalid_import() -> None:
    errors = check_django_native_mcp()
    assert [error.id for error in errors] == ["django_native_mcp.E002"]
