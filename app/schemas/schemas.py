"""
Pydantic schemas for request validation and response serialization.
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.models import RecordType, UserRole


# ──────────────────────────────────────────────
# Auth schemas
# ──────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


# ──────────────────────────────────────────────
# User schemas
# ──────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.viewer

    @field_validator("username")
    @classmethod
    def no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError("Username must not contain spaces")
        return v.lower()


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Financial record schemas
# ──────────────────────────────────────────────

class RecordCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Must be a positive number")
    type: RecordType
    category: str = Field(..., min_length=1, max_length=64)
    record_date: date
    notes: str | None = Field(default=None, max_length=1000)


class RecordUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    type: RecordType | None = None
    category: str | None = Field(default=None, min_length=1, max_length=64)
    record_date: date | None = None
    notes: str | None = None


class RecordOut(BaseModel):
    id: int
    amount: float
    type: RecordType
    category: str
    record_date: date
    notes: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedRecords(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RecordOut]


# ──────────────────────────────────────────────
# Dashboard / summary schemas
# ──────────────────────────────────────────────

class CategoryTotal(BaseModel):
    category: str
    total: float
    count: int


class MonthlyTrend(BaseModel):
    year: int
    month: int
    income: float
    expense: float
    net: float


class DashboardSummary(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    record_count: int
    income_by_category: list[CategoryTotal]
    expense_by_category: list[CategoryTotal]
    monthly_trends: list[MonthlyTrend]
    recent_records: list[RecordOut]
