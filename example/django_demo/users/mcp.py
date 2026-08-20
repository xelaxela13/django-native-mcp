from django.contrib.auth import get_user_model

from django_native_mcp import shared_tool


@shared_tool
async def get_user_name_by_email(email: str) -> dict[str, bool | str]:
    """Find a Django user by email and return the user's display name."""
    user_model = get_user_model()
    user = await user_model.objects.filter(email__iexact=email).order_by("pk").afirst()

    if user is None:
        return {
            "found": False,
            "email": email,
            "name": "",
        }

    return {
        "found": True,
        "email": user.email,
        "name": user.get_full_name().strip() or user.get_username(),
    }
