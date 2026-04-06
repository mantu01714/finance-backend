"""
Dashboard / analytics routes.

Access control:
  GET /dashboard/summary  → analyst, admin  (viewers are excluded per spec)
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_analyst_or_above
from app.models.models import User
from app.schemas.schemas import DashboardSummary
from app.services.dashboard import get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    date_from: date | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    date_to: date | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst_or_above),
):
    """
    Return aggregated financial summary for the dashboard.
    Optionally scoped to a date range.
    Accessible by analyst and admin roles only.
    """
    return get_dashboard_summary(db, date_from=date_from, date_to=date_to)
