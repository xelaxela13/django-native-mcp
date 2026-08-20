import sys
from collections.abc import Iterator

import pytest

from django_native_mcp._shared import shared_tool_store

RELOADABLE_MODULES = (
    "tests.configured",
    "tests.test_apps.inventory.mcp",
    "tests.test_apps.broken.mcp",
)


@pytest.fixture(autouse=True)
def isolate_shared_tools() -> Iterator[None]:
    snapshot = shared_tool_store.snapshot()
    for module in RELOADABLE_MODULES:
        sys.modules.pop(module, None)
    yield
    shared_tool_store.restore(snapshot)
    for module in RELOADABLE_MODULES:
        sys.modules.pop(module, None)
