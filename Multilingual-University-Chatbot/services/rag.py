import logging
from typing import Dict, List, Optional
from datetime import datetime

from config import Config
from services.retriever import RetrieverService
from services.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, retriever: RetrieverService, openai_client: OpenAIClient):
        self.retriever = retriever
        self.openai_client = openai_client
        
        # System prompt template
        self.system_prompt_template = """You are a helpful, concise university assistant. Use only the facts provided in the CONTEXT sections below. If the answer cannot be drawn from that context, say you do not know and propose safe next steps (suggest the relevant office/FAQ page or ask clarifying questions). Do not hallucinate. Answer in {user_lang}. Keep answers ≤ 300 words unless asked otherwise.

CONTEXT:
{context}

Remember to cite the sources by doc_id in your final answer (e.g., [source: doc_12])."""
    
    def generate_response(self, query: str, user_lang: str, conversation_history: List[Dict] = None, user_id: str = None) -> Dict:
        """
        Generate response using RAG pipeline
        """
        result = {
            'answer': '',
            'sources': [],
            'used_openai': False,
            'retrieval_confidence': 0.0,
            'context_used': ''
        }
        
        try:
            # Step 1: Retrieve relevant documents
            retrieved_docs = self.retriever.retrieve(
                query=query,
                language=user_lang,
                top_k=Config.TOP_K_RETRIEVAL
            )
            
            if not retrieved_docs:
                logger.info("No relevant documents found")
                result['answer'] = self._get_no_context_response(user_lang)
                return result
            
            # Step 2: Assess retrieval quality
            retrieval_confidence = self._assess_retrieval_quality(retrieved_docs)
            result['retrieval_confidence'] = retrieval_confidence
            
            # Step 3: Build context
            context, sources = self._build_context(retrieved_docs)
            result['context_used'] = context
            result['sources'] = sources
            
            # Step 4: Decide whether to call OpenAI
            if retrieval_confidence >= Config.RETRIEVAL_THRESHOLD:
                # High confidence retrieval - use OpenAI
                openai_response = self._call_openai(
                    query=query,
                    context=context,
                    user_lang=user_lang,
                    conversation_history=conversation_history
                )
                
                if openai_response['success']:
                    result['answer'] = openai_response['answer']
                    result['used_openai'] = True
                else:
                    # OpenAI failed, use fallback
                    result['answer'] = self._create_fallback_response(retrieved_docs, user_lang)
            else:
                # Low confidence retrieval - use local summarization
                result['answer'] = self._create_local_response(retrieved_docs, user_lang)
            
        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}")
            result['answer'] = self._get_error_response(user_lang)
        
        return result
    
    '''def _assess_retrieval_quality(self, retrieved_docs: List[Dict]) -> float:
        """Assess the quality of retrieved documents"""
        if not retrieved_docs:
            return 0.0
        
        # Use the highest similarity score as confidence
        max_similarity = max(doc['similarity'] for doc in retrieved_docs)
        
        # Also consider the number of relevant documents
        high_quality_docs = sum(1 for doc in retrieved_docs if doc['similarity'] >= 0.7)
        coverage_factor = min(high_quality_docs / 3.0, 1.0)  # Normalize to max 1.0
        
        return max_similarity * coverage_factor'''
    

    def _assess_retrieval_quality(self, retrieved_docs: List[Dict]) -> float:
        """Assess the quality of retrieved documents"""
        if not retrieved_docs:
            return 0.0
        
        # Use the highest similarity score as confidence
        similarities = [doc['similarity'] for doc in retrieved_docs]
        max_similarity = max(similarities)
        
        # Count high quality documents
        high_quality_docs = sum(1 for sim in similarities if sim >= 0.1)
        
        # Log for debugging
        logger.info(f"Retrieval assessment: max_sim={max_similarity:.4f}, high_quality={high_quality_docs}, total={len(retrieved_docs)}")
        
        # FIXED: Return the actual max similarity (was returning 0.0 somehow)
        return max_similarity

    
    def _build_context(self, retrieved_docs: List[Dict]) -> tuple:
        """Build context string and sources list from retrieved documents"""
        context_parts = []
        sources = []
        total_length = 0
        
        for i, doc in enumerate(retrieved_docs, 1):
            source_info = {
                'doc_id': doc['source_id'],
                'similarity': doc['similarity'],
                'document_type': doc['metadata'].get('document_type', 'unknown'),
                'department': doc['metadata'].get('department', ''),
                'last_updated': doc['metadata'].get('last_updated', '')
            }
            sources.append(source_info)
            
            # Format context entry
            context_entry = f"CONTEXT {i}/{len(retrieved_docs)} (source: {doc['source_id']} | score: {doc['similarity']:.3f}): {doc['text']}"
            
            # Check length limit
            if total_length + len(context_entry) > Config.MAX_CONTEXT_LENGTH:
                logger.info(f"Context truncated at {total_length} characters")
                break
            
            context_parts.append(context_entry)
            total_length += len(context_entry)
        
        return '\n\n'.join(context_parts), sources
    
    def _call_openai(self, query: str, context: str, user_lang: str, conversation_history: List[Dict] = None) -> Dict:
        """Call OpenAI with the constructed prompt"""
        try:
            # Build system message
            system_message = self.system_prompt_template.format(
                user_lang=user_lang,
                context=context
            )
            
            # Build user message with conversation history
            user_message = self._build_user_message(query, conversation_history)
            
            # Call OpenAI
            response = self.openai_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=Config.OPENAI_TEMPERATURE,
                max_tokens=Config.OPENAI_MAX_TOKENS
            )
            
            if response['success']:
                return {
                    'success': True,
                    'answer': response['content'],
                    'tokens_used': response.get('tokens_used', 0)
                }
            else:
                logger.error(f"OpenAI call failed: {response['error']}")
                return {'success': False, 'error': response['error']}
        
        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}")
            return {'success': False, 'error': str(e)}
    
    def _build_user_message(self, query: str, conversation_history: List[Dict] = None) -> str:
        """Build user message including conversation history"""
        message_parts = []
        
        # Add conversation history (last 3 exchanges)
        if conversation_history:
            recent_history = conversation_history[-6:]  # Last 3 Q&A pairs
            history_text = []
            
            for entry in recent_history:
                if entry.get('role') == 'user':
                    history_text.append(f"User: {entry.get('content', '')}")
                elif entry.get('role') == 'assistant':
                    history_text.append(f"Assistant: {entry.get('content', '')}")
            
            if history_text:
                message_parts.append("Previous conversation:")
                message_parts.extend(history_text)
                message_parts.append("\n---\n")
        
        # Add current query
        message_parts.append(f"Current question: {query}")
        
        return '\n'.join(message_parts)
    
    def _create_fallback_response(self, retrieved_docs: List[Dict], user_lang: str) -> str:
        """Create fallback response when OpenAI fails"""
        if not retrieved_docs:
            return self._get_no_context_response(user_lang)
        
        # Create a simple summary of retrieved documents
        summary_parts = []
        
        if user_lang == 'hi':
            summary_parts.append("मुझे निम्नलिखित जानकारी मिली:")
        elif user_lang == 'ta':
            summary_parts.append("எனக்கு பின்வரும் தகவல் கிடைத்தது:")
        elif user_lang == 'te':
            summary_parts.append("నాకు ఈ క్రింది సమాచారం లభించింది:")
        else:
            summary_parts.append("I found the following relevant information:")
        
        for doc in retrieved_docs[:2]:  # Show top 2 results
            summary_parts.append(f"\n- {doc['text'][:200]}..." if len(doc['text']) > 200 else f"\n- {doc['text']}")
        
        # Add fallback message
        fallback_msg = {
            'en': "\n\nFor more detailed information, please contact our support team at support@university.edu",
            'hi': "\n\nअधिक विस्तृत जानकारी के लिए, कृपया support@university.edu पर हमारी सहायता टीम से संपर्क करें",
            'ta': "\n\nமேலும் விரிவான தகவலுக்கு, support@university.edu இல் எங்கள் ஆதரவு குழுவைத் தொடர்பு கொள்ளவும்",
            'te': "\n\nమరింత వివరమైన సమాచారం కోసం, దయచేసి support@university.edu వద్ద మా మద్దతు బృందాన్ని సంప్రదించండి"
        }.get(user_lang, "For more information, please contact our support team.")
        
        summary_parts.append(fallback_msg)
        
        return ''.join(summary_parts)
    
    def _create_local_response(self, retrieved_docs: List[Dict], user_lang: str) -> str:
        """Create local response without OpenAI"""
        if not retrieved_docs:
            return self._get_no_context_response(user_lang)
        
        # Use the most relevant document
        best_doc = retrieved_docs[0]
        
        response_parts = []
        
        # Add the most relevant content
        response_parts.append(best_doc['text'])
        
        # Add source attribution
        source_msg = {
            'en': f"\n\n[Source: {best_doc['source_id']}]",
            'hi': f"\n\n[स्रोत: {best_doc['source_id']}]",
            'ta': f"\n\n[ஆதாரம்: {best_doc['source_id']}]",
            'te': f"\n\n[మూలం: {best_doc['source_id']}]"
        }.get(user_lang, f"\n\n[Source: {best_doc['source_id']}]")
        
        response_parts.append(source_msg)
        
        # Add additional context if available
        if len(retrieved_docs) > 1:
            additional_msg = {
                'en': "\n\nFor related information, you might also want to know about our other services and facilities.",
                'hi': "\n\nसंबंधित जानकारी के लिए, आप हमारी अन्य सेवाओं और सुविधाओं के बारे में भी जानना चाह सकते हैं।",
                'ta': "\n\nதொடர்புடைய தகவலுக्कு, எங்கள் மற்ற சेवைகள் மற்றும் வசதிகளைப் பற்றியும் நீங்கள் அறிய விரும्பலாம्।",
                'te': "\n\nసంబంధిత సమాచారం కోసం, మీరు మా ఇతర సేవలు మరియు సౌకర्यాల గురించి కూడా తెలుసుకోవాలని అనుకోవచ్చు।"
            }.get(user_lang, "\n\nFor related information, you might also want to know about our other services.")
            
            response_parts.append(additional_msg)
        
        return ''.join(response_parts)
    
    def _get_no_context_response(self, user_lang: str) -> str:
        """Get response when no relevant context is found"""
        responses = {
            'en': "I don't have specific information about that topic in my knowledge base. Please contact our support team at support@university.edu or visit our main website for more information.",
            'hi': "मेरे ज्ञान आधार में उस विषय के बारे में विशिष्ट जानकारी नहीं है। कृपया support@university.edu पर हमारी सहायता टीम से संपर्क करें या अधिक जानकारी के लिए हमारी मुख्य वेबसाइट पर जाएं।",
            'ta': "எ ள்ள் அ ப் ப் ப் எ த்த கவல் எ த் த தகவல் க்क क்क க्। त त्त त त्त च त त त त त त त त त त त त त त त त त त त त त त त त त त त त त.",
            'te': "ఆ విషయం గురించి నా జ్ఞాన ఆధారంలో నిర్దిష్ట సమాచారం లేదు. దయచేసి support@university.edu వద్ద మా మద్దతు బృందాన్ని సంప్రదించండి లేదా మరింత సమాచారం కోసం మా ముఖ్య వెబ్‌సైట్‌ను సందర్శించండి."
        }
        return responses.get(user_lang, responses['en'])
    
    def _get_error_response(self, user_lang: str) -> str:
        """Get response for system errors"""
        responses = {
            'en': "I'm experiencing technical difficulties. Please try again in a moment or contact support@university.edu for immediate assistance.",
            'hi': "मुझे तकनीकी कठिनाइयों का सामना हो रहा है। कृपया एक क्षण बाद पुनः प्रयास करें या तत्काल सहायता के लिए support@university.edu से संपर्क करें।",
            'ta': "எനक்கு தொழিநுട्पावसील त्त त त त त त त त त ত त ত त त त त त त ত ত ত ত ত ত ত ত ত ত ত ত ত ત ত",
            'te': "నేను సాంకేతిక ఇబ్బందులను ఎదుర్కొంటున్నాను. దయచేసి కొద్దిసేపటి తర్వాత మళ్లీ ప్రయత్నించండి లేదా తక్షణ సహాయం కోసం support@university.edu ని సంప్రదించండి."
        }
        return responses.get(user_lang, responses['en'])
