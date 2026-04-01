from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, Text, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime, date, timezone
import enum
from app.core.database import Base


class RecordType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    type = Column(Enum(RecordType), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)  # soft delete

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    created_by_user = relationship("User", back_populates="records", foreign_keys=[created_by])
