# Django MCP end-to-end example

This tracked example uses Django's built-in auth `User` model and an editable checkout of
`django-native-mcp`. Its virtual environment, SQLite database, caches, and compiled files remain
ignored by Git.

## 1. Create the example environment

From the repository root:

```bash
uv venv example/.venv --python 3.12
uv pip install \
  --python example/.venv/bin/python \
  -e . \
  -r example/requirements.txt
```

## 2. Prepare the database

From the repository root:

```bash
example/.venv/bin/python example/django_demo/manage.py migrate
example/.venv/bin/python example/django_demo/manage.py seed_demo_user
example/.venv/bin/python example/django_demo/manage.py mcp_list
```

The seed command grants Alice the native Django `auth.view_user` permission required by
`@shared_tool(permissions=["auth.view_user"])`. Group permissions and active superusers also work
through Django's configured authorization backends.

Create a local bearer token and keep it in the current shell environment (the command does not
print it):

```bash
export MCP_TOKEN="$(example/.venv/bin/python example/django_demo/manage.py shell -c \
  'from django.contrib.auth import get_user_model; from django_native_mcp.models import MCPToken; user = get_user_model().objects.get(username="alice"); token, _ = MCPToken.objects.get_or_create(user=user); print(token.key)' \
  --verbosity 0)"
```

Do not commit the token. Re-run this command in the terminal used for the client if necessary.
The endpoint uses default bearer authentication. Missing/invalid tokens receive HTTP 401; a
valid token whose user lacks `auth.view_user` receives a tool error with `Permission denied.`.
Protected tools cannot be called with `mcp_call` or stdio, because those transports have no
HTTP-authenticated user.

## 3. Start Django and MCP

From the repository root:

```bash
cd example/django_demo
../.venv/bin/python -m \
uvicorn config.asgi:application --host 127.0.0.1 --port 8001
```

The Django application is available at `http://127.0.0.1:8001/`, and its Streamable HTTP MCP
endpoint is `http://127.0.0.1:8001/mcp`.

## 4. Run the OpenAI agent

Open `example/openai_agent.py` and set its `OPENAI_API_KEY` placeholder. Never commit a real key.
Set `MCP_TOKEN` in the client terminal as described above. Then run from the repository root:

```bash
example/.venv/bin/python example/openai_agent.py
```

The script discovers the MCP tool schema from localhost, gives it to the OpenAI Responses API,
executes the model's tool request through MCP, and prints the final answer.

## 5. Verify permissions without OpenAI

With the server running and `MCP_TOKEN` exported, run from the repository root:

```bash
example/.venv/bin/python - <<'PYTHON'
import asyncio
import os

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {os.environ['MCP_TOKEN']}"}
    ) as http:
        async with Client(streamable_http_client(
            "http://127.0.0.1:8001/mcp", http_client=http
        )) as client:
            result = await client.call_tool(
                "users.get_user_name_by_email", {"email": "alice@example.com"}
            )
            print(result)


asyncio.run(main())
PYTHON
```

The result contains Alice Anderson. To try a denied call, create a token for an active ordinary
user with no `auth.view_user` permission and repeat with that token. The tool remains listed,
but its execution is denied. User permissions can be managed in Django admin.
