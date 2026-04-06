"""
Seed script — populates the database with demo users and financial records.
Run once after starting the app for the first time:

    python seed.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.models import FinancialRecord, RecordType, User, UserRole

Base.metadata.create_all(bind=engine)

USERS = [
    dict(username="admin",   email="admin@example.com",   password="admin123",   role=UserRole.admin),
    dict(username="analyst", email="analyst@example.com", password="analyst123", role=UserRole.analyst),
    dict(username="viewer",  email="viewer@example.com",  password="viewer123",  role=UserRole.viewer),
]

RECORDS = [
    # January
    dict(amount=5000,  type=RecordType.income,  category="Salary",     record_date=date(2024, 1, 1),  notes="Monthly salary"),
    dict(amount=800,   type=RecordType.expense, category="Rent",       record_date=date(2024, 1, 3),  notes="January rent"),
    dict(amount=150,   type=RecordType.expense, category="Groceries",  record_date=date(2024, 1, 7)),
    dict(amount=600,   type=RecordType.income,  category="Freelance",  record_date=date(2024, 1, 12), notes="Web design project"),
    dict(amount=90,    type=RecordType.expense, category="Utilities",  record_date=date(2024, 1, 15)),
    dict(amount=200,   type=RecordType.expense, category="Dining Out", record_date=date(2024, 1, 20)),
    dict(amount=50,    type=RecordType.expense, category="Transport",  record_date=date(2024, 1, 25)),
    # February
    dict(amount=5000,  type=RecordType.income,  category="Salary",     record_date=date(2024, 2, 1),  notes="Monthly salary"),
    dict(amount=800,   type=RecordType.expense, category="Rent",       record_date=date(2024, 2, 3)),
    dict(amount=120,   type=RecordType.expense, category="Groceries",  record_date=date(2024, 2, 8)),
    dict(amount=300,   type=RecordType.income,  category="Freelance",  record_date=date(2024, 2, 14)),
    dict(amount=75,    type=RecordType.expense, category="Utilities",  record_date=date(2024, 2, 16)),
    dict(amount=180,   type=RecordType.expense, category="Dining Out", record_date=date(2024, 2, 22)),
    # March
    dict(amount=5000,  type=RecordType.income,  category="Salary",     record_date=date(2024, 3, 1),  notes="Monthly salary"),
    dict(amount=1000,  type=RecordType.income,  category="Bonus",      record_date=date(2024, 3, 5),  notes="Q1 performance bonus"),
    dict(amount=800,   type=RecordType.expense, category="Rent",       record_date=date(2024, 3, 3)),
    dict(amount=200,   type=RecordType.expense, category="Groceries",  record_date=date(2024, 3, 10)),
    dict(amount=400,   type=RecordType.expense, category="Travel",     record_date=date(2024, 3, 18), notes="Weekend trip"),
    dict(amount=60,    type=RecordType.expense, category="Utilities",  record_date=date(2024, 3, 20)),
]


def seed():
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Database already seeded. Skipping.")
            return

        # Create users
        user_objs = []
        for u in USERS:
            user = User(
                username=u["username"],
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
            )
            db.add(user)
            user_objs.append(user)
        db.flush()  # assign IDs

        admin_id = user_objs[0].id

        # Create records, attributed to admin
        for r in RECORDS:
            record = FinancialRecord(**r, created_by=admin_id)
            db.add(record)

        db.commit()
        print("✅ Seed complete!")
        print("\nDemo credentials:")
        for u in USERS:
            print(f"  {u['role'].value:8s}  username={u['username']}  password={u['password']}")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
