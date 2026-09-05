import csv
import io
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends
from sqlmodel import Session, create_engine, SQLModel
from models import CleanRecord, QuarantineRecord, RawInputPayload

# --- Database Setup ---
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgrespassword@localhost:5432/integration_engine"
)

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session

# Lifespan context initializes DB tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

# --- Application Initialization ---
app = FastAPI(
    title="Universal Ingestion Engine",
    version="1.0.0",
    lifespan=lifespan
)

# --- Routes ---
@app.get("/")
def health_check():
    return {"status": "online", "service": "universal-ingestion-engine"}

@app.post("/api/v1/webhook/{source}")
def ingest_webhook(source: str, payload: dict, db: Session = Depends(get_session)):
    try:
        validated = RawInputPayload(**payload)
        record = CleanRecord(
            external_id=validated.client_ref,
            customer_name=validated.full_name.strip(),
            email=str(validated.contact_email).lower().strip(),
            phone_normalized=validated.phone_number,
            amount_cents=validated.transaction_amount,
            event_timestamp=validated.timestamp,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"status": "success", "id": record.id}
    except Exception as exc:
        quarantine = QuarantineRecord(
            raw_payload=json.dumps(payload),
            failure_reason=str(exc),
            source=source
        )
        db.add(quarantine)
        db.commit()
        return {"status": "quarantined", "error": str(exc)}

@app.post("/api/v1/batch-upload")
async def batch_upload(file: UploadFile = File(...), db: Session = Depends(get_session)):
    contents = await file.read()
    reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))
    
    success_count = 0
    quarantine_count = 0

    for row in reader:
        try:
            validated = RawInputPayload(**row)
            record = CleanRecord(
                external_id=validated.client_ref,
                customer_name=validated.full_name.strip(),
                email=str(validated.contact_email).lower().strip(),
                phone_normalized=validated.phone_number,
                amount_cents=validated.transaction_amount,
                event_timestamp=validated.timestamp,
            )
            db.add(record)
            success_count += 1
        except Exception as exc:
            quarantine = QuarantineRecord(
                raw_payload=json.dumps(row),
                failure_reason=str(exc),
                source=f"batch_{file.filename}"
            )
            db.add(quarantine)
            quarantine_count += 1

    db.commit()
    return {
        "status": "completed",
        "processed": success_count,
        "quarantined": quarantine_count
    }
