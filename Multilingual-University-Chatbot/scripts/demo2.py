#!/usr/bin/env python3
"""
Demo script to showcase all chatbot flows with realistic test cases
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_scenario(name, user_id, message, expected_pipeline=None):
    """Test a specific scenario"""
    print(f"\n=== {name} ===")
    print(f"Input: {message}")
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json={
            "user_id": user_id,
            "message": message
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data['response'][:150]}..." if len(data['response']) > 150 else f"Response: {data['response']}")
            print(f"Pipeline: {data['pipeline_used']}")
            print(f"Language: {data['language']}")
            
            if expected_pipeline and data['pipeline_used'] != expected_pipeline:
                print(f"⚠️  Expected pipeline: {expected_pipeline}")
            else:
                print("✅ Pipeline matched expected result")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
    
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")

def main():
    """Run demo scenarios with realistic test cases"""
    print("🤖 RAG University Chatbot Demo")
    print("=" * 50)
    
    # Check health
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code != 200:
            print("❌ Chatbot is not running!")
            return
        print("✅ Chatbot is healthy and running")
    except requests.RequestException:
        print("❌ Cannot connect to chatbot. Make sure it's running on http://localhost:5000")
        return
    
    user_id = "demo_user"
    
    # Test scenarios that match your actual FAQ data
    scenarios = [
        # Rule-based responses
        ("Rule-based: Greeting", "Hello", "rule_based"),
        ("Rule-based: Contact Query", "contact number", "rule_based"),
        ("Rule-based: Thank You", "thank you", "rule_based"),
        
        # FAQ exact matches (these exist in your data)
        ("FAQ Exact Match: Hostel Fee", "What is the hostel fee?", "faq_exact"),
        ("FAQ Exact Match: Admission Requirements", "What are the admission requirements?", "faq_exact"),
        ("FAQ Exact Match: CS Courses", "What courses are offered in Computer Science?", "faq_exact"),
        ("FAQ Exact Match: Library", "What are the library facilities?", "faq_exact"),
        
        # Fuzzy matching (these should match existing FAQs)
        ("FAQ Fuzzy Match: Hostel", "hostel fees", "faq_high_fuzzy"),
        ("FAQ Fuzzy Match: Admission", "admission requirements", "faq_high_fuzzy"),
        ("FAQ Fuzzy Match: CS", "computer science courses", "faq_high_fuzzy"),
        ("FAQ Fuzzy Match: Library", "library facilities", "faq_high_fuzzy"),
        
        # Hindi queries (these exist in your data)
        ("Hindi Query: Hostel Fee", "हॉस्टल शुल्क क्या है?", "faq_exact"),
        ("Hindi Query: Admission", "प्रवेश आवश्यकताएं क्या हैं?", "faq_exact"),
        
        # RAG queries (topics not in FAQ, should use retrieval + OpenAI)
        ("RAG Query: Detailed CS Info", "Tell me about the computer science program structure and career opportunities", "rag_with_openai"),
        ("RAG Query: Campus Life", "What is campus life like and what extracurricular activities are available?", "rag_with_openai"),
        
        # No context (completely unrelated)
        ("No Context: Weather", "What's the weather like today?", "rag_no_openai"),
        ("No Context: Cooking", "How do I cook pasta?", "rag_no_openai")
    ]
    
    # Run all test scenarios
    for name, message, expected_pipeline in scenarios:
        test_scenario(name, user_id, message, expected_pipeline)
        time.sleep(1)  # Rate limiting
    
    print("\n" + "=" * 50)
    print("✅ Demo completed!")
    print("\n📊 Expected Results Summary:")
    print("- Rule-based queries should respond instantly")
    print("- FAQ exact matches should work perfectly") 
    print("- FAQ fuzzy matches should find similar questions")
    print("- Hindi queries should work for existing FAQs")
    print("- RAG queries should use retrieval + OpenAI (if API key is set)")
    print("- No context queries should return fallback responses")

def test_admin_functions():
    """Test admin functionality"""
    print("\n🔧 Testing Admin Functions")
    print("-" * 30)
    
    # Test stats
    try:
        response = requests.get(f"{BASE_URL}/admin/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ System Stats: {stats.get('faq_data', {}).get('total_faqs', 0)} FAQs loaded")
        else:
            print(f"❌ Stats endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Stats test failed: {e}")
    
    # Test reindex
    try:
        response = requests.post(f"{BASE_URL}/admin/reindex", timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Reindex: {result.get('message', 'Success')}")
        else:
            print(f"❌ Reindex failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Reindex test failed: {e}")

if __name__ == "__main__":
    main()
    test_admin_functions()
