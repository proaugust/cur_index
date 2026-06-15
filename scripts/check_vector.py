from sqlalchemy import text

from app.database import engine

with engine.connect() as conn:
    ext = conn.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    ).fetchall()
    col = conn.execute(
        text(
            """
            SELECT column_name, udt_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'document_chunks' AND column_name = 'embedding'
            """
        )
    ).fetchone()
    print("pgvector extension:", ext)
    print("embedding column:", col)
