#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.nlp import NLPService
from services.matcher import MatcherService
from services.retriever import RetrieverService
from services.ollama_client import OllamaClient
from services.rag import RAGService

def debug_pipeline_step_by_step():
    print("🔍 Debugging Pipeline Step by Step")
    print("=" * 50)
    
    query = "What undergraduate programs does the university offer and what is the typical duration?"
    user_id = "debug_user"
    
    try:
        # Step 1: NLP Processing
        print("1️⃣ NLP Processing...")
        nlp_service = NLPService()
        user_lang = nlp_service.detect_language(query)
        normalized_message = nlp_service.normalize_text(query, user_lang)
        print(f"   Language: {user_lang}")
        print(f"   Normalized: '{normalized_message}'")
        
        # Step 2: Rule-based check
        print("\n2️⃣ Rule-based Check...")
        matcher_service = MatcherService()
        matcher_service.load_faq_data()
        rule_response = matcher_service.check_rules(normalized_message, user_lang)
        print(f"   Rule response: {rule_response}")
        
        # Step 3: FAQ matching
        print("\n3️⃣ FAQ Matching...")
        faq_result = matcher_service.match_faq(normalized_message, user_lang)
        print(f"   FAQ result: {faq_result['match_type']} (confidence: {faq_result['confidence']})")
        
        # Step 4: Intent detection
        print("\n4️⃣ Intent Detection...")
        intent_result = matcher_service.detect_intent(normalized_message, user_lang)
        print(f"   Intent result: {intent_result['confidence']:.4f}")
        
        # Step 5: RAG pipeline
        print("\n5️⃣ RAG Pipeline...")
        retriever_service = RetrieverService()
        retriever_service.initialize()
        
        ollama_client = OllamaClient()
        rag_service = RAGService(retriever_service, ollama_client)
        
        rag_result = rag_service.generate_response(
            query=normalized_message,
            user_lang=user_lang,
            conversation_history=[],
            user_id=user_id
        )
        
        print(f"   RAG used Ollama: {rag_result['used_openai']}")
        print(f"   RAG confidence: {rag_result['retrieval_confidence']:.4f}")
        print(f"   RAG answer: {rag_result['answer'][:200]}...")
        
    except Exception as e:
        print(f"❌ Error at step: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_pipeline_step_by_step()
