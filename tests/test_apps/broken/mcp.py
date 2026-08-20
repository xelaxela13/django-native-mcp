from django_native_mcp import shared_tool


@shared_tool
async def partial_tool() -> None:
    pass


raise RuntimeError("broken mcp module")
