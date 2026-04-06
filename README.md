# Finance Dashboard Backend

A role-based finance dashboard API built with **FastAPI**, **SQLAlchemy**, and **SQLite**.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | FastAPI | Modern, async-ready, auto-generates OpenAPI docs |
| ORM | SQLAlchemy 2.0 | Type-safe, expressive, supports any SQL database |
| Database | SQLite (default) | Zero-config for local dev; swap to Postgres for production |
| Auth | JWT (python-jose) | Stateless, standard, easy to scale |
| Passwords | bcrypt (passlib) | Industry-standard hashing |
| Validation | Pydantic v2 | Tight integration with FastAPI, fast |

---

## Project Structure

```
finance-backend/
├── app/
│   ├── core/
│   │   ├── config.py         # Settings (reads from .env)
│   │   ├── database.py       # SQLAlchemy engine + session
│   │   ├── security.py       # Password hashing + JWT helpers
│   │   └── dependencies.py   # Auth + RBAC FastAPI dependencies
│   ├── models/
│   │   └── models.py         # ORM models: User, FinancialRecord
│   ├── schemas/
│   │   └── schemas.py        # Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py           # POST /auth/register, /auth/login
│   │   ├── users.py          # CRUD /users
│   │   ├── records.py        # CRUD /records + filters + pagination
│   │   └── dashboard.py      # GET /dashboard/summary
│   ├── services/
│   │   └── dashboard.py      # Aggregation logic (separated from router)
│   └── main.py               # App factory, middleware, router wiring
├── tests/
│   └── test_api.py           # Integration tests (37 test cases)
├── seed.py                   # Demo data seeder
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env to set your SECRET_KEY (required for production)
```

### 3. Start the server

```bash
.venv\Scripts\uvicorn.exe app.main:app --reload
```

The API will be live at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### 4. Seed demo data (optional)

```bash
python seed.py
```

This creates three demo users:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Analyst | `analyst` | `analyst123` |
| Viewer | `viewer` | `viewer123` |

### 5. Run tests

```bash
pytest tests/ -v
```

---

## API Reference

All protected routes require a `Bearer` token in the `Authorization` header.

### Auth

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/auth/register` | Register a new user | Public |
| `POST` | `/auth/login` | Get JWT token | Public |

**Register:**
```json
POST /auth/register
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "mypassword",
  "role": "viewer"
}
```

**Login** (OAuth2 form, not JSON):
```bash
curl -X POST /auth/login \
  -d "username=alice&password=mypassword"
# Returns: { "access_token": "...", "token_type": "bearer" }
```

---

### Users

| Method | Path | Description | Required Role |
|---|---|---|---|
| `GET` | `/users/me` | My profile | Any |
| `GET` | `/users` | List all users | Admin |
| `GET` | `/users/{id}` | Get user by ID | Admin |
| `POST` | `/users` | Create user | Admin |
| `PUT` | `/users/{id}` | Update user | Admin |
| `DELETE` | `/users/{id}` | Deactivate user | Admin |

---

### Financial Records

| Method | Path | Description | Required Role |
|---|---|---|---|
| `GET` | `/records` | List records (filtered + paginated) | Any |
| `GET` | `/records/{id}` | Get one record | Any |
| `POST` | `/records` | Create record | Analyst, Admin |
| `PUT` | `/records/{id}` | Update record | Analyst, Admin |
| `DELETE` | `/records/{id}` | Soft-delete record | Admin |

**Query parameters for `GET /records`:**

| Parameter | Type | Description |
|---|---|---|
| `type` | `income` \| `expense` | Filter by record type |
| `category` | string | Partial match on category name |
| `date_from` | `YYYY-MM-DD` | Start of date range |
| `date_to` | `YYYY-MM-DD` | End of date range |
| `page` | int (≥1) | Page number (default: 1) |
| `page_size` | int (1–100) | Items per page (default: 20) |

**Create record body:**
```json
{
  "amount": 3500.00,
  "type": "income",
  "category": "Salary",
  "record_date": "2024-06-01",
  "notes": "June paycheck"
}
```

---

### Dashboard

| Method | Path | Description | Required Role |
|---|---|---|---|
| `GET` | `/dashboard/summary` | Aggregated summary | Analyst, Admin |

**Optional query params:** `date_from`, `date_to` (same format as records)

**Response shape:**
```json
{
  "total_income": 7500.00,
  "total_expenses": 1900.00,
  "net_balance": 5600.00,
  "record_count": 6,
  "income_by_category": [
    { "category": "Salary", "total": 7000.00, "count": 2 }
  ],
  "expense_by_category": [
    { "category": "Rent", "total": 1700.00, "count": 2 }
  ],
  "monthly_trends": [
    { "year": 2024, "month": 1, "income": 3500.0, "expense": 1000.0, "net": 2500.0 }
  ],
  "recent_records": [ ... ]
}
```

---

## Role-Based Access Control

Access control is enforced via FastAPI dependency injection in `app/core/dependencies.py`.

```
Viewer   → read records, read own profile
Analyst  → all Viewer permissions + create/update records + dashboard summary
Admin    → all Analyst permissions + delete records + manage users
```

The `require_roles(*roles)` dependency factory is composable:

```python
# Any authenticated user
Depends(get_current_active_user)

