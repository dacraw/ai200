from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from dataclasses import dataclass
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import os

DOCUMENTS_DIR = Path(__file__).parent / "documents"

_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_ad_token_provider=get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    ),
    api_version="2024-10-21"
)

EMBEDDING_DEPLOYMENT=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
EMBEDDING_DIMENSIONS=384

@dataclass
class ChunkedDocument:
    title: str
    source: str
    chunks: list[str]

def chunk_document(document_name: str) -> ChunkedDocument:
    text = (DOCUMENTS_DIR / document_name).read_text(encoding="utf-8")

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=300,
        chunk_overlap=50
    )

    title,body = text.split("\n", 1)
    chunks = splitter.split_text(body)

    return ChunkedDocument(
        title = title.strip(), 
        source=document_name,
        chunks=chunks
        )


def embed_chunk(chunk: str) -> list[float]:
    response = _client.embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=chunk,
        dimensions=EMBEDDING_DIMENSIONS
    )

    return response.data[0].embedding