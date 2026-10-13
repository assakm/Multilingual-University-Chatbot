#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ollama_client import OllamaClient

def test_ollama_integration():
    print("🔧 Testing Ollama Integration")
    print("=" * 40)
    
    # Initialize client
    client = OllamaClient()
    
    # Test connection
    connection_test = client.test_connection()
    print(f"Connection test: {connection_test}")
    
    if not connection_test['success']:
        print("❌ Connection failed. Make sure Ollama is running:")
        print("   ollama serve")
        return
    
    # Test chat completion
    messages = [
        {"role": "system", "content": "You are a helpful university assistant. Answer concisely."},
        {"role": "user", "content": "What is computer science in 2 sentences?"}
    ]
    
    print("\n🤖 Testing chat completion...")
    response = client.chat_completion(messages)
    
    if response['success']:
        print(f"✅ Response: {response['content']}")
        print(f"📊 Tokens used: {response['tokens_used']}")
    else:
        print(f"❌ Error: {response['error']}")
    
    # Get stats
    stats = client.get_usage_stats()
    print(f"\n📊 Usage stats: {stats}")

if __name__ == "__main__":
    test_ollama_integration()
