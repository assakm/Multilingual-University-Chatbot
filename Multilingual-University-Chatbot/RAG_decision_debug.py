#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.rag import RAGService
from services.retriever import RetrieverService
from services.ollama_client import OllamaClient
from config import Config

def debug_rag_decision():
    print("🔍 Debugging RAG Decision Logic")
    print("=" * 50)
    
    try:
        # Initialize services
        retriever = RetrieverService()
        retriever.initialize()
        
        ollama_client = OllamaClient()
        rag_service = RAGService(retriever, ollama_client)
        
        # Test query
        test_query = "Tell me about advanced computer science topics and research opportunities"
        print(f"🔍 Testing query: '{test_query}'")
        print(f"📊 Config RETRIEVAL_THRESHOLD: {Config.RETRIEVAL_THRESHOLD}")
        print()
        
        # Step 1: Direct retrieval test
        print("1️⃣ Direct Retrieval Test:")
        retrieved_docs = retriever.retrieve(query=test_query, language='en', top_k=5)
        
        if retrieved_docs:
            max_similarity = max(doc['similarity'] for doc in retrieved_docs)
            print(f"   Max similarity: {max_similarity:.4f}")
            print(f"   Above threshold? {max_similarity >= Config.RETRIEVAL_THRESHOLD}")
            print(f"   Number of docs: {len(retrieved_docs)}")
        
        # Step 2: RAG service assessment
        print("\n2️⃣ RAG Service Assessment:")
        retrieval_confidence = rag_service._assess_retrieval_quality(retrieved_docs)
        print(f"   RAG confidence: {retrieval_confidence:.4f}")
        print(f"   Above threshold? {retrieval_confidence >= Config.RETRIEVAL_THRESHOLD}")
        
        # Step 3: Context building
        print("\n3️⃣ Context Building:")
        context, sources = rag_service._build_context(retrieved_docs)
        print(f"   Context length: {len(context)} characters")
        print(f"   Number of sources: {len(sources)}")
        print(f"   Context preview: {context[:200]}...")
        
        # Step 4: Test Ollama call directly
        print("\n4️⃣ Direct Ollama Test:")
        
        messages = [
            {
                "role": "system",
                "content": f"You are a helpful, concise university assistant. Use only the facts provided in the CONTEXT sections below. If the answer cannot be drawn from that context, say you do not know and propose safe next steps. Do not hallucinate. Answer in English. Keep answers ≤ 300 words unless asked otherwise.\n\nCONTEXT:\n{context[:500]}..."
            },
            {
                "role": "user", 
                "content": f"Current question: {test_query}"
            }
        ]
        
        ollama_response = rag_service._call_openai(
            query=test_query,
            context=context,
            user_lang='en',
            conversation_history=[]
        )
        
        print(f"   Ollama call success: {ollama_response['success']}")
        if ollama_response['success']:
            print(f"   Response: {ollama_response['answer'][:200]}...")
        else:
            print(f"   Error: {ollama_response['error']}")
        
        # Step 5: Full RAG pipeline test
        print("\n5️⃣ Full RAG Pipeline Test:")
        full_result = rag_service.generate_response(
            query=test_query,
            user_lang='en',
            conversation_history=[],
            user_id='debug_user'
        )
        
        print(f"   Used Ollama: {full_result['used_openai']}")
        print(f"   Retrieval confidence: {full_result['retrieval_confidence']:.4f}")
        print(f"   Answer: {full_result['answer'][:200]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_rag_decision()
