"""将 document_chunks.embedding 迁移为 vector(embedding_dim)。"""
from sqlalchemy import inspect, text

from app.core.config import settings
from app.database import engine

EMBEDDING_DIM = settings.embedding_dim


def main() -> None:
    cols = inspect(engine).get_columns("document_chunks")
    emb = next(column for column in cols if column["name"] == "embedding")
    type_name = str(emb["type"]).upper()
    target = f"vector({EMBEDDING_DIM})"

    with engine.begin() as conn:
        if target.upper() not in type_name:
            conn.execute(text("UPDATE document_chunks SET embedding = NULL"))
            conn.execute(
                text(
                    f"""
                    ALTER TABLE document_chunks
                    ALTER COLUMN embedding TYPE {target}
                    USING embedding::{target}
                    """
                )
            )
            print(f"migrated embedding column to {target}")
        else:
            print(f"embedding column already {target}")

        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
                ON document_chunks
                USING hnsw (embedding vector_cosine_ops)
                """
            )
        )
        print("hnsw index ensured")


if __name__ == "__main__":
    main()
