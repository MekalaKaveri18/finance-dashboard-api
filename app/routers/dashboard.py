from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import require_analyst_or_above
from app.models.user import User
from app.models.record import FinancialRecord, RecordType
from app.schemas.dashboard import DashboardSummary, CategoryTotal, MonthlyTrend, RecentActivity

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    date_from: Optional[date] = Query(None, description="Filter from this date"),
    date_to: Optional[date] = Query(None, description="Filter to this date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst_or_above),  # viewer excluded from insights
):
    """
    Full dashboard summary: totals, category breakdowns, monthly trends, recent activity.
    Analyst and Admin only.
    """
    base_query = db.query(FinancialRecord).filter(FinancialRecord.is_deleted == False)

    if date_from:
        base_query = base_query.filter(FinancialRecord.date >= date_from)
    if date_to:
        base_query = base_query.filter(FinancialRecord.date <= date_to)

    # --- Totals ---
    income_result = (
        base_query.filter(FinancialRecord.type == RecordType.INCOME)
        .with_entities(func.coalesce(func.sum(FinancialRecord.amount), 0))
        .scalar()
    )
    expense_result = (
        base_query.filter(FinancialRecord.type == RecordType.EXPENSE)
        .with_entities(func.coalesce(func.sum(FinancialRecord.amount), 0))
        .scalar()
    )
    total_income = float(income_result)
    total_expenses = float(expense_result)
    total_records = base_query.count()

    # --- Category breakdowns ---
    def get_category_totals(record_type: RecordType):
        rows = (
            base_query.filter(FinancialRecord.type == record_type)
            .with_entities(
                FinancialRecord.category,
                func.sum(FinancialRecord.amount).label("total"),
                func.count(FinancialRecord.id).label("count"),
            )
            .group_by(FinancialRecord.category)
            .order_by(func.sum(FinancialRecord.amount).desc())
            .all()
        )
        return [CategoryTotal(category=r.category, total=float(r.total), count=r.count) for r in rows]

    income_by_category = get_category_totals(RecordType.INCOME)
    expense_by_category = get_category_totals(RecordType.EXPENSE)

    # --- Monthly trends (last 12 months) ---
    monthly_rows = (
        base_query
        .with_entities(
            func.strftime("%Y-%m", FinancialRecord.date).label("month"),
            FinancialRecord.type,
            func.sum(FinancialRecord.amount).label("total"),
        )
        .group_by("month", FinancialRecord.type)
        .order_by("month")
        .all()
    )

    monthly_map: dict = {}
    for row in monthly_rows:
        m = row.month
        if m not in monthly_map:
            monthly_map[m] = {"income": 0.0, "expense": 0.0}
        if row.type == RecordType.INCOME:
            monthly_map[m]["income"] += float(row.total)
        else:
            monthly_map[m]["expense"] += float(row.total)

    monthly_trends = [
        MonthlyTrend(
            month=m,
            income=v["income"],
            expense=v["expense"],
            net=round(v["income"] - v["expense"], 2),
        )
        for m, v in sorted(monthly_map.items())
    ]

    # --- Recent activity (last 10 records) ---
    recent_records = (
        base_query
        .order_by(FinancialRecord.date.desc(), FinancialRecord.created_at.desc())
        .limit(10)
        .all()
    )
    recent_activity = [
        RecentActivity(
            id=r.id,
            amount=r.amount,
            type=r.type,
            category=r.category,
            date=r.date,
            notes=r.notes,
        )
        for r in recent_records
    ]

    return DashboardSummary(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        net_balance=round(total_income - total_expenses, 2),
        total_records=total_records,
        income_by_category=income_by_category,
        expense_by_category=expense_by_category,
        monthly_trends=monthly_trends,
        recent_activity=recent_activity,
    )
