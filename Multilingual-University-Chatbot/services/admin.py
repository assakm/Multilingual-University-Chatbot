import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
import uuid

from config import Config
from services.retriever import RetrieverService
from services.matcher import MatcherService

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self):
        self.faq_file_path = Config.FAQ_FILE_PATH
        self._ensure_faq_file_exists()
    
    def _ensure_faq_file_exists(self):
        """Ensure FAQ file exists with sample data"""
        if not os.path.exists(self.faq_file_path):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.faq_file_path), exist_ok=True)
            
            # Create sample FAQ data
            sample_data = self._get_sample_faq_data()
            self._save_faq_data(sample_data)
            logger.info(f"Created initial FAQ file: {self.faq_file_path}")
    
    def _get_sample_faq_data(self) -> List[Dict]:
        """Get sample FAQ data in multiple languages"""
        return [
            {
                "id": "faq-0001",
                "question": {
                    "en": "What is the hostel fee?",
                    "hi": "हॉस्टल शुल्क क्या है?",
                    "ta": "விடுதி கட்டணம் என்ன?",
                    "te": "హాస్టల్ ఫీజు ఎంత?"
                },
                "answer": {
                    "en": "Hostel fee is ₹25,000 per semester. This includes accommodation, mess charges, and basic amenities. Payment can be made online or through bank draft.",
                    "hi": "हॉस्टल शुल्क प्रति सेमेस्टर ₹25,000 है। इसमें आवास, मेस शुल्क और बुनियादी सुविधाएं शामिल हैं। भुगतान ऑनलाइन या बैंक ड्राफ्ट के माध्यम से किया जा सकता है।",
                    "ta": "விடுதி கட்டணம் செமஸ்டருக்கு ₹25,000 ஆகும். இதில் தங்குமிடம், மெஸ் கட்டணம் மற்றும் அடிப्पടை வசதிகள் அடங்கும். கட்டணம் ऑनলைன் அல்லது வங்கி வரைவு மூலம் செலுत்தலாம்।",
                    "te": "హాస్టల్ ఫీజు సెమిస్టర్‌కు ₹25,000. ఇందులో వసతి, మెస్ ఛార్జీలు మరియు ప్రాథమిక సౌకర్యాలు ఉంటాయి. చెల్లింపు ఆన్‌లైన్ లేదా బ్యాంక్ డ్రాఫ్ట్ ద్వారా చేయవచ్చు."
                },
                "tags": ["hostel", "fees", "accommodation"],
                "sources": ["prospectus-2025.pdf"],
                "last_updated": "2025-01-01",
                "metadata": {"department": "student-affairs"}
            },
            {
                "id": "faq-0002", 
                "question": {
                    "en": "What are the admission requirements?",
                    "hi": "प्रवेश आवश्यकताएं क्या हैं?",
                    "ta": "சேர்க्கை தேவைகள் என்ன?",
                    "te": "ప్రవేశ అవసరాలు ఏమిటి?"
                },
                "answer": {
                    "en": "For undergraduate programs, you need 12th grade with minimum 60% marks. For postgraduate programs, a bachelor's degree with 55% marks is required. Entrance exam scores may also be considered.",
                    "hi": "अंडरग्रेजुएट कार्यक्रमों के लिए, आपको न्यूनतम 60% अंकों के साथ 12वीं कक्षा चाहिए। स्नातकोत्तर कार्यक्रमों के लिए, 55% अंकों के साथ स्नातक की डिग्री आवश्यक है। प्रवेश परीक्षा के अंकों पर भी विचार किया जा सकता है।",
                    "ta": "இளங்கलை திட்டங்களுக्கு, குறைந्தது 60% மதிப्पেण்களுடன் 12वां வகுप्પு தேवை. முதुकलै திட्डங्களுक्कु, 55% மதिप्पेण्களுடன् இளங्கலै पदवी तेवै। नुळैवु परीक्षै மतिप्पेण्களुम् विचारिक्कप्पडलाम्।",
                    "te": "అండర్‌గ్రాడ్యుయేట్ ప్రోగ్రామ్‌లకు, మీకు కనీసం 60% మార్కులతో 12వ తరగతి అవసరం. పోస్ట్‌గ్రాడ్యుయేట్ ప్రోగ్రామ్‌లకు, 55% మార్కులతో బ్యాచిలర్ డిగ్రీ అవసరం. ప్రవేశ పరీక్ష స్కోర్‌లను కూడా పరిగణించవచ్చు."
                },
                "tags": ["admission", "requirements", "eligibility"],
                "sources": ["admission-guide-2025.pdf"],
                "last_updated": "2025-01-01",
                "metadata": {"department": "admissions"}
            },
            {
                "id": "faq-0003",
                "question": {
                    "en": "What library facilities are available?",
                    "hi": "कौन सी पुस्तकालय सुविधाएं उपलब्ध हैं?",
                    "ta": "என்ன நூலगम् वसतिकळ् उपलब्धम्?",
                    "te": "ఏ లైబ్రరీ సౌకర్యాలు అందుబాటులో ఉన్నాయి?"
                },
                "answer": {
                    "en": "Our library is open 24/7 with over 100,000 books, digital resources, online databases, study spaces, and computer labs. Students get free access to all resources with their ID card.",
                    "hi": "हमारी लाइब्रेरी 24/7 खुली रहती है जिसमें 100,000 से अधिक पुस्तकें, डिजिटल संसाधन, ऑनलाइन डेटाबेस, अध्ययन स्थान और कंप्यूटर लैब हैं। छात्रों को अपने ID कार्ड के साथ सभी संसाधनों तक मुफ्त पहुंच मिलती है।",
                    "ta": "எங்கள் நூலகம் 24/7 திறந்திருக्கிறது, இதில் 1,00,000க्कुम् अधिकमान पुस्तकங्गळ्, цифरова संसाधनगळ्, ऑनलैन् डेटाबेस्, अध्ययन इडम् मत्तुम् कंप्यूटर् लैब्गळ् उळ्ळदु. विद्यार्थिगळ् तमम् ID कार्डिनिन्द सकळ संसाधनगळिग निशुल्क प्रवेश पडैदु.",
                    "te": "మా లైబ్రరీ 24/7 తెరిచి ఉంటుంది, ఇందులో 1,00,000కు మించిన పుస్తకాలు, డిజిటల్ వనరులు, ఆన్‌లైన్ డేటాబేస్‌లు, అధ్యయన స్థలాలు మరియు కంప్యూటర్ ల్యాబ్‌లు ఉన్నాయి. విద్యార్థులు వారి ID కార్డుతో అన్ని వనరులకు ఉచిత ప్రవేశం పొందుతారు."
                },
                "tags": ["library", "facilities", "books", "digital resources"],
                "sources": ["facilities-guide.pdf"],
                "last_updated": "2025-01-01",
                "metadata": {"department": "library"}
            }
        ]
    
    def _load_faq_data(self) -> List[Dict]:
        """Load FAQ data from file"""
        try:
            with open(self.faq_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading FAQ data: {e}")
            return []
    
    def _save_faq_data(self, data: List[Dict]):
        """Save FAQ data to file"""
        try:
            with open(self.faq_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving FAQ data: {e}")
            raise
    
    def get_all_faqs(self) -> List[Dict]:
        """Get all FAQ entries"""
        return self._load_faq_data()
    
    def add_faq_entry(self, faq_data: Dict) -> Dict:
        """Add a new FAQ entry"""
        try:
            # Validate required fields
            required_fields = ['question', 'answer']
            for field in required_fields:
                if field not in faq_data:
                    return {'success': False, 'message': f'Missing required field: {field}'}
            
            # Generate unique ID if not provided
            if 'id' not in faq_data:
                faq_data['id'] = f"faq-{uuid.uuid4().hex[:8]}"
            
            # Set default values
            faq_data.setdefault('tags', [])
            faq_data.setdefault('sources', [])
            faq_data.setdefault('metadata', {})
            faq_data['last_updated'] = datetime.now().strftime('%Y-%m-%d')
            
            # Load existing data
            faqs = self._load_faq_data()
            
            # Check for duplicate ID
            if any(faq['id'] == faq_data['id'] for faq in faqs):
                return {'success': False, 'message': f'FAQ with ID {faq_data["id"]} already exists'}
            
            # Add new FAQ
            faqs.append(faq_data)
            
            # Save to file
            self._save_faq_data(faqs)
            
            logger.info(f"Added new FAQ entry: {faq_data['id']}")
            return {'success': True, 'message': 'FAQ entry added successfully', 'id': faq_data['id']}
            
        except Exception as e:
            logger.error(f"Error adding FAQ entry: {e}")
            return {'success': False, 'message': f'Error adding FAQ entry: {str(e)}'}
    
    def update_faq_entry(self, faq_data: Dict) -> Dict:
        """Update an existing FAQ entry"""
        try:
            if 'id' not in faq_data:
                return {'success': False, 'message': 'Missing FAQ ID for update'}
            
            # Load existing data
            faqs = self._load_faq_data()
            
            # Find and update FAQ
            updated = False
            for i, faq in enumerate(faqs):
                if faq['id'] == faq_data['id']:
                    # Update timestamp
                    faq_data['last_updated'] = datetime.now().strftime('%Y-%m-%d')
                    faqs[i] = faq_data
                    updated = True
                    break
            
            if not updated:
                return {'success': False, 'message': f'FAQ with ID {faq_data["id"]} not found'}
            
            # Save to file
            self._save_faq_data(faqs)
            
            logger.info(f"Updated FAQ entry: {faq_data['id']}")
            return {'success': True, 'message': 'FAQ entry updated successfully'}
            
        except Exception as e:
            logger.error(f"Error updating FAQ entry: {e}")
            return {'success': False, 'message': f'Error updating FAQ entry: {str(e)}'}
    
    def delete_faq_entry(self, faq_id: str) -> Dict:
        """Delete an FAQ entry"""
        try:
            # Load existing data
            faqs = self._load_faq_data()
            
            # Find and remove FAQ
            original_length = len(faqs)
            faqs = [faq for faq in faqs if faq['id'] != faq_id]
            
            if len(faqs) == original_length:
                return {'success': False, 'message': f'FAQ with ID {faq_id} not found'}
            
            # Save to file
            self._save_faq_data(faqs)
            
            logger.info(f"Deleted FAQ entry: {faq_id}")
            return {'success': True, 'message': 'FAQ entry deleted successfully'}
            
        except Exception as e:
            logger.error(f"Error deleting FAQ entry: {e}")
            return {'success': False, 'message': f'Error deleting FAQ entry: {str(e)}'}
    
    def reindex_documents(self) -> Dict:
        """Reindex all documents in the vector store"""
        try:
            from services.retriever import RetrieverService
            retriever = RetrieverService()
            
            # Clear existing collection
            retriever.clear_collection()
            
            # Reload documents
            retriever._load_initial_documents()
            
            # Reload FAQ data in matcher
            from services.matcher import MatcherService
            matcher = MatcherService()
            matcher.load_faq_data()
            
            logger.info("Document reindexing completed successfully")
            return {
                'success': True,
                'message': 'Documents reindexed successfully',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during reindexing: {e}")
            return {
                'success': False,
                'message': f'Error during reindexing: {str(e)}'
            }
    
    def get_stats(self) -> Dict:
        """Get system statistics"""
        try:
            from services.retriever import RetrieverService
            from services.openai_client import OpenAIClient
            
            retriever = RetrieverService()
            openai_client = OpenAIClient()
            
            # Get collection stats
            vector_stats = retriever.get_collection_stats()
            
            # Get OpenAI usage stats
            openai_stats = openai_client.get_usage_stats()
            
            # Get FAQ stats
            faqs = self._load_faq_data()
            faq_stats = {
                'total_faqs': len(faqs),
                'languages': list(set().union(*[faq['question'].keys() for faq in faqs])),
                'departments': list(set(faq.get('metadata', {}).get('department', 'unknown') for faq in faqs))
            }
            
            return {
                'vector_store': vector_stats,
                'openai_usage': openai_stats,
                'faq_data': faq_stats,
                'system_status': 'healthy',
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
