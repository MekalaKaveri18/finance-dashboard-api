from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import date
from app.core.database import get_db
from app.core.security import get_current_user, require_analyst_or_above, require_admin
from app.models.user import User, UserRole
from app.models.record import FinancialRecord, RecordType
from app.schemas.record import RecordCreate, RecordUpdate, RecordOut, PaginatedRecords

router = APIRouter()


def _get_active_record(record_id: int, db: Session) -> FinancialRecord:
    record = db.query(FinancialRecord).filter(
        FinancialRecord.id == record_id,
        FinancialRecord.is_deleted == False,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.get("/", response_model=PaginatedRecords)
def list_records(
    type: Optional[RecordType] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # all roles can view
):
    """List financial records with optional filters and pagination. All roles allowed."""
    filters = [FinancialRecord.is_deleted == False]

    if type:
        filters.append(FinancialRecord.type == type)
    if category:
        filters.append(FinancialRecord.category.ilike(f"%{category}%"))
    if date_from:
        filters.append(FinancialRecord.date >= date_from)
    if date_to:
        filters.append(FinancialRecord.date <= date_to)

    query = db.query(FinancialRecord).filter(and_(*filters))
    total = query.count()
    results = query.order_by(FinancialRecord.date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {"total": total, "page": page, "page_size": page_size, "results": results}


@router.get("/{record_id}", response_model=RecordOut)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single record by ID. All roles allowed."""
    return _get_active_record(record_id, db)


@router.post("/", response_model=RecordOut, status_code=201)
def create_record(
    payload: RecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst_or_above),  # analyst + admin
):
    """Create a new financial record. Analyst and Admin only."""
    record = FinancialRecord(**payload.model_dump(), created_by=current_user.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{record_id}", response_model=RecordOut)
def update_record(
    record_id: int,
    payload: RecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst_or_above),
):
    """Update a record. Analyst can only update their own; Admin can update any."""
    record = _get_active_record(record_id, db)

    if current_user.role == UserRole.ANALYST and record.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Analysts can only update their own records")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=204)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst_or_above),
):
    """Soft delete a record. Analyst can only delete their own; Admin can delete any."""
    record = _get_active_record(record_id, db)

    if current_user.role == UserRole.ANALYST and record.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Analysts can only delete their own records")

    record.is_deleted = True
    db.commit()
