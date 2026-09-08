from __future__ import annotations

import json

import pytest


@pytest.fixture()
def tools():
    from app.tools.registry import Tools

    return Tools(telegram_id=999)


def test_tools_registry_builds(tools):
    schemas = tools.schemas()
    assert len(schemas) >= 20
    names = [s.name for s in schemas]
    for required in [
        "search_products",
        "create_bill",
        "add_bill_item",
        "calculate_bill",
        "finalize_bill",
        "receive_stock",
        "record_credit_payment",
        "generate_invoice_pdf",
        "generate_analysis_pptx",
        "set_preference",
    ]:
        assert required in names, f"missing tool: {required}"


def test_tools_schemas_are_valid_json_schema(tools):
    for s in tools.schemas():
        assert s.parameters.get("type") == "object"
        assert isinstance(s.parameters.get("properties"), dict)
        json.dumps(s.parameters)  # must be serializable


def test_unknown_tool_returns_error(tools):
    result = tools.call("does_not_exist", {})
    assert "error" in result
    assert "unknown tool" in result["error"]


def test_preference_tools_bound_to_user(tools):
    # reflecting the ctx binding used by preference handlers
    assert tools.ctx.telegram_id == 999