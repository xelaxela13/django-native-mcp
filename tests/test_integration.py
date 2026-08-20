import pytest

from django_native_mcp import MCP
from django_native_mcp.testing import MCPTestClient
from tests.test_apps.inventory.models import Item


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_mcp_client_to_async_django_orm() -> None:
    item = await Item.objects.acreate(name="Widget")
    app = MCP("backend")
    app.autodiscover_tools(["tests.test_apps.inventory"])

    async with MCPTestClient(app) as client:
        result = await client.call_tool("inventory.get_item", {"item_id": item.pk})

    assert result.structured_content == {"id": item.pk, "name": "Widget"}
