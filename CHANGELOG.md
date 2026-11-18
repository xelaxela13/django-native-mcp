# Changelog

## 0.1.3

- Add optional `permissions` to `@shared_tool` and `@app.tool`.
- Enforce every required permission using Django's async `user.ahas_perms()` before tool execution, supporting Django authorization backends, user/group permissions and superusers.
- Deny protected tool calls without an authenticated request user, including public HTTP, stdio and in-process calls. Tool listing and input/output schemas remain unchanged.
- Update the end-to-end example with bearer authentication, `auth.view_user`, and token configuration through `MCP_TOKEN`.

No database migration is required for this release. Tools without declared permissions retain their existing behavior.
