from __future__ import annotations

import pytest


def test_gst_service_calculation():
    from app.services.gst import GstLine, GstService

    items = [
        GstLine("Maggi", 6, 14.0, 12),       # 84.00, GST 10.08
        GstLine("Atta 5kg", 1, 230.0, 5),    # 230.00, GST 11.50
    ]
    result = GstService.calculate(items)

    assert result.subtotal == 314.0
    assert round(result.gst_amount, 2) == 21.58
    assert round(result.total, 2) == 335.58
    assert result.breakdown[12] == 10.08
    assert result.breakdown[5] == 11.50


def test_gst_zero_rate():
    from app.services.gst import GstLine, GstService

    result = GstService.calculate([GstLine("Milk", 2, 62.0, 0)])
    assert result.gst_amount == 0
    assert result.total == 124.0