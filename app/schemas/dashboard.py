from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class CategoryTotal(BaseModel):
    category: str
    total: float
    count: int


class MonthlyTrend(BaseModel):
    month: str  # e.g. "2024-01"
    income: float
    expense: float
    net: float


class RecentActivity(BaseModel):
    id: int
    amount: float
    type: str
    category: str
    date: date
    notes: Optional[str]


class DashboardSummary(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    total_records: int
    income_by_category: List[CategoryTotal]
    expense_by_category: List[CategoryTotal]
    monthly_trends: List[MonthlyTrend]
    recent_activity: List[RecentActivity]
