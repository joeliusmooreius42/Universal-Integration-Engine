from datetime import datetime
from typing import Optional
import re
from pydantic import BaseModel, field_validator
from sqlmodel import SQLModel, Field

# --- Database Tables ---

class CleanRecord(SQLModel, table=True):
    __tablename__ = "clean_records"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)
    customer_name: str
    email: str = Field(index=True)
    phone_normalized: str
    amount_cents: int
    event_timestamp: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QuarantineRecord(SQLModel, table=True):
    __tablename__ = "quarantine_records"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    raw_payload: str
    failure_reason: str
    source: str
    received_at: datetime = Field(default_factory=datetime.utcnow)

# --- Pydantic Validation & Normalization ---

class RawInputPayload(BaseModel):
    client_ref: str
    full_name: str
    contact_email: str
    phone_number: str
    transaction_amount: str
    timestamp: str

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        raise ValueError(f"Invalid phone: {v}")

    @field_validator("transaction_amount")
    @classmethod
    def clean_amount(cls, v: str) -> int:
        cleaned = re.sub(r"[^\d.]", "", v)
        if not cleaned:
            raise ValueError("Missing amount")
        return int(round(float(cleaned) * 100))

    @field_validator("timestamp")
    @classmethod
    def parse_datetime(cls, v: str) -> datetime:
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            raise ValueError(f"Invalid ISO timestamp: {v}")
