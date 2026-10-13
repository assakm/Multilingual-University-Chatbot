import pytest
from unittest.mock import Mock, patch
from services.retriever import RetrieverService

@pytest.fixture
def retriever_service():
    with patch('services.retriever.SentenceTransformer'):
        with patch('services.retriever.chromadb'):
            service = RetrieverService()
            return service

def test_chunk_documents(retriever_service):
    docs = ["This is a long document that should be chunked"]
    metadata = [{"source": "test"}]
    ids = ["doc1"]
    
    chunked_docs, chunked_meta, chunked_ids = retriever_service._chunk_documents(docs, metadata, ids)
    assert len(chunked_docs) >= 1
