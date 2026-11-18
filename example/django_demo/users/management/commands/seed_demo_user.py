from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update the local MCP demo user."

    def handle(self, *args: object, **options: object) -> None:
        del args, options
        user_model = get_user_model()
        user, created = user_model.objects.update_or_create(
            username="alice",
            defaults={
                "email": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Anderson",
            },
        )
        action = "Created" if created else "Updated"
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="auth", codename="view_user")
        )
        self.stdout.write(self.style.SUCCESS(f"{action} demo user: {user.email}"))
