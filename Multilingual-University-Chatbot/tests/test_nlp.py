import pytest
from services.nlp import NLPService

@pytest.fixture
def nlp_service():
    return NLPService()

def test_language_detection(nlp_service):
    assert nlp_service.detect_language("Hello world") == "en"
    assert nlp_service.detect_language("हॉस्टल शुल्क") == "hi"

def test_text_normalization(nlp_service):
    text = "  Hello   World  "
    normalized = nlp_service.normalize_text(text)
    assert normalized == "hello world"

def test_tokenization(nlp_service):
    tokens = nlp_service.tokenize("Hello world")
    assert len(tokens) >= 2