# Analyst or Admin only
Depends(require_analyst_or_above)   # shorthand for require_roles(analyst, admin)

# Admin only
Depends(require_admin)
```

---

## Data Model

### User

| Field | Type | Notes |
|---|---|---|
| `id` | int | PK |
| `username` | string | Unique, lowercase |
| `email` | string | Unique |
| `hashed_password` | string | bcrypt |
| `role` | enum | `viewer`, `analyst`, `admin` |
| `is_active` | bool | Soft disable via admin |
| `created_at` | datetime | UTC |

### FinancialRecord

| Field | Type | Notes |
|---|---|---|
| `id` | int | PK |
| `amount` | float | Must be > 0 |
| `type` | enum | `income` or `expense` |
| `category` | string | e.g. Salary, Rent |
| `record_date` | date | Business date of transaction |
| `notes` | string? | Optional description |
| `is_deleted` | bool | Soft delete flag |
| `created_by` | int | FK → users.id |
| `created_at` | datetime | UTC |
| `updated_at` | datetime | UTC, auto-updated |

---

## Design Decisions & Assumptions

**Soft deletes** — Records are never hard-deleted. `is_deleted=True` hides them from all queries while preserving the audit trail. Users are deactivated (not deleted) for the same reason.

**Viewer access to dashboard** — The spec listed Viewer as "can only view dashboard data" but also said Analyst "can view records and access insights." I interpreted this as: Viewers see the record list, Analysts and above see the analytics summary. This stricter reading felt cleaner architecturally and matches the "access insights" phrasing.

**Amount validation** — Amounts must be positive (`> 0`). The `type` field (`income`/`expense`) carries the sign semantics, so negative amounts would be ambiguous.

**Self-registration defaults to Viewer** — Anyone can register publicly and gets `viewer` role. An admin must explicitly elevate their role. This is the safest default.

**SQLite for local dev** — No external dependencies needed to run. Switching to PostgreSQL requires only changing `DATABASE_URL` in `.env` and installing `psycopg2`.

**No refresh tokens** — Tokens expire after 8 hours. For production, a refresh token flow would be added; omitted here for simplicity.

**Dashboard computed in Python, not SQL** — The aggregation in `services/dashboard.py` loads records into memory and computes totals in Python. For large datasets, this should be replaced with `GROUP BY` SQL queries via SQLAlchemy's aggregation functions. The current design makes the logic easy to read and test.

---

## Switching to PostgreSQL

```bash
pip install psycopg2-binary
```

In `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/finance_db
```

No code changes required.
