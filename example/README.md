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
example/.venv/bin/python example/django_demo/manage.py \
  mcp_call users.get_user_name_by_email '{"email":"alice@example.com"}'
```

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
Then use a second terminal from the repository root:

```bash
example/.venv/bin/python example/openai_agent.py
```

The script discovers the MCP tool schema from localhost, gives it to the OpenAI Responses API,
executes the model's tool request through MCP, and prints the final answer.
