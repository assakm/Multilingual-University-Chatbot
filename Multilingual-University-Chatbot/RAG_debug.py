#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.rag import RAGService
from services.retriever import RetrieverService
from services.ollama_client import OllamaClient

def debug_rag_pipeline():
    print("🔍 Debugging RAG Pipeline")
    print("=" * 40)
    
    try:
        # Test Ollama connection
        print("1️⃣ Testing Ollama connection...")
        ollama_client = OllamaClient()
        connection_test = ollama_client.test_connection()
        print(f"   Ollama status: {connection_test}")
        
        if not connection_test['success']:
            print("❌ Ollama not connected. Please run: ollama serve")
            return
        
        # Test retriever
        print("\n2️⃣ Testing Retriever service...")
        retriever = RetrieverService()
        try:
            retriever.initialize()
            stats = retriever.get_collection_stats()
            print(f"   Retriever stats: {stats}")
        except Exception as e:
            print(f"   ❌ Retriever error: {e}")
            return
        
        # Test RAG service
        print("\n3️⃣ Testing RAG service...")
        rag_service = RAGService(retriever, ollama_client)
        
        # Test query that should use RAG
        test_query = "Tell me about advanced computer science topics and research opportunities"
        print(f"   Testing query: '{test_query}'")
        
        rag_result = rag_service.generate_response(
            query=test_query,
            user_lang='en',
            conversation_history=[],
            user_id='debug_user'
        )
        
        print(f"   RAG result:")
        print(f"     - Used OpenAI/Ollama: {rag_result['used_openai']}")
        print(f"     - Retrieval confidence: {rag_result['retrieval_confidence']}")
        print(f"     - Answer: {rag_result['answer'][:200]}...")
        print(f"     - Sources: {len(rag_result['sources'])}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_rag_pipeline()
