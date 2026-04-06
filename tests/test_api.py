"""
Integration tests using TestClient with an in-memory SQLite database.
Run with: pytest tests/test_api.py -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# ── Test DB setup ──────────────────────────────────────────────────────────
# StaticPool forces all sessions to share a single connection, so tables
# created by create_all() are visible to every session (critical for SQLite :memory:)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def create_tables():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────

def register(username="alice", password="secret1", role="viewer", email=None):
    email = email or f"{username}@example.com"
    return client.post("/auth/register", json={
        "username": username, "email": email,
        "password": password, "role": role,
    })


def login(username, password="secret1"):
    resp = client.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ── Auth tests ─────────────────────────────────────────────────────────────

class TestAuth:
    def setup_method(self):
        create_tables()

    def test_register_and_login(self):
        r = register("bob", role="viewer")
        assert r.status_code == 201
        assert r.json()["role"] == "viewer"

        token = login("bob")
        assert isinstance(token, str)

    def test_duplicate_username_rejected(self):
        register("charlie")
        r = register("charlie")
        assert r.status_code == 400

    def test_wrong_password_rejected(self):
        register("dave")
        r = client.post("/auth/login", data={"username": "dave", "password": "wrong"})
        assert r.status_code == 401

    def test_protected_route_requires_token(self):
        r = client.get("/users/me")
        assert r.status_code == 401


# ── RBAC tests ─────────────────────────────────────────────────────────────

class TestRBAC:
    def setup_method(self):
        create_tables()
        register("viewer_user", role="viewer")
        register("analyst_user", role="analyst")
        register("admin_user", role="admin")
        self.viewer_token = login("viewer_user")
        self.analyst_token = login("analyst_user")
        self.admin_token = login("admin_user")

    def test_viewer_cannot_create_record(self):
        r = client.post("/records", json={
            "amount": 100, "type": "income", "category": "Salary",
            "record_date": "2024-01-15",
        }, headers=auth_header(self.viewer_token))
        assert r.status_code == 403

    def test_analyst_can_create_record(self):
        r = client.post("/records", json={
            "amount": 500, "type": "income", "category": "Freelance",
            "record_date": "2024-02-01",
        }, headers=auth_header(self.analyst_token))
        assert r.status_code == 201

    def test_analyst_cannot_delete_record(self):
        # Create by analyst, try to delete as analyst
        r = client.post("/records", json={
            "amount": 200, "type": "expense", "category": "Food",
            "record_date": "2024-02-10",
        }, headers=auth_header(self.analyst_token))
        record_id = r.json()["id"]

        r2 = client.delete(f"/records/{record_id}", headers=auth_header(self.analyst_token))
        assert r2.status_code == 403

    def test_admin_can_delete_record(self):
        r = client.post("/records", json={
            "amount": 300, "type": "expense", "category": "Rent",
            "record_date": "2024-03-01",
        }, headers=auth_header(self.analyst_token))
        record_id = r.json()["id"]

        r2 = client.delete(f"/records/{record_id}", headers=auth_header(self.admin_token))
        assert r2.status_code == 204

    def test_viewer_cannot_access_user_list(self):
        r = client.get("/users", headers=auth_header(self.viewer_token))
        assert r.status_code == 403

    def test_viewer_cannot_access_dashboard(self):
        r = client.get("/dashboard/summary", headers=auth_header(self.viewer_token))
        assert r.status_code == 403

    def test_analyst_can_access_dashboard(self):
        r = client.get("/dashboard/summary", headers=auth_header(self.analyst_token))
        assert r.status_code == 200


# ── Records CRUD tests ─────────────────────────────────────────────────────

class TestRecords:
    def setup_method(self):
        create_tables()
        register("admin_r", role="admin")
        self.token = login("admin_r")
        self.headers = auth_header(self.token)

    def _create(self, amount=1000, rtype="income", category="Salary", record_date="2024-06-01"):
        return client.post("/records", json={
            "amount": amount, "type": rtype, "category": category,
            "record_date": record_date,
        }, headers=self.headers)

    def test_create_and_read(self):
        r = self._create()
        assert r.status_code == 201
        record_id = r.json()["id"]

        r2 = client.get(f"/records/{record_id}", headers=self.headers)
        assert r2.status_code == 200
        assert r2.json()["amount"] == 1000

    def test_update_record(self):
        record_id = self._create().json()["id"]
        r = client.put(f"/records/{record_id}", json={"amount": 2000, "category": "Bonus"},
                       headers=self.headers)
        assert r.status_code == 200
        assert r.json()["amount"] == 2000
        assert r.json()["category"] == "Bonus"

    def test_soft_delete_hides_record(self):
        record_id = self._create().json()["id"]
        client.delete(f"/records/{record_id}", headers=self.headers)

        r = client.get(f"/records/{record_id}", headers=self.headers)
        assert r.status_code == 404

    def test_filter_by_type(self):
        self._create(rtype="income")
        self._create(rtype="expense", category="Rent")

        r = client.get("/records?type=expense", headers=self.headers)
        items = r.json()["items"]
        assert all(i["type"] == "expense" for i in items)

    def test_filter_by_date_range(self):
        self._create(record_date="2024-01-10")
        self._create(record_date="2024-06-15")
        self._create(record_date="2024-12-20")

        r = client.get("/records?date_from=2024-06-01&date_to=2024-06-30", headers=self.headers)
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["record_date"] == "2024-06-15"

    def test_pagination(self):
        for i in range(5):
            self._create(amount=i + 1)
        r = client.get("/records?page=1&page_size=3", headers=self.headers)
        data = r.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3

    def test_invalid_amount_rejected(self):
        r = client.post("/records", json={
            "amount": -50, "type": "income", "category": "Test",
            "record_date": "2024-01-01",
        }, headers=self.headers)
        assert r.status_code == 422


# ── Dashboard tests ────────────────────────────────────────────────────────

class TestDashboard:
    def setup_method(self):
        create_tables()
        register("analyst_d", role="analyst")
        self.token = login("analyst_d")
        self.headers = auth_header(self.token)

        # Seed records via admin
        register("admin_d", role="admin")
        admin_token = login("admin_d")
        admin_headers = auth_header(admin_token)

        for item in [
            {"amount": 3000, "type": "income", "category": "Salary", "record_date": "2024-01-10"},
            {"amount": 500,  "type": "income", "category": "Freelance", "record_date": "2024-01-20"},
            {"amount": 800,  "type": "expense", "category": "Rent", "record_date": "2024-01-05"},
            {"amount": 200,  "type": "expense", "category": "Food", "record_date": "2024-01-15"},
            {"amount": 4000, "type": "income", "category": "Salary", "record_date": "2024-02-10"},
            {"amount": 900,  "type": "expense", "category": "Rent", "record_date": "2024-02-05"},
        ]:
            client.post("/records", json=item, headers=admin_headers)

    def test_summary_totals(self):
        r = client.get("/dashboard/summary", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total_income"] == 7500.0
        assert data["total_expenses"] == 1900.0
        assert data["net_balance"] == 5600.0

    def test_summary_category_breakdown(self):
        r = client.get("/dashboard/summary", headers=self.headers)
        data = r.json()
        income_cats = {c["category"]: c["total"] for c in data["income_by_category"]}
        assert income_cats["Salary"] == 7000.0
        assert income_cats["Freelance"] == 500.0

    def test_monthly_trends(self):
        r = client.get("/dashboard/summary", headers=self.headers)
        trends = r.json()["monthly_trends"]
        assert len(trends) == 2  # Jan and Feb
        jan = next(t for t in trends if t["month"] == 1)
        assert jan["income"] == 3500.0
        assert jan["expense"] == 1000.0

    def test_date_scoped_summary(self):
        r = client.get("/dashboard/summary?date_from=2024-02-01&date_to=2024-02-28",
                       headers=self.headers)
        data = r.json()
        assert data["total_income"] == 4000.0
        assert data["total_expenses"] == 900.0
