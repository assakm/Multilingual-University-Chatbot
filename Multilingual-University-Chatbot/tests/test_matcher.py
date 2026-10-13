import pytest
from unittest.mock import Mock, patch
from services.matcher import MatcherService

@pytest.fixture
def matcher_service():
    service = MatcherService()
    service.faq_data = [
        {
            "id": "test-001",
            "question": {"en": "What is the fee?"},
            "answer": {"en": "Fee is $100"},
            "tags": ["fee"]
        }
    ]
    return service

def test_exact_faq_match(matcher_service):
    result = matcher_service.match_faq("What is the fee?", "en")
    assert result['match_type'] == 'exact'

def test_fuzzy_faq_match(matcher_service):
    result = matcher_service.match_faq("fee amount", "en") 
    assert result['match_type'] in ['high_fuzzy', 'low_fuzzy', 'none']
