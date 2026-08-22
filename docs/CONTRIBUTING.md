# Contributing

Keep changes scoped to the current development phase in `context.md`. Before opening a change:

1. Run the relevant lint, type-check, and test commands.
2. Do not commit `.env`, API keys, passwords, tokens, or local database data.
3. Add tests with backend logic and document user-visible or architectural changes.
4. Keep route handlers thin; place reusable business logic in the intended module boundary.
