from flask import Flask, json
import uuid
import psycopg
from psycopg import sql

import logging
import os
from text_functions import chunk_document
from db_functions import create_document, get_all_documents, get_connection

app = Flask(__name__)
logging.basicConfig()
logger = logging.getLogger()



def create_conversations_table():
    schema = """
        CREATE TABLE conversations(
            id BIGSERIAL PRIMARY KEY,
            session_id UUID NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP WITH TIME ZONE,
            metadata JSONB DEFAULT '{}'::jsonb
        )
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema)

def create_conversation(user_id: str, metadata: dict = None):
    session_id = uuid.uuid4()
    query = """
        INSERT INTO conversations(
            session_id,
            user_id,
            metadata
        )
        VALUES (%s, %s, %s)
        RETURNING id, session_id, started_at
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (str(session_id), user_id, psycopg.types.json.Json(metadata or {})))

            row = cur.fetchone()
            conn.commit()

            return {
                "conversation_id": row[0],
                "session_id": str(row[1]),
                "started_at": row[2].isoformat()
            }

def create_messages_table():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE messages(
                    id BIGSERIAL PRIMARY KEY,
                    conversation_id BIGINT NOT NULL REFERENCES conversations(id),
                    role VARCHAR(50) NOT NULL CHECK (role IN ('user','system','assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)

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


def create_indexes():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
                CREATE INDEX idx_messages_create_at ON messages(created_at);
                CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at)
            """)

def drop_index(index_name: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP INDEX IF EXISTS {}").format(sql.Identifier(index_name))
            )


def drop_table(table_name: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table_name))
            )

def drop_all_tables():
    drop_table("conversations")
    drop_table("messages")
    drop_table("documents")

def create_vector_extension():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

def create_documents_table():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE documents(
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'::jsonb
                )
            """)

def create_document_chunks_table():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE document_chunks(
                    id BIGSERIAL PRIMARY KEY,
                    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(384),
                    UNIQUE (document_id, chunk_index)
                )
            """)

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


if __name__ == "__main__":
    try:
        # Config DB
        create_vector_extension()

        # DB Schema
        create_conversations_table()
        create_messages_table()
        create_documents_table()
        create_indexes()

        # Upload embedding document chunks
        chunked = chunk_document("chihuahua.txt")

        uploaded_document = create_document(chunked.title, chunked.source)

        document_list = get_all_documents()

        for doc in document_list:
            print(f"doc info: {doc["document_id"]}")    

        # for chunk in chunked.chunks:
        #     print(f"chunk: {chunk}")

        conversation = create_conversation("dougie")
        print(f"Conversation details: {json.dumps(conversation, indent=2, default=str)}")

        conversation_id = conversation.get("conversation_id")

        message = create_message(conversation_id,"system","You are a helpful assistant who brings up dogs as much as possible.")

        messages = get_messages_by_conversation_id(conversation_id)

        for msg in messages:
            print(f"Message id #{msg["message_id"]}:[{msg["role"]}] {msg["message_content"]}")

    except Exception as e:
        print(f"Exception: {e}")
    finally:

        input("Press enter to drop all tables....")

        drop_all_tables()


