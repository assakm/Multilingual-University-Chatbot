import pytest
import tempfile
import os
from app import app
from services.retriever import RetrieverService
from services.matcher import MatcherService

@pytest.fixture
def client():
    """Create a test client"""
    # Create temporary database
    db_fd, app.config['DATABASE_URL'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            yield client
    
    os.close(db_fd)
    os.unlink(app.config['DATABASE_URL'])

@pytest.fixture
def sample_faq_data():
    """Sample FAQ data for testing"""
    return [
        {
            "id": "test-001",
            "question": {"en": "Test question?"},
            "answer": {"en": "Test answer"},
            "tags": ["test"],
            "last_updated": "2025-01-01"
        }
    ]
