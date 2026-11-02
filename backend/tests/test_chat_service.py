"""Smoke tests for the remediation chat module."""

from app.services import chat  # noqa: F401 — ensures the module imports cleanly
from app.api.routes.findings import router


def test_findings_router_has_chat_routes() -> None:
    paths = {route.path for route in router.routes}  # type: ignore[attr-defined]
    assert any("chat" in p for p in paths)


def test_chat_service_exports() -> None:
    assert callable(chat.get_finding_for_user)
    assert callable(chat.get_chat_history)
    assert callable(chat.send_chat_message)
