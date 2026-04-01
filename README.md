# Finance Dashboard API

A role-based finance data management backend built with **FastAPI**, **SQLAlchemy**, and **SQLite**. Designed to serve a frontend finance dashboard with clean data access, enforced role permissions, and summary-level analytics.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Running](#setup--running)
- [Authentication](#authentication)
- [Roles & Access Control](#roles--access-control)
- [API Reference](#api-reference)
- [Design Decisions & Assumptions](#design-decisions--assumptions)
- [Running Tests](#running-tests)

---

## Tech Stack

| Layer       | Choice                          | Reason                                          |
|-------------|----------------------------------|-------------------------------------------------|
| Framework   | FastAPI                          | Fast, typed, auto-docs via OpenAPI              |
| ORM         | SQLAlchemy 2.x                   | Clean model definitions, composable queries     |
| Database    | SQLite (default)                 | Zero-config local dev; swap via `DATABASE_URL`  |
| Auth        | JWT (python-jose) + bcrypt       | Stateless, industry standard                    |
| Validation  | Pydantic v2                      | Request/response schema enforcement             |
| Tests       | pytest + httpx TestClient        | Integration tests against real app logic        |

---

## Project Structure

```
finance-dashboard/
├── app/
│   ├── main.py               # FastAPI app, router registration, CORS
│   ├── core/
│   │   ├── database.py       # SQLAlchemy engine, session, Base
│   │   └── security.py       # JWT, password hashing, role guards
│   ├── models/
│   │   ├── user.py           # User ORM model + UserRole enum
│   │   └── record.py         # FinancialRecord ORM model + RecordType enum
│   ├── schemas/
│   │   ├── user.py           # Pydantic schemas: UserCreate, UserOut, TokenResponse
│   │   ├── record.py         # RecordCreate, RecordOut, PaginatedRecords, filters
│   │   └── dashboard.py      # DashboardSummary, CategoryTotal, MonthlyTrend
│   └── routers/
│       ├── auth.py           # POST /register, POST /login
│       ├── users.py          # User CRUD (admin-gated)
│       ├── records.py        # Financial record CRUD + filtering + pagination
│       └── dashboard.py      # GET /summary — aggregated analytics
├── tests/
│   └── test_api.py           # 22 integration tests covering all roles & flows
├── seed.py                   # Populate DB with demo users + 60 records
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup & Running

### 1. Clone and install

```bash
git clone <your-repo-url>
cd finance-dashboard

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env if needed — defaults work out of the box for local dev
```

`.env` values:
```
DATABASE_URL=sqlite:///./finance.db
SECRET_KEY=your-secret-key-change-in-production
```

To use PostgreSQL instead:
```
DATABASE_URL=postgresql://user:password@localhost:5432/finance_db
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

API is live at: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### 4. (Optional) Seed demo data

```bash
python seed.py
```

Creates 3 demo users and 60 financial records:

| Email             | Password   | Role     |
|-------------------|------------|----------|
| alice@demo.com    | demo1234   | admin    |
| bob@demo.com      | demo1234   | analyst  |
| carol@demo.com    | demo1234   | viewer   |

---

## Authentication

The API uses **JWT Bearer tokens**.

**Register:**
```http
POST /api/auth/register
Content-Type: application/json

{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "mypassword",
  "role": "analyst"
}
```
> Note: The **first registered user** is always promoted to `admin`, regardless of the role field.

**Login:**
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "jane@example.com",
  "password": "mypassword"
}
```

Returns:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": { "id": 1, "name": "Jane Doe", "role": "analyst", ... }
}
```

**Use the token:**
```http
Authorization: Bearer <access_token>
```

---

## Roles & Access Control

| Action                        | Viewer | Analyst | Admin |
|-------------------------------|--------|---------|-------|
| View financial records        | ✅     | ✅      | ✅    |
| Create financial records      | ❌     | ✅      | ✅    |
| Update own records            | ❌     | ✅      | ✅    |
| Update any record             | ❌     | ❌      | ✅    |
| Delete own records (soft)     | ❌     | ✅      | ✅    |
| Delete any record (soft)      | ❌     | ❌      | ✅    |
| View dashboard summary        | ❌     | ✅      | ✅    |
| List / manage users           | ❌     | ❌      | ✅    |

Access control is enforced via **FastAPI dependency injection** — role guards are composed from `Depends()` and applied per route. No role logic leaks into business logic or models.

---

## API Reference

### Auth

| Method | Endpoint            | Description              | Auth |
|--------|---------------------|--------------------------|------|
| POST   | /api/auth/register  | Create a new user        | No   |
| POST   | /api/auth/login     | Login, get JWT           | No   |

---

### Users

| Method | Endpoint           | Description                   | Role  |
|--------|--------------------|-------------------------------|-------|
| GET    | /api/users/me      | Get own profile               | Any   |
| GET    | /api/users/        | List all users                | Admin |
| GET    | /api/users/{id}    | Get user by ID                | Admin |
| PATCH  | /api/users/{id}    | Update role / status / name   | Admin |
| DELETE | /api/users/{id}    | Delete user                   | Admin |

---

### Financial Records

| Method | Endpoint              | Description                          | Role             |
|--------|-----------------------|--------------------------------------|------------------|
| GET    | /api/records/         | List records (filtered, paginated)   | Any              |
| GET    | /api/records/{id}     | Get single record                    | Any              |
| POST   | /api/records/         | Create record                        | Analyst, Admin   |
| PATCH  | /api/records/{id}     | Update record                        | Analyst*, Admin  |
| DELETE | /api/records/{id}     | Soft delete record                   | Analyst*, Admin  |

*Analysts can only modify/delete records they created.

**Filtering (query params on GET /api/records/):**

| Param      | Type   | Example                 |
|------------|--------|-------------------------|
| type       | string | `?type=income`          |
| category   | string | `?category=Rent`        |
| date_from  | date   | `?date_from=2024-01-01` |
| date_to    | date   | `?date_to=2024-03-31`   |
| page       | int    | `?page=2`               |
| page_size  | int    | `?page_size=10`         |

**Record fields:**

```json
{
  "amount": 1500.00,
  "type": "income",
  "category": "Salary",
  "date": "2024-03-15",
  "notes": "March salary"
}
```

---

### Dashboard

| Method | Endpoint                | Description                          | Role             |
|--------|-------------------------|--------------------------------------|------------------|
| GET    | /api/dashboard/summary  | Aggregated analytics                 | Analyst, Admin   |

**Optional query params:** `date_from`, `date_to` to scope the summary.

**Response shape:**
```json
{
  "total_income": 15000.00,
  "total_expenses": 8200.00,
  "net_balance": 6800.00,
  "total_records": 42,
  "income_by_category": [
    { "category": "Salary", "total": 12000.00, "count": 3 }
  ],
  "expense_by_category": [
    { "category": "Rent", "total": 4500.00, "count": 3 }
  ],
  "monthly_trends": [
    { "month": "2024-01", "income": 5000.00, "expense": 2700.00, "net": 2300.00 }
  ],
  "recent_activity": [
    { "id": 42, "amount": 500.00, "type": "expense", "category": "Utilities", "date": "2024-03-20", "notes": null }
  ]
}
```

---

## Running Tests

```bash
pytest tests/ -v
```

22 integration tests covering:
- Registration, login, bad credentials
- Role enforcement (viewer blocked from write/dashboard, analyst blocked from others' records)
- Record CRUD, filtering, pagination
- Input validation (negative amounts, missing fields)
- Soft delete (deleted records return 404)
- Dashboard math correctness (`net = income - expenses`)
- Admin-only user management

---

## Design Decisions & Assumptions

**SQLite as default database**  
Zero setup cost for evaluation. The `DATABASE_URL` environment variable accepts any SQLAlchemy-compatible URL — switching to PostgreSQL requires no code changes.

**Soft delete on records**  
Records are never hard-deleted. `is_deleted = True` hides them from all queries. This preserves audit history and is standard practice in financial systems.

**First user becomes admin**  
When the database is empty, the first registration is automatically elevated to admin. This avoids the chicken-and-egg problem of needing an admin to create an admin.

**Analyst ownership rule**  
Analysts can create, update, and delete their own records. Admins have unrestricted write access across all records. This models a realistic multi-user finance team.

**Viewer excluded from dashboard**  
Dashboard analytics (category breakdowns, trends) are treated as insights — a step above raw data access. Viewers can see individual records but not aggregated analysis. This is a deliberate design choice, not a technical constraint.

**JWT expiry set to 24 hours**  
Reasonable for a dashboard tool used in a workday context. Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` in `security.py`.

**No refresh tokens**  
Out of scope for this assignment. In production, a refresh token flow would be added.

**Pydantic validates all inputs**  
Amount must be positive (`gt=0`), dates must be valid ISO format, strings have length limits. Invalid requests return `422 Unprocessable Entity` with field-level error detail.

---

## Example: Quick API Walkthrough

```bash
# Register (first user = admin)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@co.com","password":"pass1234","role":"viewer"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@co.com","password":"pass1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create a record (admin can do this)
curl -X POST http://localhost:8000/api/records/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount":2500,"type":"income","category":"Salary","date":"2024-03-01"}'

# Get dashboard summary
curl http://localhost:8000/api/dashboard/summary \
  -H "Authorization: Bearer $TOKEN"
```
