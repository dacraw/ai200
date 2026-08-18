"""
Vector search functions for storing and retrieving documents with embeddings from Cosmos DB.
These functions serve as the interface between the Flask app and Cosmos DB vector search.
"""
import os
import logging
import json
from datetime import datetime, timezone
from azure.cosmos import CosmosClient, exceptions
from azure.identity import DefaultAzureCredential

logging.basicConfig(
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def get_container():
    """Get a reference to the Cosmos DB container using Entra ID authentication."""
    endpoint = os.environ.get("COSMOS_ENDPOINT")
    database_name = os.environ.get("COSMOS_DATABASE")
    container_name = os.environ.get("COSMOS_CONTAINER")

    if not endpoint or not database_name or not container_name:
        raise ValueError(
            "COSMOS_ENDPOINT, COSMOS_DATABASE, and COSMOS_CONTAINER "
            "environment variables must be set"
        )

    credential = DefaultAzureCredential()
    client = CosmosClient(endpoint, credential=credential)
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)

    return container


# BEGIN STORE VECTOR DOCUMENT FUNCTION
# def store_vector_document(
#         chunk_id: str,
#         document_id: str,
#         content: str,
#         embedding: list = None,
#         metadata: dict = None
# ):
#     container = get_container()
#     chunk = {
#         "id": chunk_id,
#         "documentId": document_id,
#         "content": content,
#         "chunkIndex": metadata.get("chunkIndex", 0) if metadata else 0,
#         "createdAt": datetime.now(timezone.utc).isoformat(),
#         "embedding": embedding,
#         "metadata": metadata or {}
#     }

#     logging.info(f"Chunk to upload: {json.dumps(chunk)}")

#     result = container.upsert_item(body=chunk)

#     logging.info(f"Completed upserting, result: {json.dumps(result)}")
#     ru_charge = result.get_response_headers()["x-ms-request-charge"]
#     return {
#         "chunkId": result["chunkId"],
#         "documentId": result["documentId"],
#         "ruCharge": float(ru_charge)
#     }
def store_vector_document(
    document_id: str,
    chunk_id: str,
    content: str,
    embedding: list,
    metadata: dict = None
) -> dict:
    """Store a document with its vector embedding for similarity search."""
    container = get_container()

    # Build the document structure with embedding for vector search
    # The 'id' field is required by Cosmos DB and must be unique within the partition
    # The 'documentId' field is our partition key - chunks from the same source document
    # are stored together for efficient retrieval
    # The 'embedding' field contains the vector that will be used for similarity search
    document = {
        "id": chunk_id,
        "documentId": document_id,
        "content": content,
        "embedding": embedding,  # 256-dimensional vector for similarity search
        "metadata": metadata or {},
        "createdAt": datetime.utcnow().isoformat(),
        "chunkIndex": metadata.get("chunkIndex", 0) if metadata else 0
    }

    # upsert_item inserts if new, updates if exists (based on id + partition key)
    # This is idempotent - safe to call multiple times with the same data
    response = container.upsert_item(body=document)

    # Request Units (RUs) measure the cost of database operations in Cosmos DB
    # Tracking RU consumption helps optimize queries and estimate costs
    ru_charge = response.get_response_headers()['x-ms-request-charge']

    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "ru_charge": float(ru_charge)
    }

# END STORE VECTOR DOCUMENT FUNCTION


# BEGIN VECTOR SIMILARITY SEARCH FUNCTION
# def vector_similarity_search(
#         query_embedding: list, top_n: int = 5
# ):
#     container = get_container()
#     query = """
#     SELECT TOP @topN 
#         c.id, c.documentId, c.content, c.metadata, VectorDistance(c.embedding, @queryEmbedding) as similiarityScore
#     FROM c
#     ORDER BY VectorDistance(c.embedding, @queryEmbedding)
#     """


#     items = container.query_items(
#         query=query,
#         parameters=[
#             {"name": "@topN", "value": top_n},
#             {"name": "@queryEmbedding", "value": query_embedding}
#         ],
#         enable_cross_partition_query = True
#     )

#     return [
#         {
#             "chunk_id": item["id"],
#             "document_id": item["documentId"],
#             "content": item["content"],
#             "metadata": item["metadata"],
#             "similiarity_score": item["similiarityScore"]
#         } for item in items
#     ]
def vector_similarity_search(
    query_embedding: list,
    top_n: int = 5
) -> list:
    """
    Find documents most similar to the query using vector distance.

    Uses the VectorDistance function to calculate cosine similarity between
    the query embedding and document embeddings stored in Cosmos DB.
    Results are ordered by similarity (lowest distance = most similar).
    """
    container = get_container()

    # The VectorDistance function calculates the distance between two vectors
    # Using cosine distance: 0 = identical, 2 = opposite
    # We order by distance ascending so most similar results come first
    # The @queryVector parameter contains our 256-dimensional query embedding
    query = """
        SELECT TOP @topN
            c.id,
            c.documentId,
            c.content,
            c.metadata,
            VectorDistance(c.embedding, @queryVector) AS similarityScore
        FROM c
        ORDER BY VectorDistance(c.embedding, @queryVector)
    """

    items = container.query_items(
        query=query,
        parameters=[
            {"name": "@topN", "value": top_n},
            {"name": "@queryVector", "value": query_embedding}
        ],
        enable_cross_partition_query=True
    )

    return [
        {
            "chunk_id": item["id"],
            "document_id": item["documentId"],
            "content": item["content"],
            "metadata": item["metadata"],
            "similarity_score": item["similarityScore"]
        }
        for item in items
    ]


# END VECTOR SIMILARITY SEARCH FUNCTION


# BEGIN FILTERED VECTOR SEARCH FUNCTION
def filtered_vector_search(query_embedding: list, category: str = None, top_n: int = 5):
    container = get_container()

    where_clause = ""
    parameters = []

    if category:
        where_clause = "WHERE c.metadata.category = @category"
        parameters.append({"name": "@category", "value": category})

    query = f"""
        SELECT TOP @topN
            c.id, c.documentId, c.content, c.metadata, VectorDistance(c.embedding, @queryEmbedding) as similarityScore
        FROM c
        {where_clause}
        ORDER BY VectorDistance(c.embedding, @queryEmbedding)
    """

    parameters.append({"name":"@queryEmbedding", "value": query_embedding})
    parameters.append({"name":"@topN", "value": top_n})

    items = container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    )

    return [
        {
            "chunk_id": item["id"],
            "document_id": item["documentId"],
            "content": item["content"],
            "metadata": item["metadata"],
            "similarity_score": item["similarityScore"]
        } for item in items
    ]

# END FILTERED VECTOR SEARCH FUNCTION


def get_all_categories() -> list:
    """Get a list of unique categories from the container."""
    try:
        container = get_container()
        query = "SELECT DISTINCT c.metadata.category FROM c WHERE IS_DEFINED(c.metadata.category)"
        items = container.query_items(
            query=query,
            enable_cross_partition_query=True
        )
        return sorted([item["category"] for item in items if item.get("category")])
    except Exception:
        return []


def get_all_document_ids() -> list:
    """Get a list of unique document IDs from the container."""
    try:
        container = get_container()
        query = "SELECT DISTINCT c.documentId FROM c"
        items = container.query_items(
            query=query,
            enable_cross_partition_query=True
        )
        return sorted([item["documentId"] for item in items])
    except Exception:
        return []
