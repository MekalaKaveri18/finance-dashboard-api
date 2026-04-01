"""
seed.py — Populates the database with demo users and financial records.
Run: python seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.record import FinancialRecord, RecordType
from datetime import date, timedelta
import random

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Clean slate
db.query(FinancialRecord).delete()
db.query(User).delete()
db.commit()

# Users
users_data = [
    {"name": "Alice Admin",   "email": "alice@demo.com",   "role": UserRole.ADMIN},
    {"name": "Bob Analyst",   "email": "bob@demo.com",     "role": UserRole.ANALYST},
    {"name": "Carol Viewer",  "email": "carol@demo.com",   "role": UserRole.VIEWER},
]
created_users = []
for u in users_data:
    user = User(**u, hashed_password=hash_password("demo1234"))
    db.add(user)
    db.flush()
    created_users.append(user)
db.commit()

# Records
categories_income  = ["Salary", "Freelance", "Investment", "Bonus", "Rental Income"]
categories_expense = ["Rent", "Utilities", "Groceries", "Transport", "Insurance", "Entertainment"]

base_date = date(2024, 1, 1)
records = []
for i in range(60):
    d = base_date + timedelta(days=i * 6)
    rec_type = RecordType.INCOME if i % 3 != 0 else RecordType.EXPENSE
    records.append(FinancialRecord(
        amount=round(random.uniform(50, 5000), 2),
        type=rec_type,
        category=random.choice(categories_income if rec_type == RecordType.INCOME else categories_expense),
        date=d,
        notes=f"Auto-seeded record #{i+1}",
        created_by=created_users[i % 2].id,  # alternate between admin and analyst
    ))

db.add_all(records)
db.commit()
db.close()

print("✅ Seed complete.")
print("  alice@demo.com  / demo1234  → ADMIN")
print("  bob@demo.com    / demo1234  → ANALYST")
print("  carol@demo.com  / demo1234  → VIEWER")
