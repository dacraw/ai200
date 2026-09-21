from flask import Flask, json
import uuid
import psycopg
from psycopg import sql
from azure.identity import DefaultAzureCredential
import logging
import os

app = Flask(__name__)
logging.basicConfig()
logger = logging.getLogger()

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
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    metadata JSONB DEFAULT '{}'::jsonb
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
        create_vector_extension()

        create_conversations_table()
        create_messages_table()
        create_indexes()

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


