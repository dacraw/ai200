import psycopg
import json
from azure.identity import DefaultAzureCredential
import logging
logging.basicConfig()
logger = logging.getLogger()
import os

def get_connection():
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")

        return psycopg.connect(
            host=os.getenv('DB_HOST'),
            port=5432,
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=token.token,
            sslmode="require",
            connect_timeout=10
        )
    except Exception as e:
        logger.exception(f"exception :{e}")
        raise

def create_document(
    title: str,
    source: str,
    metadata: dict = None
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents(title,source,metadata)
                VALUES(%s,%s,%s)
                RETURNING id,title
            """,
                (title, source, psycopg.types.json.Json(metadata or {}))
            )

            row = cur.fetchone()
            conn.commit()

            return {
                "document_id": row[0],
                "document_title": row[1]
            }
        
def get_all_documents() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.id, d.title, d.source
                FROM documents d
            """)
            rows = cur.fetchall()

            return [
                {
                    "document_id": row[0],
                    "document_title": row[1],
                    "document_source": row[2]
                } for row in rows
            ]

def create_document_chunk(
    document_id: int,
    chunk_index: int,
    content: str,
    embedding: list[str]
) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO document_chunks(document_id,chunk_index,content,embedding)
                VALUES(%s,%s,%s,%s)
            """, (document_id, chunk_index, content, embedding))

def get_document_chunks(document_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.content, c.document_id, c.chunk_index
                FROM document_chunks c
                WHERE c.document_id = %s
            """, (
                document_id,
            ))
            rows = cur.fetchall()

            return [{
                "chunk_id": row[0],
                "content": row[1],
                "document_id": row[2],
                "chunk_index": row[3]
            } for row in rows]
