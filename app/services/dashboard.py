"""
Dashboard service: all aggregation and summary logic lives here,
keeping the router thin and the business logic testable.
"""
from collections import defaultdict
from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import FinancialRecord, RecordType
from app.schemas.schemas import CategoryTotal, DashboardSummary, MonthlyTrend, RecordOut


def get_dashboard_summary(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
) -> DashboardSummary:
    """
    Compute a full dashboard summary.

    Optionally scoped to a date range.
    All values exclude soft-deleted records.
    """
    base_query = db.query(FinancialRecord).filter(FinancialRecord.is_deleted.is_(False))

    if date_from:
        base_query = base_query.filter(FinancialRecord.record_date >= date_from)
    if date_to:
        base_query = base_query.filter(FinancialRecord.record_date <= date_to)

    records: list[FinancialRecord] = base_query.order_by(
        FinancialRecord.record_date.desc(), FinancialRecord.id.desc()
    ).all()

    # ── Totals ─────────────────────────────────────────────────────────────
    total_income: float = 0.0
    total_expenses: float = 0.0

    income_by_cat: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    expense_by_cat: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    monthly: dict[tuple[int, int], dict] = defaultdict(
        lambda: {"income": 0.0, "expense": 0.0}
    )

    for r in records:
        key = (r.record_date.year, r.record_date.month)
        if r.type == RecordType.income:
            total_income += r.amount
            income_by_cat[r.category]["total"] += r.amount
            income_by_cat[r.category]["count"] += 1
            monthly[key]["income"] += r.amount
        else:
            total_expenses += r.amount
            expense_by_cat[r.category]["total"] += r.amount
            expense_by_cat[r.category]["count"] += 1
            monthly[key]["expense"] += r.amount

    # ── Shape output ───────────────────────────────────────────────────────
    income_categories = [
        CategoryTotal(category=cat, total=round(v["total"], 2), count=v["count"])
        for cat, v in sorted(income_by_cat.items(), key=lambda x: -x[1]["total"])
    ]
    expense_categories = [
        CategoryTotal(category=cat, total=round(v["total"], 2), count=v["count"])
        for cat, v in sorted(expense_by_cat.items(), key=lambda x: -x[1]["total"])
    ]

    trends = [
        MonthlyTrend(
            year=year,
            month=month,
            income=round(vals["income"], 2),
            expense=round(vals["expense"], 2),
            net=round(vals["income"] - vals["expense"], 2),
        )
        for (year, month), vals in sorted(monthly.items())
    ]

    recent = [RecordOut.model_validate(r) for r in records[:10]]

    return DashboardSummary(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        net_balance=round(total_income - total_expenses, 2),
        record_count=len(records),
        income_by_category=income_categories,
        expense_by_category=expense_categories,
        monthly_trends=trends,
        recent_records=recent,
    )
