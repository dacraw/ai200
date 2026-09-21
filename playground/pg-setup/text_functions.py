from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from dataclasses import dataclass

DOCUMENTS_DIR = Path(__file__).parent / "documents"

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
