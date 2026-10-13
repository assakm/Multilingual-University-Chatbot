#!/usr/bin/env python3
"""
Simple load testing script
"""
import requests
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:5000"

def send_request(user_id, message):
    """Send a single request"""
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/chat", json={
            "user_id": user_id,
            "message": message
        }, timeout=10)
        
        end_time = time.time()
        return {
            'status_code': response.status_code,
            'response_time': end_time - start_time,
            'success': response.status_code == 200
        }
    except Exception as e:
        return {
            'status_code': 0,
            'response_time': 0,
            'success': False,
            'error': str(e)
        }

def load_test(num_requests=100, num_threads=10):
    """Run load test"""
    print(f"🚀 Starting load test: {num_requests} requests with {num_threads} threads")
    
    messages = [
        "What is the hostel fee?",
        "Tell me about admission requirements",
        "Library facilities?",
        "Course information",
        "Contact details"
    ]
    
    results = []
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        
        for i in range(num_requests):
            user_id = f"load_test_user_{i % 10}"
            message = messages[i % len(messages)]
            future = executor.submit(send_request, user_id, message)
            futures.append(future)
        
        for future in futures:
            results.append(future.result())
    
    # Analyze results
    successful_requests = [r for r in results if r['success']]
    failed_requests = [r for r in results if not r['success']]
    
    if successful_requests:
        avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
        max_response_time = max(r['response_time'] for r in successful_requests)
        min_response_time = min(r['response_time'] for r in successful_requests)
    else:
        avg_response_time = max_response_time = min_response_time = 0
    
    print(f"\n📊 Load Test Results:")
    print(f"Total Requests: {num_requests}")
    print(f"Successful: {len(successful_requests)}")
    print(f"Failed: {len(failed_requests)}")
    print(f"Success Rate: {len(successful_requests)/num_requests*100:.1f}%")
    print(f"Average Response Time: {avg_response_time:.3f}s")
    print(f"Min Response Time: {min_response_time:.3f}s")
    print(f"Max Response Time: {max_response_time:.3f}s")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--threads", type=int, default=10)
    args = parser.parse_args()
    
    load_test(args.requests, args.threads)
