"""
Financial records routes.

Access control:
  GET  /records           → viewer, analyst, admin
  GET  /records/{id}      → viewer, analyst, admin
  POST /records           → analyst, admin
  PUT  /records/{id}      → analyst, admin
  DELETE /records/{id}    → admin only (soft delete)
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_active_user,
    require_admin,
    require_analyst_or_above,
)
from app.models.models import FinancialRecord, RecordType, User
from app.schemas.schemas import PaginatedRecords, RecordCreate, RecordOut, RecordUpdate

router = APIRouter(prefix="/records", tags=["Financial Records"])


def _get_record_or_404(record_id: int, db: Session) -> FinancialRecord:
    record = db.get(FinancialRecord, record_id)
    if not record or record.is_deleted:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.get("", response_model=PaginatedRecords)
def list_records(
    # Filters
    type: RecordType | None = Query(default=None, description="Filter by income/expense"),
    category: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    # Pagination
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),  # all active roles can read
):
    """
    List financial records with optional filters and pagination.
    All active users may access this endpoint.
    """
    query = db.query(FinancialRecord).filter(FinancialRecord.is_deleted.is_(False))

    if type:
        query = query.filter(FinancialRecord.type == type)
    if category:
        query = query.filter(FinancialRecord.category.ilike(f"%{category}%"))
    if date_from:
        query = query.filter(FinancialRecord.record_date >= date_from)
    if date_to:
        query = query.filter(FinancialRecord.record_date <= date_to)

    total = query.count()
    items = (
        query.order_by(FinancialRecord.record_date.desc(), FinancialRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedRecords(total=total, page=page, page_size=page_size, items=items)


@router.get("/{record_id}", response_model=RecordOut)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    return _get_record_or_404(record_id, db)


@router.post("", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: RecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst_or_above),
):
    """Create a new financial record (analyst or admin only)."""
    record = FinancialRecord(**payload.model_dump(), created_by=current_user.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/{record_id}", response_model=RecordOut)
def update_record(
    record_id: int,
    payload: RecordUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst_or_above),
):
    """Update a financial record (analyst or admin only)."""
    record = _get_record_or_404(record_id, db)
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Soft-delete a record (admin only)."""
    record = _get_record_or_404(record_id, db)
    record.is_deleted = True
    db.commit()
