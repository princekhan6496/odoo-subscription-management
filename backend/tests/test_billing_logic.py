from datetime import date
from app.api.v1.operations import next_date, money

def test_monthly_date_handles_month_end():
    assert next_date(date(2026, 1, 31), "monthly") == date(2026, 2, 28)

def test_yearly_date_handles_leap_day():
    assert next_date(date(2024, 2, 29), "yearly") == date(2025, 2, 28)

def test_daily_and_weekly_intervals():
    assert next_date(date(2026, 10, 31), "daily") == date(2026, 11, 1)
    assert next_date(date(2026, 10, 31), "weekly") == date(2026, 11, 7)

def test_money_rounding():
    from decimal import Decimal
    assert money("10.235") == Decimal("10.24")


def test_month_end_anchor_is_preserved_across_short_months():
    assert next_date(date(2026, 2, 28), "monthly", 31) == date(2026, 3, 31)
    assert next_date(date(2026, 2, 28), "monthly", 30) == date(2026, 3, 30)
    assert next_date(date(2027, 2, 28), "yearly", 29) == date(2028, 2, 29)
