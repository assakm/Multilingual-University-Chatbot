#!/usr/bin/env python3
"""
Debug fuzzy matching issues
"""
import sys
import os

# Ensure we can import from the project (redundant but safe)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.matcher import MatcherService
from config import Config

def debug_fuzzy_matching():
    print("🔍 Debugging Fuzzy Matching")
    print("=" * 40)
    
    try:
        # Initialize matcher
        matcher = MatcherService()
        matcher.load_faq_data()
        
        print(f"📊 FAQ data loaded: {len(matcher.faq_data)} entries")
        print(f"📊 Fuzzy thresholds: High={Config.FUZZY_HIGH_THRESHOLD}, Low={Config.FUZZY_LOW_THRESHOLD}")
        
        # Show available FAQs
        print("\n📋 Available FAQ Questions:")
        for i, faq in enumerate(matcher.faq_data):
            if 'en' in faq.get('question', {}):
                print(f"  {i+1}. {faq['question']['en']}")
        
        # Test fuzzy matching with debug info
        test_cases = [
            ("hostel fees", "en"),
            ("admission requirements", "en"),
            ("computer science courses", "en"),
            ("library facilities", "en")
        ]
        
        for query, lang in test_cases:
            print(f"\n🔍 Testing: '{query}' (language: {lang})")
            
            try:
                # Get available questions for this language
                questions = []
                for faq in matcher.faq_data:
                    if lang in faq.get('question', {}):
                        questions.append(faq['question'][lang])
                
                print(f"  Available questions ({len(questions)}):")
                for q in questions[:3]:  # Show first 3
                    print(f"    - {q}")
                if len(questions) > 3:
                    print(f"    ... and {len(questions)-3} more")
                
                # Test the matching
                result = matcher.match_faq(query, lang)
                print(f"  Match result: {result['match_type']} (confidence: {result['confidence']})")
                if result['answer']:
                    print(f"  Answer preview: {result['answer'][:100]}...")
                
                # Test rapidfuzz directly
                try:
                    from rapidfuzz import process, fuzz
                    
                    if questions:
                        # Try different scorers
                        scorers = [fuzz.ratio, fuzz.partial_ratio, fuzz.token_set_ratio, fuzz.token_sort_ratio]
                        scorer_names = ['ratio', 'partial_ratio', 'token_set_ratio', 'token_sort_ratio']
                        
                        for scorer, name in zip(scorers, scorer_names):
                            best_match = process.extractOne(
                                query,
                                questions,
                                scorer=scorer,
                                score_cutoff=40  # Lower threshold for testing
                            )
                            print(f"  {name}: {best_match}")
                
                except ImportError:
                    print("  ❌ RapidFuzz not available")
                
            except Exception as e:
                print(f"  ❌ Error testing '{query}': {e}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        print(f"❌ Failed to initialize matcher: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to check if FAQ file exists
        try:
            import json
            with open('data/faq.json', 'r', encoding='utf-8') as f:
                faq_data = json.load(f)
            print(f"✅ FAQ file readable directly: {len(faq_data)} entries")
        except Exception as e2:
            print(f"❌ FAQ file also not readable: {e2}")

if __name__ == "__main__":
    debug_fuzzy_matching()
