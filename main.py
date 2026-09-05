import os
from sqlmodel import create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgrespassword@localhost:5432/integration_engine"
)

# Render Postgres URLs start with "postgres://", which SQLAlchemy 2.0 / SQLModel rejects in favor of "postgresql://"
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False)
