"""
Integration tests for the Finance Dashboard API.
Uses an in-memory SQLite database — no setup required.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db

TEST_DB_URL = "sqlite:///./test_finance.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)
client = TestClient(app)


# ─── Helpers ───────────────────────────────────────────────────────────────

def register_and_login(email, password, name="Test User", role="viewer"):
    client.post("/api/auth/register", json={"name": name, "email": email, "password": password, "role": role})
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ─── Auth Tests ────────────────────────────────────────────────────────────

def test_register_first_user_becomes_admin():
    resp = client.post("/api/auth/register", json={
        "name": "Admin User", "email": "admin@test.com", "password": "secret123", "role": "viewer"
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"  # first user overridden to admin


def test_register_duplicate_email():
    resp = client.post("/api/auth/register", json={
        "name": "Dup", "email": "admin@test.com", "password": "secret123"
    })
    assert resp.status_code == 400


def test_login_success():
    resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "secret123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password():
    resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user():
    resp = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "x"})
    assert resp.status_code == 401


# ─── Role Access Tests ─────────────────────────────────────────────────────

def test_viewer_cannot_create_record():
    token = register_and_login("viewer@test.com", "pass123", "Viewer", "viewer")
    resp = client.post("/api/records/", json={
        "amount": 100, "type": "income", "category": "Salary", "date": "2024-01-15"
    }, headers=auth(token))
    assert resp.status_code == 403


def test_analyst_can_create_record():
    token = register_and_login("analyst@test.com", "pass123", "Analyst", "analyst")
    resp = client.post("/api/records/", json={
        "amount": 500, "type": "income", "category": "Freelance", "date": "2024-02-10"
    }, headers=auth(token))
    assert resp.status_code == 201
    assert resp.json()["category"] == "Freelance"


def test_admin_can_create_record():
    token = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "secret123"}).json()["access_token"]
    resp = client.post("/api/records/", json={
        "amount": 2000, "type": "expense", "category": "Rent", "date": "2024-03-01"
    }, headers=auth(token))
    assert resp.status_code == 201


def test_viewer_can_list_records():
    token = client.post("/api/auth/login", json={"email": "viewer@test.com", "password": "pass123"}).json()["access_token"]
    resp = client.get("/api/records/", headers=auth(token))
    assert resp.status_code == 200


def test_viewer_cannot_access_dashboard():
    token = client.post("/api/auth/login", json={"email": "viewer@test.com", "password": "pass123"}).json()["access_token"]
    resp = client.get("/api/dashboard/summary", headers=auth(token))
    assert resp.status_code == 403


def test_analyst_can_access_dashboard():
    token = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "pass123"}).json()["access_token"]
    resp = client.get("/api/dashboard/summary", headers=auth(token))
    assert resp.status_code == 200


# ─── Record CRUD Tests ─────────────────────────────────────────────────────

def test_record_filtering_by_type():
    token = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "pass123"}).json()["access_token"]
    resp = client.get("/api/records/?type=income", headers=auth(token))
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        assert r["type"] == "income"


def test_record_filtering_by_category():
    token = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "pass123"}).json()["access_token"]
    resp = client.get("/api/records/?category=Rent", headers=auth(token))
    assert resp.status_code == 200


def test_record_pagination():
    token = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "pass123"}).json()["access_token"]
    resp = client.get("/api/records/?page=1&page_size=2", headers=auth(token))
    data = resp.json()
    assert "total" in data
    assert len(data["results"]) <= 2


def test_invalid_amount_rejected():
    token = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "pass123"}).json()["access_token"]
    resp = client.post("/api/records/", json={
        "amount": -50, "type": "income", "category": "X", "date": "2024-01-01"
    }, headers=auth(token))
    assert resp.status_code == 422


def test_analyst_cannot_update_others_record():
    # Admin creates a record
    admin_token = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "secret123"}).json()["access_token"]
    rec = client.post("/api/records/", json={
        "amount": 999, "type": "expense", "category": "Admin Expense", "date": "2024-04-01"
    }, headers=auth(admin_token)).json()

    # Analyst tries to update it
    analyst_token = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "pass123"}).json()["access_token"]
    resp = client.patch(f"/api/records/{rec['id']}", json={"amount": 1}, headers=auth(analyst_token))
    assert resp.status_code == 403


def test_soft_delete():
    token = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "pass123"}).json()["access_token"]
    # Create then delete
    rec = client.post("/api/records/", json={
        "amount": 100, "type": "income", "category": "Bonus", "date": "2024-05-01"
    }, headers=auth(token)).json()
    del_resp = client.delete(f"/api/records/{rec['id']}", headers=auth(token))
    assert del_resp.status_code == 204
    # Should 404 now
    get_resp = client.get(f"/api/records/{rec['id']}", headers=auth(token))
    assert get_resp.status_code == 404


# ─── Dashboard Tests ───────────────────────────────────────────────────────

def test_dashboard_summary_fields():
    token = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "secret123"}).json()["access_token"]
    resp = client.get("/api/dashboard/summary", headers=auth(token))
    assert resp.status_code == 200
    data = resp.json()
    for key in ["total_income", "total_expenses", "net_balance", "income_by_category",
                "expense_by_category", "monthly_trends", "recent_activity"]:
        assert key in data


def test_dashboard_net_balance_is_correct():
    token = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "secret123"}).json()["access_token"]
    data = client.get("/api/dashboard/summary", headers=auth(token)).json()
    assert round(data["net_balance"], 2) == round(data["total_income"] - data["total_expenses"], 2)


# ─── User Management Tests ─────────────────────────────────────────────────

def test_non_admin_cannot_list_users():
    token = client.post("/api/auth/login", json={"email": "analyst@test.com", "password": "pass123"}).json()["access_token"]
    resp = client.get("/api/users/", headers=auth(token))
    assert resp.status_code == 403


def test_admin_can_list_users():
    token = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "secret123"}).json()["access_token"]
    resp = client.get("/api/users/", headers=auth(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_unauthenticated_request_rejected():
    resp = client.get("/api/records/")
    assert resp.status_code == 403
