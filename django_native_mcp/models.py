import binascii
import os
from typing import Any

from django.conf import settings
from django.db import models


def generate_token_key() -> str:
    """Generate a 40-character hexadecimal token, matching DRF Token."""
    return binascii.hexlify(os.urandom(20)).decode()


class MCPToken(models.Model):
    """A bearer token used to authenticate an MCP HTTP client."""

    key = models.CharField(max_length=40, primary_key=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    expires = models.DateTimeField(null=True, blank=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.key:
            self.key = generate_token_key()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.key
