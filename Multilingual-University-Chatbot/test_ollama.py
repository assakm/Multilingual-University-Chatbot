#!/usr/bin/env python3
import requests
import json

def test_ollama_simple():
    print("🤖 Testing Ollama Simple")
    print("=" * 30)
    
    # Test 1: Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print("✅ Ollama is running")
            print(f"Models: {[m['name'] for m in models['models']]}")
        else:
            print(f"❌ Ollama returned: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        print("💡 Make sure Ollama is running: ollama serve")
        return
    
    # Test 2: Simple generation
    payload = {
        "model": "llama3.2:3b",
        "prompt": "What is computer science? Answer in 2 sentences.",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 100
        }
    }
    
    print("\n🚀 Testing simple generation...")
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Generation successful!")
            print(f"Response: {result['response']}")
            print(f"Eval count: {result.get('eval_count', 'N/A')}")
        else:
            print(f"❌ Generation failed: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"❌ Generation error: {e}")

if __name__ == "__main__":
    test_ollama_simple()
