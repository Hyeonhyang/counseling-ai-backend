"""Add new columns to sessions table"""
from app.database import engine
from sqlalchemy import text

columns = [
    "ALTER TABLE sessions ADD COLUMN risk_level VARCHAR DEFAULT 'none'",
    "ALTER TABLE sessions ADD COLUMN risk_keywords TEXT DEFAULT '[]'",
    "ALTER TABLE sessions ADD COLUMN soap_subjective TEXT DEFAULT ''",
    "ALTER TABLE sessions ADD COLUMN soap_objective TEXT DEFAULT ''",
    "ALTER TABLE sessions ADD COLUMN soap_assessment TEXT DEFAULT ''",
    "ALTER TABLE sessions ADD COLUMN soap_plan TEXT DEFAULT ''",
]

with engine.connect() as conn:
    for sql in columns:
        try:
            conn.execute(text(sql))
            print(f"OK: {sql[:50]}...")
        except Exception as e:
            print(f"SKIP (already exists): {sql[:50]}... ({e})")
    conn.commit()

print("Migration complete!")
