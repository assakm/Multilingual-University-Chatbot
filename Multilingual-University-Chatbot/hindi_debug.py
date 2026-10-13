#!/usr/bin/env python3
"""
Debug Hindi FAQ matching
"""
import sys
import os
import json

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.matcher import MatcherService

def debug_hindi_faq():
    print("🔍 Debugging Hindi FAQ")
    print("=" * 40)
    
    try:
        # Load FAQ data directly first
        print("📂 Loading FAQ data directly from file...")
        with open('data/faq.json', 'r', encoding='utf-8') as f:
            faq_data = json.load(f)
        
        print(f"📊 Total FAQs loaded: {len(faq_data)}")
        
        # Check Hindi questions
        hindi_questions = []
        for faq in faq_data:
            if 'hi' in faq.get('question', {}):
                hindi_questions.append({
                    'id': faq['id'],
                    'question': faq['question']['hi'],
                    'answer': faq['answer']['hi'][:100] + '...' if len(faq['answer']['hi']) > 100 else faq['answer']['hi']
                })
        
        print(f"\n📊 Hindi FAQs available ({len(hindi_questions)}):")
        for hq in hindi_questions:
            print(f"  {hq['id']}: {hq['question']}")
        
        # Test specific Hindi queries
        test_queries = [
            "हॉस्टल शुल्क क्या है?",
            "प्रवेश आवश्यकताएं क्या हैं?",
            "कंप्यूटर साइंस में कौन से कोर्स उपलब्ध हैं?"
        ]
        
        for test_query in test_queries:
            print(f"\n🔍 Testing query: '{test_query}'")
            
            # Test exact string comparison first
            found_exact = False
            for hq in hindi_questions:
                if test_query.lower().strip() == hq['question'].lower().strip():
                    print(f"✅ Exact match found: {hq['id']}")
                    found_exact = True
                    break
            
            if not found_exact:
                print("❌ No exact match found")
                print("  Character-by-character comparison:")
                for hq in hindi_questions:
                    question = hq['question']
                    if any(word in question for word in test_query.split()):
                        print(f"    Partial match with {hq['id']}: '{question}'")
                        print(f"    Test:  [{repr(test_query)}]")
                        print(f"    FAQ:   [{repr(question)}]")
                        print(f"    Equal: {test_query == question}")
            
            # Test with matcher service
            try:
                matcher = MatcherService()
                matcher.load_faq_data()
                
                result = matcher.match_faq(test_query, "hi")
                print(f"  Matcher result: {result['match_type']} (confidence: {result['confidence']})")
                
            except Exception as e:
                print(f"  ❌ Matcher error: {e}")
    
    except Exception as e:
        print(f"❌ Error loading FAQ data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_hindi_faq()
