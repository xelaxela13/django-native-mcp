from django_native_mcp import shared_tool

from .models import Item


@shared_tool
async def get_item(item_id: int) -> dict[str, int | str]:
    """Return an inventory item."""
    item = await Item.objects.aget(pk=item_id)
    return {"id": item.pk, "name": item.name}
