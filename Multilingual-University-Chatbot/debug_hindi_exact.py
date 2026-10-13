#!/usr/bin/env python3
"""
Debug Hindi exact matching issue
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from services.matcher import MatcherService

def debug_hindi_exact():
    print("🔍 Debugging Hindi Exact vs Fuzzy Matching")
    print("=" * 50)
    
    # Load FAQ data directly
    with open('data/faq.json', 'r', encoding='utf-8') as f:
        faq_data = json.load(f)
    
    # Find the specific FAQ
    test_query = "प्रवेश आवश्यकताएं क्या हैं?"
    target_faq = None
    
    for faq in faq_data:
        if faq['id'] == 'faq-0002':
            target_faq = faq
            break
    
    if not target_faq:
        print("❌ FAQ-0002 not found")
        return
    
    stored_question = target_faq['question']['hi']
    
    print(f"Test Query:     '{test_query}'")
    print(f"Stored Question: '{stored_question}'")
    print(f"Are they equal? {test_query == stored_question}")
    print()
    
    # Character-by-character comparison
    print("Character-by-character analysis:")
    print(f"Test Query length:     {len(test_query)}")
    print(f"Stored Question length: {len(stored_question)}")
    print()
    
    # Show character codes
    print("Test Query characters:")
    for i, char in enumerate(test_query):
        print(f"  {i:2d}: '{char}' (U+{ord(char):04X})")
    
    print("\nStored Question characters:")
    for i, char in enumerate(stored_question):
        print(f"  {i:2d}: '{char}' (U+{ord(char):04X})")
    
    # Find differences
    print("\nDifferences:")
    min_len = min(len(test_query), len(stored_question))
    differences = []
    
    for i in range(min_len):
        if test_query[i] != stored_question[i]:
            differences.append(f"Position {i}: '{test_query[i]}' vs '{stored_question[i]}'")
    
    if len(test_query) != len(stored_question):
        differences.append(f"Length difference: {len(test_query)} vs {len(stored_question)}")
    
    if differences:
        for diff in differences:
            print(f"  - {diff}")
    else:
        print("  No differences found (this is strange!)")
    
    # Test with matcher service
    print(f"\n🔧 Testing with Matcher Service:")
    matcher = MatcherService()
    matcher.load_faq_data()
    
    result = matcher.match_faq(test_query, "hi")
    print(f"Result: {result['match_type']} (confidence: {result['confidence']})")
    
    # Test string comparison directly
    print(f"\n🔧 Direct String Comparison:")
    print(f"test_query.lower().strip() == stored_question.lower().strip(): {test_query.lower().strip() == stored_question.lower().strip()}")
    
    # Test normalization
    from services.nlp import NLPService
    nlp = NLPService()
    
    normalized_test = nlp.normalize_text(test_query, "hi")
    print(f"Normalized test query: '{normalized_test}'")
    
    # Check if there are invisible characters
    print(f"\n🔧 Invisible Character Check:")
    print(f"Test query repr:     {repr(test_query)}")
    print(f"Stored question repr: {repr(stored_question)}")

if __name__ == "__main__":
    debug_hindi_exact()
