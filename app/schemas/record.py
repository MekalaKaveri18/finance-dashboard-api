from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime
from app.models.record import RecordType


class RecordCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Amount must be positive")
    type: RecordType
    category: str = Field(..., min_length=1, max_length=100)
    date: date
    notes: Optional[str] = Field(None, max_length=500)


class RecordUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    type: Optional[RecordType] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)


class RecordOut(BaseModel):
    id: int
    amount: float
    type: RecordType
    category: str
    date: date
    notes: Optional[str]
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecordFilters(BaseModel):
    type: Optional[RecordType] = None
    category: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PaginatedRecords(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[RecordOut]
