from django.contrib import admin

from .models import MCPToken


@admin.register(MCPToken)
class MCPTokenAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("key", "user", "created", "last_used", "expires")
    readonly_fields = ("key", "created", "last_used")
    search_fields = ("key", "user__username", "user__email")
    raw_id_fields = ("user",)
