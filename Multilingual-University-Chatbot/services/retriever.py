import os
import logging
import json
from typing import List, Dict, Optional, Tuple
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from pathlib import Path
import hashlib

from config import Config

logger = logging.getLogger(__name__)

class RetrieverService:
    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.documents_processed = set()
    
    def initialize(self):
        """Initialize the vector database and embedding model"""
        try:
            # Initialize ChromaDB
            os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=Config.VECTOR_DB_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=Config.VECTOR_DB_COLLECTION
                )
                logger.info(f"Loaded existing collection: {Config.VECTOR_DB_COLLECTION}")
            except:
                self.collection = self.client.create_collection(
                    name=Config.VECTOR_DB_COLLECTION,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {Config.VECTOR_DB_COLLECTION}")
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
            logger.info(f"Initialized embedding model: {Config.EMBEDDING_MODEL}")
            
            # Load initial documents if collection is empty
            if self.collection.count() == 0:
                self._load_initial_documents()
            
        except Exception as e:
            logger.error(f"Failed to initialize retriever service: {e}")
            raise
    
    def _load_initial_documents(self):
        """Load initial documents from FAQ and sample data"""
        try:
            # Load FAQ data as documents
            faq_path = Config.FAQ_FILE_PATH
            if os.path.exists(faq_path):
                with open(faq_path, 'r', encoding='utf-8') as f:
                    faq_data = json.load(f)
                
                documents = []
                metadatas = []
                ids = []
                
                for faq in faq_data:
                    for lang in Config.SUPPORTED_LANGUAGES:
                        if lang in faq['question'] and lang in faq['answer']:
                            # Create document from Q&A pair
                            doc_text = f"Question: {faq['question'][lang]}\nAnswer: {faq['answer'][lang]}"
                            documents.append(doc_text)
                            
                            metadatas.append({
                                'source_id': faq['id'],
                                'document_type': 'faq',
                                'language': lang,
                                'tags': ','.join(faq.get('tags', [])),
                                'last_updated': faq.get('last_updated', ''),
                                'department': faq.get('metadata', {}).get('department', '')
                            })
                            
                            ids.append(f"{faq['id']}_{lang}")
                
                if documents:
                    self.add_documents(documents, metadatas, ids)
                    logger.info(f"Added {len(documents)} FAQ documents to vector store")
            
            # Add sample university documents
            self._add_sample_documents()
            
        except Exception as e:
            logger.error(f"Error loading initial documents: {e}")
    
    def _add_sample_documents(self):
        """Add sample university documents"""
        sample_docs = [
            {
                'text': "The university offers undergraduate programs in Engineering, Science, Arts, and Commerce. The duration is typically 3-4 years depending on the program.",
                'metadata': {
                    'source_id': 'academics_001',
                    'document_type': 'academic_info',
                    'language': 'en',
                    'department': 'academics',
                    'last_updated': '2025-01-01'
                }
            },
            {
                'text': "Library facilities are available 24/7 with over 100,000 books and digital resources. Students can access online databases and study spaces.",
                'metadata': {
                    'source_id': 'facilities_001',
                    'document_type': 'facilities',
                    'language': 'en',
                    'department': 'library',
                    'last_updated': '2025-01-01'
                }
            },
            {
                'text': "The campus has modern hostels with Wi-Fi, mess facilities, recreation rooms, and 24/7 security. Both boys and girls hostels are available.",
                'metadata': {
                    'source_id': 'hostels_001',
                    'document_type': 'facilities',
                    'language': 'en',
                    'department': 'student-affairs',
                    'last_updated': '2025-01-01'
                }
            }
        ]
        
        documents = [doc['text'] for doc in sample_docs]
        metadatas = [doc['metadata'] for doc in sample_docs]
        ids = [doc['metadata']['source_id'] for doc in sample_docs]
        
        try:
            self.add_documents(documents, metadatas, ids)
            logger.info(f"Added {len(sample_docs)} sample documents")
        except Exception as e:
            logger.error(f"Error adding sample documents: {e}")
    
    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Add documents to the vector store"""
        if not self.collection or not self.embedding_model:
            raise RuntimeError("Retriever service not initialized")
        
        try:
            # Chunk documents if they're too long
            chunked_docs, chunked_metadatas, chunked_ids = self._chunk_documents(
                documents, metadatas, ids
            )
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(chunked_docs).tolist()
            
            # Add to collection
            self.collection.add(
                documents=chunked_docs,
                metadatas=chunked_metadatas,
                ids=chunked_ids,
                embeddings=embeddings
            )
            
            logger.info(f"Added {len(chunked_docs)} document chunks to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise
    
    def _chunk_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> Tuple[List[str], List[Dict], List[str]]:
        """Chunk documents into smaller pieces"""
        chunked_docs = []
        chunked_metadatas = []
        chunked_ids = []
        
        for doc, metadata, doc_id in zip(documents, metadatas, ids):
            chunks = self._split_text(doc, Config.CHUNK_SIZE, Config.CHUNK_OVERLAP)
            
            for i, chunk in enumerate(chunks):
                chunked_docs.append(chunk)
                
                # Create metadata for chunk
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'chunk_index': i,
                    'chunk_count': len(chunks),
                    'chunk_size': len(chunk)
                })
                chunked_metadatas.append(chunk_metadata)
                
                # Create unique ID for chunk
                chunk_id = f"{doc_id}_chunk_{i}"
                chunked_ids.append(chunk_id)
        
        return chunked_docs, chunked_metadatas, chunked_ids
    
    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into chunks with overlap"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to break at word boundary
            chunk = text[start:end]
            last_space = chunk.rfind(' ')
            
            if last_space > chunk_size * 0.8:  # If word boundary is reasonable
                chunk = chunk[:last_space]
                end = start + last_space
            
            chunks.append(chunk)
            start = end - overlap
        
        return chunks
    
    def retrieve(self, query: str, language: str = 'en', top_k: int = None) -> List[Dict]:
        """Retrieve similar documents for a query"""
        if not self.collection or not self.embedding_model:
            raise RuntimeError("Retriever service not initialized")
        
        if top_k is None:
            top_k = Config.TOP_K_RETRIEVAL
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Search in vector store
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Process results
            retrieved_docs = []
            
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0], 
                results['distances'][0]
            )):
                # Convert distance to similarity (assuming cosine distance)
                similarity = 1 - distance
                
                # Filter by similarity threshold
                if similarity >= Config.RETRIEVAL_THRESHOLD:
                    retrieved_docs.append({
                        'text': doc,
                        'metadata': metadata,
                        'similarity': similarity,
                        'rank': i + 1,
                        'source_id': metadata.get('source_id', 'unknown')
                    })
            
            logger.info(f"Retrieved {len(retrieved_docs)} relevant documents for query")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector collection"""
        if not self.collection:
            return {}
        
        try:
            count = self.collection.count()
            
            # Get sample of documents to analyze
            sample_results = self.collection.get(limit=100, include=['metadatas'])
            
            # Analyze document types
            doc_types = {}
            languages = {}
            departments = {}
            
            for metadata in sample_results.get('metadatas', []):
                doc_type = metadata.get('document_type', 'unknown')
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                language = metadata.get('language', 'unknown')
                languages[language] = languages.get(language, 0) + 1
                
                department = metadata.get('department', 'unknown')
                departments[department] = departments.get(department, 0) + 1
            
            return {
                'total_documents': count,
                'document_types': doc_types,
                'languages': languages,
                'departments': departments,
                'collection_name': Config.VECTOR_DB_COLLECTION
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def delete_documents(self, ids: List[str]):
        """Delete documents from vector store"""
        if not self.collection:
            raise RuntimeError("Retriever service not initialized")
        
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from vector store")
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise
    
    def clear_collection(self):
        """Clear all documents from the collection"""
        if not self.collection:
            raise RuntimeError("Retriever service not initialized")
        
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(Config.VECTOR_DB_COLLECTION)
            self.collection = self.client.create_collection(
                name=Config.VECTOR_DB_COLLECTION,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Cleared vector collection")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            raise
    
    def update_document(self, doc_id: str, document: str, metadata: Dict):
        """Update a document in the vector store"""
        if not self.collection or not self.embedding_model:
            raise RuntimeError("Retriever service not initialized")
        
        try:
            # Generate embedding
            embedding = self.embedding_model.encode([document])[0].tolist()
            
            # Update in collection
            self.collection.update(
                ids=[doc_id],
                documents=[document],
                metadatas=[metadata],
                embeddings=[embedding]
            )
            
            logger.info(f"Updated document: {doc_id}")
            
        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {e}")
            raise
