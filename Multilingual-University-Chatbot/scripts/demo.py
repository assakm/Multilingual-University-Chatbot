#!/usr/bin/env python3
"""
Demo script to showcase all chatbot flows
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_scenario(name, user_id, message, expected_pipeline=None):
    """Test a specific scenario"""
    print(f"\n=== {name} ===")
    print(f"Input: {message}")
    
    response = requests.post(f"{BASE_URL}/chat", json={
        "user_id": user_id,
        "message": message
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data['response']}")
        print(f"Pipeline: {data['pipeline_used']}")
        print(f"Language: {data['language']}")
        
        if expected_pipeline and data['pipeline_used'] != expected_pipeline:
            print(f"⚠️  Expected pipeline: {expected_pipeline}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

def main():
    """Run demo scenarios"""
    print("🤖 RAG University Chatbot Demo")
    print("=" * 50)
    
    # Check health
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code != 200:
        print("❌ Chatbot is not running!")
        return
    
    user_id = "demo_user"
    
    # Test scenarios
    scenarios = [
        ("Rule-based: Greeting", "Hello", "rule_based"),
        ("FAQ Exact Match", "What is the hostel fee?", "faq_exact"),
        ("FAQ Fuzzy Match", "hostel fees", "faq_high_fuzzy"),
        ("RAG with OpenAI", "Tell me about computer science courses", "rag_with_openai"),
        ("Hindi Query", "हॉस्टल शुल्क क्या है?", "faq_exact"),
        ("No Context", "What's the weather like?", "rag_no_openai")
    ]
    
    for name, message, expected_pipeline in scenarios:
        test_scenario(name, user_id, message, expected_pipeline)
        time.sleep(1)  # Rate limiting
    
    print("\n✅ Demo completed!")

if __name__ == "__main__":
    main()
