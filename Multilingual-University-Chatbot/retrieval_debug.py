#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.retriever import RetrieverService
from config import Config

def debug_retrieval_confidence():
    print("🔍 Debugging Retrieval Confidence")
    print("=" * 50)
    
    try:
        # Initialize retriever
        retriever = RetrieverService()
        retriever.initialize()
        
        # Test different queries
        test_queries = [
            "Tell me about advanced computer science topics and research opportunities",
            "What are the campus facilities and infrastructure?",
            "Explain quantum computing and machine learning",
            "computer science courses"  # This should have higher similarity
        ]
        
        print(f"Current RETRIEVAL_THRESHOLD: {Config.RETRIEVAL_THRESHOLD}")
        print()
        
        for query in test_queries:
            print(f"Query: '{query}'")
            
            # Get retrieval results
            results = retriever.retrieve(query, language='en', top_k=5)
            
            if results:
                print(f"  📊 Found {len(results)} results:")
                for i, result in enumerate(results):
                    print(f"    {i+1}. Similarity: {result['similarity']:.4f} | Source: {result['source_id']}")
                    print(f"       Text: {result['text'][:100]}...")
                
                max_similarity = max(r['similarity'] for r in results)
                print(f"  🎯 Max similarity: {max_similarity:.4f}")
                print(f"  ✅ Above threshold ({Config.RETRIEVAL_THRESHOLD})? {max_similarity >= Config.RETRIEVAL_THRESHOLD}")
            else:
                print("  ❌ No results found")
            
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_retrieval_confidence()
