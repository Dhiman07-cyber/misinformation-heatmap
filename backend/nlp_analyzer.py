"""
NLP Analysis pipeline using IndicBERT transformer for Indian languages.
Handles text preprocessing, language detection, named entity recognition,
and geographic entity extraction for misinformation detection.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# NLP and ML imports
import torch
from transformers import (
    AutoTokenizer, AutoModel, AutoModelForTokenClassification,
    pipeline, BertTokenizer, BertModel
)
import spacy
from langdetect import detect, DetectorFactory
import numpy as np

# Local imports
from config import config
from models import LanguageCode, ClaimCategory, INDIAN_STATES

# Set seed for consistent language detection
DetectorFactory.seed = 0

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class LanguageDetectionResult:
    """Result of language detection analysis"""
    language: LanguageCode
    confidence: float
    detected_lang_code: str
    is_supported: bool


@dataclass
class EntityExtractionResult:
    """Result of named entity recognition"""
    entities: List[str]
    geographic_entities: List[str]
    person_entities: List[str]
    organization_entities: List[str]
    locations: List[str]
    indian_states: List[str]


@dataclass
class TextAnalysisResult:
    """Complete text analysis result"""
    original_text: str
    cleaned_text: str
    language_detection: LanguageDetectionResult
    entities: EntityExtractionResult
    embeddings: Optional[np.ndarray]
    keywords: List[str]
    sentiment_score: float
    processing_time_ms: int
    metadata: Dict[str, Any]


class IndicBERTAnalyzer:
    """
    IndicBERT-based text analyzer for Indian languages.
    Supports Hindi, English, Bengali, and other Indian languages.
    """
    
    def __init__(self):
        self.config = config.get_nlp_config()
        self.device = self._get_device()
        
        # Initialize models
        self.tokenizer = None
        self.model = None
        self.ner_pipeline = None
        self.spacy_nlp = None
        
        # Indian geographic entities
        self.indian_states_set = set(INDIAN_STATES.keys())
        self.indian_cities = self._load_indian_cities()
        
        logger.info(f"Initializing IndicBERT analyzer on device: {self.device}")
    
    def _get_device(self) -> str:
        """Determine the best available device for processing"""
        if self.config["device"] == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return self.config["device"]
    
    def _load_indian_cities(self) -> set:
        """Load major Indian cities for geographic entity recognition"""
        # Major Indian cities - in production, this could be loaded from a comprehensive database
        cities = {
            "mumbai", "delhi", "bangalore", "hyderabad", "ahmedabad", "chennai",
            "kolkata", "surat", "pune", "jaipur", "lucknow", "kanpur", "nagpur",
            "indore", "thane", "bhopal", "visakhapatnam", "pimpri-chinchwad",
            "patna", "vadodara", "ghaziabad", "ludhiana", "agra", "nashik",
            "faridabad", "meerut", "rajkot", "kalyan-dombivali", "vasai-virar",
            "varanasi", "srinagar", "aurangabad", "dhanbad", "amritsar",
            "navi mumbai", "allahabad", "ranchi", "howrah", "coimbatore",
            "jabalpur", "gwalior", "vijayawada", "jodhpur", "madurai",
            "raipur", "kota", "guwahati", "chandigarh", "solapur"
        }
        return cities
    
    async def initialize(self) -> bool:
        """Initialize all NLP models and pipelines"""
        try:
            logger.info("Loading IndicBERT models...")
            
            # Load IndicBERT tokenizer and model
            model_name = self.config["model_name"]
            cache_dir = self.config["cache_dir"]
            
            # Get authentication token if available
            auth_token = self.config.get("hf_token")
            
            # Try to load tokenizer with proper parameters for IndicBERT
            try:
                # IndicBERT uses AlbertTokenizer, try that first
                from transformers import AlbertTokenizer
                
                tokenizer_kwargs = {
                    "cache_dir": cache_dir,
                    "do_lower_case": False
                }
                
                if auth_token:
                    tokenizer_kwargs["token"] = auth_token
                
                self.tokenizer = AlbertTokenizer.from_pretrained(
                    model_name,
                    **tokenizer_kwargs
                )
                logger.info("Successfully loaded IndicBERT tokenizer (Albert)")
                
            except Exception as e:
                logger.warning(f"Failed to load AlbertTokenizer: {e}")
                
                try:
                    # Try AutoTokenizer with trust_remote_code for custom tokenizers
                    tokenizer_kwargs = {
                        "cache_dir": cache_dir,
                        "do_lower_case": False,
                        "use_fast": False,
                        "trust_remote_code": True
                    }
                    
                    if auth_token:
                        tokenizer_kwargs["token"] = auth_token
                    
                    self.tokenizer = AutoTokenizer.from_pretrained(
                        model_name,
                        **tokenizer_kwargs
                    )
                    logger.info("Successfully loaded IndicBERT tokenizer (Auto with trust_remote_code)")
                    
                except Exception as e2:
                    logger.error(f"Failed to load any tokenizer: {e2}")
                    raise e2
            
            # Load model with authentication
            model_kwargs = {"cache_dir": cache_dir}
            if auth_token:
                model_kwargs["token"] = auth_token
                
            self.model = AutoModel.from_pretrained(
                model_name,
                **model_kwargs
            ).to(self.device)
            
            # Initialize NER pipeline for entity extraction
            try:
                self.ner_pipeline = pipeline(
                    "ner",
                    model="dbmdz/bert-large-cased-finetuned-conll03-english",
                    tokenizer="dbmdz/bert-large-cased-finetuned-conll03-english",
                    aggregation_strategy="simple",
                    device=0 if self.device == "cuda" else -1
                )
            except Exception as e:
                logger.warning(f"Failed to load NER pipeline: {e}. Using fallback.")
                self.ner_pipeline = None
            
            # Load spaCy model for additional NLP tasks
            try:
                self.spacy_nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
                self.spacy_nlp = None
            
            logger.info("IndicBERT analyzer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize IndicBERT analyzer: {e}")
            return False
    
    def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Detect the language of input text with confidence scoring.
        Maps detected languages to supported Indian language codes.
        """
        try:
            # Clean text for language detection
            cleaned_text = self._clean_text_for_language_detection(text)
            
            if len(cleaned_text.strip()) < 10:
                # Default to English for very short texts
                return LanguageDetectionResult(
                    language=LanguageCode.ENGLISH,
                    confidence=0.5,
                    detected_lang_code="en",
                    is_supported=True
                )
            
            # Detect language using langdetect
            detected_lang = detect(cleaned_text)
            
            # Map detected language to our supported languages
            lang_mapping = {
                "hi": LanguageCode.HINDI,
                "en": LanguageCode.ENGLISH,
                "bn": LanguageCode.BENGALI,
                "te": LanguageCode.TELUGU,
                "ta": LanguageCode.TAMIL,
                "gu": LanguageCode.GUJARATI,
                "kn": LanguageCode.KANNADA,
                "ml": LanguageCode.MALAYALAM,
                "or": LanguageCode.ORIYA,
                "pa": LanguageCode.PUNJABI,
                "mr": LanguageCode.MARATHI,
                "as": LanguageCode.ASSAMESE
            }
            
            mapped_lang = lang_mapping.get(detected_lang, LanguageCode.ENGLISH)
            is_supported = detected_lang in lang_mapping
            
            # Calculate confidence based on text characteristics
            confidence = self._calculate_language_confidence(text, detected_lang)
            
            return LanguageDetectionResult(
                language=mapped_lang,
                confidence=confidence,
                detected_lang_code=detected_lang,
                is_supported=is_supported
            )
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}. Defaulting to English.")
            return LanguageDetectionResult(
                language=LanguageCode.ENGLISH,
                confidence=0.3,
                detected_lang_code="en",
                is_supported=True
            )
    
    def _clean_text_for_language_detection(self, text: str) -> str:
        """Clean text for more accurate language detection"""
        # Remove URLs, mentions, hashtags
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#\w+', '', text)
        
        # Remove excessive whitespace and special characters
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\u0900-\u097F\u0980-\u09FF]', ' ', text)  # Keep Devanagari and Bengali scripts
        
        return text.strip()
    
    def _calculate_language_confidence(self, text: str, detected_lang: str) -> float:
        """Calculate confidence score for language detection"""
        base_confidence = 0.7
        
        # Boost confidence for longer texts
        if len(text) > 100:
            base_confidence += 0.1
        elif len(text) > 50:
            base_confidence += 0.05
        
        # Check for script-specific characters
        if detected_lang == "hi" and re.search(r'[\u0900-\u097F]', text):
            base_confidence += 0.15  # Devanagari script
        elif detected_lang == "bn" and re.search(r'[\u0980-\u09FF]', text):
            base_confidence += 0.15  # Bengali script
        elif detected_lang == "en" and re.search(r'[a-zA-Z]', text):
            base_confidence += 0.1   # Latin script
        
        return min(1.0, base_confidence)
    
    def preprocess_text(self, text: str, language: LanguageCode) -> str:
        """
        Preprocess text for IndicBERT analysis.
        Handles cleaning, normalization, and language-specific preprocessing.
        """
        # Basic cleaning
        cleaned_text = text.strip()
        
        # Remove excessive whitespace
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # Handle URLs and mentions
        cleaned_text = re.sub(r'http[s]?://\S+', '[URL]', cleaned_text)
        cleaned_text = re.sub(r'@\w+', '[MENTION]', cleaned_text)
        cleaned_text = re.sub(r'#(\w+)', r'\1', cleaned_text)  # Keep hashtag content
        
        # Language-specific preprocessing
        if language in [LanguageCode.HINDI, LanguageCode.MARATHI]:
            # Devanagari script normalization
            cleaned_text = self._normalize_devanagari(cleaned_text)
        elif language == LanguageCode.BENGALI:
            # Bengali script normalization
            cleaned_text = self._normalize_bengali(cleaned_text)
        
        # Truncate to model's maximum length
        max_length = self.config["max_text_length"]
        if len(cleaned_text) > max_length:
            cleaned_text = cleaned_text[:max_length-3] + "..."
        
        return cleaned_text
    
    def _normalize_devanagari(self, text: str) -> str:
        """Normalize Devanagari script text"""
        # Basic Devanagari normalization
        # In production, this could use more sophisticated normalization libraries
        return text
    
    def _normalize_bengali(self, text: str) -> str:
        """Normalize Bengali script text"""
        # Basic Bengali normalization
        return text
    
    def extract_entities(self, text: str, language: LanguageCode) -> EntityExtractionResult:
        """
        Extract named entities from text using multiple approaches.
        Focuses on geographic entities relevant to India.
        """
        entities = []
        geographic_entities = []
        person_entities = []
        organization_entities = []
        locations = []
        indian_states = []
        
        try:
            # Method 1: Use Transformers NER pipeline (if available)
            if self.ner_pipeline:
                ner_results = self.ner_pipeline(text)
                for entity in ner_results:
                    entity_text = entity['word'].strip()
                    entity_type = entity['entity_group']
                    
                    entities.append(entity_text)
                    
                    if entity_type in ['LOC', 'LOCATION']:
                        locations.append(entity_text)
                        if self._is_indian_geographic_entity(entity_text):
                            geographic_entities.append(entity_text)
                    elif entity_type in ['PER', 'PERSON']:
                        person_entities.append(entity_text)
                    elif entity_type in ['ORG', 'ORGANIZATION']:
                        organization_entities.append(entity_text)
            
            # Method 2: Use spaCy NER (if available)
            if self.spacy_nlp and language == LanguageCode.ENGLISH:
                doc = self.spacy_nlp(text)
                for ent in doc.ents:
                    entity_text = ent.text.strip()
                    entities.append(entity_text)
                    
                    if ent.label_ in ['GPE', 'LOC']:
                        locations.append(entity_text)
                        if self._is_indian_geographic_entity(entity_text):
                            geographic_entities.append(entity_text)
                    elif ent.label_ == 'PERSON':
                        person_entities.append(entity_text)
                    elif ent.label_ == 'ORG':
                        organization_entities.append(entity_text)
            
            # Method 3: Pattern-based extraction for Indian entities
            indian_entities = self._extract_indian_entities_by_pattern(text)
            geographic_entities.extend(indian_entities['states'])
            geographic_entities.extend(indian_entities['cities'])
            indian_states.extend(indian_entities['states'])
            
            # Remove duplicates and clean up
            entities = list(set([e for e in entities if len(e.strip()) > 1]))
            geographic_entities = list(set(geographic_entities))
            person_entities = list(set(person_entities))
            organization_entities = list(set(organization_entities))
            locations = list(set(locations))
            indian_states = list(set(indian_states))
            
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
        
        return EntityExtractionResult(
            entities=entities,
            geographic_entities=geographic_entities,
            person_entities=person_entities,
            organization_entities=organization_entities,
            locations=locations,
            indian_states=indian_states
        )
    
    def _is_indian_geographic_entity(self, entity: str) -> bool:
        """Check if an entity is an Indian geographic location"""
        entity_lower = entity.lower().strip()
        
        # Check against Indian states
        if entity_lower in self.indian_states_set:
            return True
        
        # Check against Indian cities
        if entity_lower in self.indian_cities:
            return True
        
        # Check for partial matches with Indian states
        for state in self.indian_states_set:
            if entity_lower in state or state in entity_lower:
                return True
        
        return False
    
    def _extract_indian_entities_by_pattern(self, text: str) -> Dict[str, List[str]]:
        """Extract Indian geographic entities using pattern matching"""
        text_lower = text.lower()
        
        found_states = []
        found_cities = []
        
        # Find Indian states
        for state in self.indian_states_set:
            if state in text_lower:
                found_states.append(state.title())
        
        # Find Indian cities
        for city in self.indian_cities:
            if city in text_lower:
                found_cities.append(city.title())
        
        return {
            'states': found_states,
            'cities': found_cities
        }
    
    def generate_embeddings(self, text: str) -> Optional[np.ndarray]:
        """
        Generate IndicBERT embeddings for the input text.
        Returns mean-pooled embeddings from the last hidden layer.
        """
        try:
            if not self.tokenizer or not self.model:
                logger.warning("IndicBERT model not initialized")
                return None
            
            # Tokenize input
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=self.config["max_text_length"]
            ).to(self.device)
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                
                # Use mean pooling of last hidden states
                last_hidden_states = outputs.last_hidden_state
                attention_mask = inputs['attention_mask']
                
                # Apply attention mask and compute mean
                masked_embeddings = last_hidden_states * attention_mask.unsqueeze(-1)
                summed_embeddings = torch.sum(masked_embeddings, dim=1)
                summed_mask = torch.sum(attention_mask, dim=1, keepdim=True)
                mean_embeddings = summed_embeddings / summed_mask
                
                # Convert to numpy
                embeddings = mean_embeddings.cpu().numpy().flatten()
                
                return embeddings
                
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return None
    
    def extract_keywords(self, text: str, language: LanguageCode, top_k: int = 10) -> List[str]:
        """
        Extract important keywords from text using multiple approaches.
        Combines frequency analysis with entity extraction.
        """
        keywords = []
        
        try:
            # Method 1: Simple frequency-based extraction
            words = re.findall(r'\b\w+\b', text.lower())
            
            # Filter out common stop words (basic list)
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
                'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
                'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its',
                'our', 'their', 'से', 'में', 'का', 'की', 'के', 'को', 'ने', 'पर', 'और'
            }
            
            # Count word frequencies
            word_freq = {}
            for word in words:
                if len(word) > 2 and word not in stop_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top frequent words
            frequent_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            keywords.extend([word for word, freq in frequent_words[:top_k//2]])
            
            # Method 2: Extract important entities as keywords
            entities_result = self.extract_entities(text, language)
            keywords.extend(entities_result.geographic_entities[:3])
            keywords.extend(entities_result.organization_entities[:2])
            
            # Method 3: Domain-specific keywords for misinformation detection
            misinfo_keywords = self._extract_misinformation_keywords(text)
            keywords.extend(misinfo_keywords)
            
            # Remove duplicates and limit to top_k
            keywords = list(set(keywords))[:top_k]
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
        
        return keywords
    
    def _extract_misinformation_keywords(self, text: str) -> List[str]:
        """Extract keywords commonly associated with misinformation"""
        text_lower = text.lower()
        
        # Common misinformation indicators
        misinfo_patterns = [
            'fake', 'false', 'hoax', 'conspiracy', 'secret', 'hidden', 'cover-up',
            'leaked', 'exposed', 'truth', 'real story', 'mainstream media',
            'government', 'vaccine', 'covid', 'virus', 'election', 'fraud',
            'scam', 'dangerous', 'warning', 'alert', 'urgent', 'breaking'
        ]
        
        found_keywords = []
        for pattern in misinfo_patterns:
            if pattern in text_lower:
                found_keywords.append(pattern)
        
        return found_keywords[:5]  # Limit to top 5
    
    def calculate_sentiment_score(self, text: str) -> float:
        """
        Calculate sentiment score for the text.
        Returns value between -1 (negative) and 1 (positive).
        """
        try:
            # Simple sentiment analysis based on word patterns
            # In production, this could use more sophisticated sentiment models
            
            positive_words = [
                'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
                'positive', 'happy', 'joy', 'success', 'win', 'victory', 'hope'
            ]
            
            negative_words = [
                'bad', 'terrible', 'awful', 'horrible', 'disaster', 'crisis',
                'negative', 'sad', 'angry', 'fear', 'danger', 'threat', 'attack',
                'death', 'kill', 'destroy', 'harm', 'damage', 'fail', 'loss'
            ]
            
            words = re.findall(r'\b\w+\b', text.lower())
            
            positive_count = sum(1 for word in words if word in positive_words)
            negative_count = sum(1 for word in words if word in negative_words)
            
            total_sentiment_words = positive_count + negative_count
            
            if total_sentiment_words == 0:
                return 0.0  # Neutral
            
            sentiment_score = (positive_count - negative_count) / total_sentiment_words
            return max(-1.0, min(1.0, sentiment_score))
            
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return 0.0
    
    async def analyze_text(self, text: str) -> TextAnalysisResult:
        """
        Perform complete text analysis including language detection,
        entity extraction, embedding generation, and keyword extraction.
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Language detection
            language_result = self.detect_language(text)
            
            # Step 2: Text preprocessing
            cleaned_text = self.preprocess_text(text, language_result.language)
            
            # Step 3: Entity extraction
            entities_result = self.extract_entities(cleaned_text, language_result.language)
            
            # Step 4: Generate embeddings
            embeddings = self.generate_embeddings(cleaned_text)
            
            # Step 5: Extract keywords
            keywords = self.extract_keywords(cleaned_text, language_result.language)
            
            # Step 6: Calculate sentiment
            sentiment_score = self.calculate_sentiment_score(cleaned_text)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Compile metadata
            metadata = {
                "model_name": self.config["model_name"],
                "device": self.device,
                "text_length": len(text),
                "cleaned_text_length": len(cleaned_text),
                "embedding_dimension": len(embeddings) if embeddings is not None else 0,
                "entities_count": len(entities_result.entities),
                "geographic_entities_count": len(entities_result.geographic_entities)
            }
            
            return TextAnalysisResult(
                original_text=text,
                cleaned_text=cleaned_text,
                language_detection=language_result,
                entities=entities_result,
                embeddings=embeddings,
                keywords=keywords,
                sentiment_score=sentiment_score,
                processing_time_ms=int(processing_time),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Text analysis failed: {e}")
            
            # Return minimal result on failure
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return TextAnalysisResult(
                original_text=text,
                cleaned_text=text,
                language_detection=LanguageDetectionResult(
                    language=LanguageCode.ENGLISH,
                    confidence=0.3,
                    detected_lang_code="en",
                    is_supported=True
                ),
                entities=EntityExtractionResult(
                    entities=[], geographic_entities=[], person_entities=[],
                    organization_entities=[], locations=[], indian_states=[]
                ),
                embeddings=None,
                keywords=[],
                sentiment_score=0.0,
                processing_time_ms=int(processing_time),
                metadata={"error": str(e)}
            )


# Global analyzer instance
nlp_analyzer = IndicBERTAnalyzer()