import pytest
import json

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_chat_endpoint_missing_fields(client):
    """Test chat endpoint with missing fields"""
    response = client.post('/chat', json={})
    assert response.status_code == 400

def test_chat_endpoint_valid_request(client):
    """Test chat endpoint with valid request"""
    response = client.post('/chat', json={
        'user_id': 'test_user',
        'message': 'Hello'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'response' in data
    assert 'conversation_id' in data

def test_faq_management(client):
    """Test FAQ management endpoints"""
    # Add FAQ
    faq_data = {
        "question": {"en": "Test question?"},
        "answer": {"en": "Test answer"},
        "tags": ["test"]
    }
    response = client.post('/admin/faq', json=faq_data)
    assert response.status_code == 200
    
    # Get FAQs
    response = client.get('/admin/faq')
    assert response.status_code == 200
