import psycopg
import json
from azure.identity import DefaultAzureCredential
from text_functions import embed_chunk
import logging
logging.basicConfig()
logger = logging.getLogger()
import os

SYSTEM_PROMPT = "You are a dog breeder who answers about the dogs using the information provided in the context. Do not pull information from outside."

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
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            cur.execute("""
                INSERT INTO document_chunks(document_id,chunk_index,content,embedding)
                VALUES(%s,%s,%s,%s::vector)
            """, (document_id, chunk_index, content, embedding_str))

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

def search_chunks(query: str, k: int = 3) -> list[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            embedded_query = embed_chunk(query);
            
            cur.execute("""
                SELECT content
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (embedded_query, k))

            return [row[0] for row in cur.fetchall()]

def create_message(
        conversation_id: int, 
        role: str,
        content: str
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO messages(
                    conversation_id, role, content
                )
                VALUES (%s, %s, %s)
                RETURNING id, content, created_at
            """,
            (conversation_id, role, content)
            )

            row = cur.fetchone()
            conn.commit()

            return {
                "conversation_id": row[0],
                "role": row[1],
                "content": row[2]
            }

def get_messages_by_conversation_id(conversation_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT m.id, m.content, m.role
                FROM messages m
                WHERE m.conversation_id = %s
                ORDER BY m.created_at
                LIMIT 10
            
            """, (conversation_id,))

            rows = cur.fetchall()

            return [
                {
                    "message_id": row[0],
                    "message_content": row[1],
                    "role": row[2]
                } for row in rows
            ]

def answer(conversation_id: int, user_text: str) -> str:
    create_message(conversation_id, "user", user_text)

    context = "\n\n".join(search_chunks(user_text))
    history = get_messages_by_conversation_id(conversation_id)

    messages = [{
        "role": "system",
        "content": f"{SYSTEM_PROMPT}. Use these dog facts in your answer: \n{context}"
    }]

    messages += [
        {"role": m["role"], "content": m["content"]}
        for m in history if m["role"] != "system"
    ]
