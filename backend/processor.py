"""
Event processing pipeline that orchestrates NLP analysis, claim extraction,
virality scoring, and satellite validation for misinformation detection.
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Local imports
from config import config
from models import (
    ProcessedEvent, Claim, SatelliteResult, EventSource, LanguageCode, 
    ClaimCategory, INDIAN_STATES, normalize_state_name
)
from nlp_analyzer import nlp_analyzer, TextAnalysisResult
from database import database

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RawEvent:
    """Raw event data before processing"""
    source: EventSource
    original_text: str
    timestamp: datetime
    metadata: Dict[str, Any]
    url: Optional[str] = None
    author: Optional[str] = None
    engagement_metrics: Optional[Dict[str, int]] = None


@dataclass
class ClaimExtractionResult:
    """Result of claim extraction from text"""
    claims: List[Claim]
    primary_claim: Optional[Claim]
    confidence_score: float
    extraction_method: str
    processing_metadata: Dict[str, Any]


class ClaimExtractor:
    """
    Extracts and analyzes claims from text content.
    Uses pattern matching, NLP analysis, and heuristics to identify
    potential misinformation claims.
    """
    
    def __init__(self):
        self.misinformation_patterns = self._load_misinformation_patterns()
        self.claim_indicators = self._load_claim_indicators()
        
    def _load_misinformation_patterns(self) -> Dict[str, List[str]]:
        """Load patterns commonly associated with misinformation"""
        return {
            "health": [
                r"vaccine.*(?:cause|dangerous|kill|harm|side effect)",
                r"covid.*(?:hoax|fake|conspiracy|planned)",
                r"medicine.*(?:hidden|secret|banned|suppressed)",
                r"doctor.*(?:don't want|hiding|secret)",
                r"cure.*(?:they|government|pharma).*(?:don't want|hiding)"
            ],
            "politics": [
                r"election.*(?:rigged|fraud|stolen|fake)",
                r"government.*(?:hiding|secret|conspiracy|cover.?up)",
                r"politician.*(?:corrupt|bribe|scandal|secret)",
                r"vote.*(?:fraud|illegal|fake|manipulation)",
                r"media.*(?:lying|fake|propaganda|biased)"
            ],
            "disaster": [
                r"earthquake.*(?:predicted|warning|coming|artificial)",
                r"flood.*(?:artificial|man.?made|planned|conspiracy)",
                r"cyclone.*(?:artificial|weather manipulation|planned)",
                r"disaster.*(?:planned|artificial|government|conspiracy)"
            ],
            "technology": [
                r"5g.*(?:dangerous|radiation|cancer|kill|harm)",
                r"phone.*(?:radiation|cancer|dangerous|spy)",
                r"internet.*(?:control|surveillance|spy|track)",
                r"ai.*(?:dangerous|control|replace|eliminate)"
            ],
            "social": [
                r"community.*(?:under attack|threat|danger|conspiracy)",
                r"religion.*(?:under threat|attack|conspiracy|persecution)",
                r"culture.*(?:destroyed|attack|threat|conspiracy)",
                r"tradition.*(?:under attack|threat|destroyed)"
            ]
        }
    
    def _load_claim_indicators(self) -> List[str]:
        """Load linguistic indicators of claims"""
        return [
            # Assertion indicators
            "it is true that", "the fact is", "evidence shows", "studies prove",
            "research confirms", "scientists say", "experts claim", "data reveals",
            
            # Certainty indicators
            "definitely", "certainly", "absolutely", "without doubt", "clearly",
            "obviously", "undoubtedly", "proven", "confirmed", "established",
            
            # Urgency indicators
            "urgent", "breaking", "alert", "warning", "immediate", "emergency",
            "critical", "important", "must know", "shocking", "exposed",
            
            # Authority indicators
            "according to", "sources say", "reports indicate", "leaked documents",
            "insider information", "confidential", "classified", "secret documents"
        ]
    
    def extract_claims(self, text_analysis: TextAnalysisResult) -> ClaimExtractionResult:
        """
        Extract claims from analyzed text using multiple approaches.
        """
        try:
            claims = []
            extraction_methods = []
            
            text = text_analysis.cleaned_text
            language = text_analysis.language_detection.language
            
            # Method 1: Pattern-based claim extraction
            pattern_claims = self._extract_claims_by_patterns(text, language)
            claims.extend(pattern_claims)
            if pattern_claims:
                extraction_methods.append("pattern_matching")
            
            # Method 2: Sentence-based claim extraction
            sentence_claims = self._extract_claims_by_sentences(text, text_analysis)
            claims.extend(sentence_claims)
            if sentence_claims:
                extraction_methods.append("sentence_analysis")
            
            # Method 3: Entity-based claim extraction
            entity_claims = self._extract_claims_by_entities(text, text_analysis)
            claims.extend(entity_claims)
            if entity_claims:
                extraction_methods.append("entity_analysis")
            
            # Remove duplicates and rank by confidence
            unique_claims = self._deduplicate_claims(claims)
            ranked_claims = sorted(unique_claims, key=lambda c: c.confidence, reverse=True)
            
            # Select primary claim (highest confidence)
            primary_claim = ranked_claims[0] if ranked_claims else None
            
            # Calculate overall confidence
            overall_confidence = (
                sum(claim.confidence for claim in ranked_claims) / len(ranked_claims)
                if ranked_claims else 0.0
            )
            
            processing_metadata = {
                "extraction_methods": extraction_methods,
                "total_claims_found": len(claims),
                "unique_claims": len(unique_claims),
                "text_length": len(text),
                "language": language.value,
                "sentiment_score": text_analysis.sentiment_score
            }
            
            return ClaimExtractionResult(
                claims=ranked_claims[:5],  # Limit to top 5 claims
                primary_claim=primary_claim,
                confidence_score=overall_confidence,
                extraction_method=", ".join(extraction_methods),
                processing_metadata=processing_metadata
            )
            
        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            return ClaimExtractionResult(
                claims=[],
                primary_claim=None,
                confidence_score=0.0,
                extraction_method="error",
                processing_metadata={"error": str(e)}
            )
    
    def _extract_claims_by_patterns(self, text: str, language: LanguageCode) -> List[Claim]:
        """Extract claims using predefined misinformation patterns"""
        claims = []
        text_lower = text.lower()
        
        for category, patterns in self.misinformation_patterns.items():
            for pattern in patterns:
                import re
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                
                for match in matches:
                    # Extract surrounding context
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    claim_text = text[start:end].strip()
                    
                    # Calculate confidence based on pattern specificity
                    confidence = 0.7 + (len(pattern) / 100)  # More specific patterns get higher confidence
                    confidence = min(0.95, confidence)
                    
                    claim = Claim(
                        text=claim_text,
                        category=ClaimCategory(category),
                        confidence=confidence,
                        keywords=[match.group()],
                        entities=[]
                    )
                    claims.append(claim)
        
        return claims
    
    def _extract_claims_by_sentences(self, text: str, text_analysis: TextAnalysisResult) -> List[Claim]:
        """Extract claims by analyzing individual sentences"""
        claims = []
        
        # Split text into sentences
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            if len(sentence.strip()) < 20:  # Skip very short sentences
                continue
            
            # Check for claim indicators
            claim_score = self._calculate_sentence_claim_score(sentence)
            
            if claim_score > 0.5:  # Threshold for considering as a claim
                # Determine category based on content
                category = self._categorize_claim(sentence)
                
                # Extract entities from this sentence
                sentence_entities = []
                for entity in text_analysis.entities.entities:
                    if entity.lower() in sentence.lower():
                        sentence_entities.append(entity)
                
                claim = Claim(
                    text=sentence.strip(),
                    category=category,
                    confidence=claim_score,
                    entities=sentence_entities,
                    geographic_entities=[
                        e for e in text_analysis.entities.geographic_entities
                        if e.lower() in sentence.lower()
                    ]
                )
                claims.append(claim)
        
        return claims
    
    def _extract_claims_by_entities(self, text: str, text_analysis: TextAnalysisResult) -> List[Claim]:
        """Extract claims based on important entities and their context"""
        claims = []
        
        # Focus on geographic entities (Indian states/cities)
        for geo_entity in text_analysis.entities.geographic_entities:
            # Find sentences containing this entity
            sentences = self._find_sentences_with_entity(text, geo_entity)
            
            for sentence in sentences:
                # Check if this sentence makes claims about the geographic entity
                if self._contains_geographic_claim(sentence, geo_entity):
                    confidence = 0.6 + (0.2 if geo_entity.lower() in INDIAN_STATES else 0.1)
                    
                    claim = Claim(
                        text=sentence.strip(),
                        category=self._categorize_claim(sentence),
                        confidence=min(0.9, confidence),
                        entities=[geo_entity],
                        geographic_entities=[geo_entity]
                    )
                    claims.append(claim)
        
        return claims
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using simple heuristics"""
        import re
        
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Minimum sentence length
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _calculate_sentence_claim_score(self, sentence: str) -> float:
        """Calculate how likely a sentence is to contain a claim"""
        score = 0.0
        sentence_lower = sentence.lower()
        
        # Check for claim indicators
        for indicator in self.claim_indicators:
            if indicator in sentence_lower:
                score += 0.2
        
        # Check for assertion patterns
        assertion_patterns = [
            r'\b(is|are|was|were)\s+\w+',  # "is dangerous", "are fake"
            r'\b(will|would|can|could)\s+\w+',  # "will cause", "can kill"
            r'\b(always|never|all|every|no)\s+\w+',  # Absolute statements
            r'\b(proven|confirmed|established|fact)\b'  # Certainty claims
        ]
        
        import re
        for pattern in assertion_patterns:
            if re.search(pattern, sentence_lower):
                score += 0.15
        
        # Boost score for controversial topics
        controversial_keywords = [
            'vaccine', 'government', 'conspiracy', 'secret', 'hidden',
            'dangerous', 'fake', 'hoax', 'fraud', 'scam'
        ]
        
        for keyword in controversial_keywords:
            if keyword in sentence_lower:
                score += 0.1
        
        return min(1.0, score)
    
    def _categorize_claim(self, text: str) -> ClaimCategory:
        """Categorize a claim based on its content"""
        text_lower = text.lower()
        
        # Health-related keywords
        if any(word in text_lower for word in ['vaccine', 'medicine', 'doctor', 'health', 'disease', 'cure', 'treatment']):
            return ClaimCategory.HEALTH
        
        # Politics-related keywords
        if any(word in text_lower for word in ['government', 'election', 'politician', 'vote', 'policy', 'minister']):
            return ClaimCategory.POLITICS
        
        # Disaster-related keywords
        if any(word in text_lower for word in ['earthquake', 'flood', 'cyclone', 'disaster', 'emergency', 'crisis']):
            return ClaimCategory.DISASTER
        
        # Technology-related keywords
        if any(word in text_lower for word in ['5g', 'phone', 'internet', 'ai', 'technology', 'digital']):
            return ClaimCategory.TECHNOLOGY
        
        # Environment-related keywords
        if any(word in text_lower for word in ['climate', 'environment', 'pollution', 'global warming', 'weather']):
            return ClaimCategory.ENVIRONMENT
        
        # Social-related keywords
        if any(word in text_lower for word in ['community', 'religion', 'culture', 'tradition', 'society']):
            return ClaimCategory.SOCIAL
        
        return ClaimCategory.OTHER
    
    def _find_sentences_with_entity(self, text: str, entity: str) -> List[str]:
        """Find sentences containing a specific entity"""
        sentences = self._split_into_sentences(text)
        matching_sentences = []
        
        for sentence in sentences:
            if entity.lower() in sentence.lower():
                matching_sentences.append(sentence)
        
        return matching_sentences
    
    def _contains_geographic_claim(self, sentence: str, geo_entity: str) -> bool:
        """Check if sentence makes claims about a geographic entity"""
        sentence_lower = sentence.lower()
        
        # Look for claim patterns involving the geographic entity
        claim_patterns = [
            f"{geo_entity.lower()}.*(?:dangerous|unsafe|attack|threat|crisis)",
            f"(?:in|at).*{geo_entity.lower()}.*(?:happening|occurred|reported|confirmed)",
            f"{geo_entity.lower()}.*(?:government|officials|authorities).*(?:hiding|covering|denying)"
        ]
        
        import re
        for pattern in claim_patterns:
            if re.search(pattern, sentence_lower):
                return True
        
        return False
    
    def _deduplicate_claims(self, claims: List[Claim]) -> List[Claim]:
        """Remove duplicate claims based on text similarity"""
        if not claims:
            return []
        
        unique_claims = []
        
        for claim in claims:
            is_duplicate = False
            
            for existing_claim in unique_claims:
                # Simple similarity check based on text overlap
                similarity = self._calculate_text_similarity(claim.text, existing_claim.text)
                
                if similarity > 0.7:  # Threshold for considering as duplicate
                    is_duplicate = True
                    # Keep the claim with higher confidence
                    if claim.confidence > existing_claim.confidence:
                        unique_claims.remove(existing_claim)
                        unique_claims.append(claim)
                    break
            
            if not is_duplicate:
                unique_claims.append(claim)
        
        return unique_claims
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity based on word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)


class ViralityScorer:
    """
    Calculates virality scores for events based on source credibility,
    engagement metrics, and content characteristics.
    """
    
    def __init__(self):
        self.source_credibility = self._load_source_credibility_scores()
    
    def _load_source_credibility_scores(self) -> Dict[EventSource, float]:
        """Load credibility scores for different event sources"""
        return {
            EventSource.NEWS: 0.7,      # Traditional news sources
            EventSource.TWITTER: 0.4,   # Social media - lower credibility
            EventSource.FACEBOOK: 0.3,  # Social media - lower credibility
            EventSource.RSS: 0.6,       # RSS feeds - moderate credibility
            EventSource.MANUAL: 0.5     # Manual input - neutral
        }
    
    def calculate_virality_score(self, raw_event: RawEvent, text_analysis: TextAnalysisResult, 
                               claims: List[Claim]) -> float:
        """
        Calculate virality score based on multiple factors.
        Higher score indicates higher potential for viral spread.
        """
        try:
            # Base score from source credibility (inverted - less credible sources spread faster)
            base_score = 1.0 - self.source_credibility.get(raw_event.source, 0.5)
            
            # Content factors
            content_score = self._calculate_content_virality(text_analysis, claims)
            
            # Engagement factors (if available)
            engagement_score = self._calculate_engagement_virality(raw_event.engagement_metrics)
            
            # Timing factors
            timing_score = self._calculate_timing_virality(raw_event.timestamp)
            
            # Combine scores with weights
            virality_score = (
                base_score * 0.3 +
                content_score * 0.4 +
                engagement_score * 0.2 +
                timing_score * 0.1
            )
            
            return min(1.0, max(0.0, virality_score))
            
        except Exception as e:
            logger.warning(f"Virality score calculation failed: {e}")
            return 0.5  # Default neutral score
    
    def _calculate_content_virality(self, text_analysis: TextAnalysisResult, claims: List[Claim]) -> float:
        """Calculate virality based on content characteristics"""
        score = 0.0
        
        # Emotional content spreads faster
        sentiment_magnitude = abs(text_analysis.sentiment_score)
        score += sentiment_magnitude * 0.3
        
        # Controversial claims spread faster
        if claims:
            avg_claim_confidence = sum(claim.confidence for claim in claims) / len(claims)
            score += avg_claim_confidence * 0.4
        
        # Certain keywords increase virality
        viral_keywords = [
            'breaking', 'urgent', 'shocking', 'exposed', 'secret', 'hidden',
            'conspiracy', 'scandal', 'leaked', 'exclusive', 'warning', 'alert'
        ]
        
        keyword_count = sum(1 for keyword in viral_keywords if keyword in text_analysis.original_text.lower())
        score += min(0.3, keyword_count * 0.1)
        
        return min(1.0, score)
    
    def _calculate_engagement_virality(self, engagement_metrics: Optional[Dict[str, int]]) -> float:
        """Calculate virality based on engagement metrics"""
        if not engagement_metrics:
            return 0.5  # Neutral score if no metrics available
        
        # Normalize engagement metrics
        likes = engagement_metrics.get('likes', 0)
        shares = engagement_metrics.get('shares', 0)
        comments = engagement_metrics.get('comments', 0)
        
        # Shares are most important for virality
        share_score = min(1.0, shares / 100)  # Normalize assuming 100 shares = max score
        like_score = min(1.0, likes / 1000)   # Normalize assuming 1000 likes = max score
        comment_score = min(1.0, comments / 50)  # Normalize assuming 50 comments = max score
        
        return (share_score * 0.5 + like_score * 0.3 + comment_score * 0.2)
    
    def _calculate_timing_virality(self, timestamp: datetime) -> float:
        """Calculate virality based on timing factors"""
        # Recent content has higher virality potential
        now = datetime.utcnow()
        age_hours = (now - timestamp).total_seconds() / 3600
        
        if age_hours < 1:
            return 1.0  # Very recent
        elif age_hours < 6:
            return 0.8  # Recent
        elif age_hours < 24:
            return 0.6  # Same day
        elif age_hours < 72:
            return 0.4  # Within 3 days
        else:
            return 0.2  # Older content


class EventProcessor:
    """
    Main event processor that orchestrates the entire pipeline:
    NLP analysis -> Claim extraction -> Virality scoring -> Satellite validation
    """
    
    def __init__(self):
        self.claim_extractor = ClaimExtractor()
        self.virality_scorer = ViralityScorer()
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the event processor and all its components"""
        try:
            # Initialize NLP analyzer
            nlp_success = await nlp_analyzer.initialize()
            if not nlp_success:
                logger.error("Failed to initialize NLP analyzer")
                return False
            
            # Initialize database
            db_success = await database.initialize()
            if not db_success:
                logger.error("Failed to initialize database")
                return False
            
            self.initialized = True
            logger.info("Event processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize event processor: {e}")
            return False
    
    async def process_event(self, raw_event: RawEvent) -> Optional[ProcessedEvent]:
        """
        Process a raw event through the complete pipeline.
        Returns a ProcessedEvent ready for storage and visualization.
        """
        if not self.initialized:
            logger.error("Event processor not initialized")
            return None
        
        try:
            logger.debug(f"Processing event from {raw_event.source.value}")
            
            # Step 1: NLP Analysis
            text_analysis = await nlp_analyzer.analyze_text(raw_event.original_text)
            
            # Step 2: Claim Extraction
            claim_result = self.claim_extractor.extract_claims(text_analysis)
            
            # Step 3: Geographic Processing
            region_hint, lat, lon = self._extract_geographic_info(text_analysis, raw_event.metadata)
            
            # Step 4: Virality Scoring
            virality_score = self.virality_scorer.calculate_virality_score(
                raw_event, text_analysis, claim_result.claims
            )
            
            # Step 5: Create ProcessedEvent
            processed_event = ProcessedEvent(
                source=raw_event.source,
                original_text=raw_event.original_text,
                timestamp=raw_event.timestamp,
                lang=text_analysis.language_detection.language,
                region_hint=region_hint,
                lat=lat,
                lon=lon,
                entities=text_analysis.entities.entities,
                virality_score=virality_score,
                satellite=None,  # Will be populated by satellite validation
                claims=claim_result.claims,
                processing_metadata={
                    "nlp_analysis": text_analysis.metadata,
                    "claim_extraction": claim_result.processing_metadata,
                    "virality_factors": {
                        "source_credibility": self.virality_scorer.source_credibility.get(raw_event.source, 0.5),
                        "content_score": virality_score
                    },
                    "processing_time_ms": text_analysis.processing_time_ms
                }
            )
            
            logger.debug(f"Event processed successfully: {processed_event.event_id}")
            return processed_event
            
        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            return None
    
    def _extract_geographic_info(self, text_analysis: TextAnalysisResult, 
                               metadata: Dict[str, Any]) -> Tuple[str, float, float]:
        """
        Extract geographic information from text analysis and metadata.
        Returns (region_hint, latitude, longitude)
        """
        region_hint = ""
        lat, lon = 0.0, 0.0
        
        # Try to get location from metadata first
        if metadata.get('location'):
            location_data = metadata['location']
            if isinstance(location_data, dict):
                lat = location_data.get('lat', 0.0)
                lon = location_data.get('lon', 0.0)
                region_hint = location_data.get('region', '')
        
        # If no metadata location, try to infer from text analysis
        if not region_hint and text_analysis.entities.indian_states:
            # Use the first Indian state found
            region_hint = normalize_state_name(text_analysis.entities.indian_states[0])
            
            # Get approximate coordinates for the state
            lat, lon = self._get_state_coordinates(region_hint)
        
        elif not region_hint and text_analysis.entities.geographic_entities:
            # Try to match geographic entities to Indian states
            for geo_entity in text_analysis.entities.geographic_entities:
                normalized_entity = normalize_state_name(geo_entity)
                if normalized_entity.lower() in INDIAN_STATES:
                    region_hint = normalized_entity
                    lat, lon = self._get_state_coordinates(region_hint)
                    break
        
        return region_hint, lat, lon
    
    def _get_state_coordinates(self, state_name: str) -> Tuple[float, float]:
        """Get approximate coordinates for an Indian state"""
        # Approximate coordinates for Indian state capitals
        state_coordinates = {
            "andhra pradesh": (15.9129, 79.7400),
            "arunachal pradesh": (28.2180, 94.7278),
            "assam": (26.2006, 92.9376),
            "bihar": (25.0961, 85.3131),
            "chhattisgarh": (21.2787, 81.8661),
            "goa": (15.2993, 74.1240),
            "gujarat": (23.0225, 72.5714),
            "haryana": (29.0588, 76.0856),
            "himachal pradesh": (31.1048, 77.1734),
            "jharkhand": (23.6102, 85.2799),
            "karnataka": (15.3173, 75.7139),
            "kerala": (10.8505, 76.2711),
            "madhya pradesh": (22.9734, 78.6569),
            "maharashtra": (19.7515, 75.7139),
            "manipur": (24.6637, 93.9063),
            "meghalaya": (25.4670, 91.3662),
            "mizoram": (23.1645, 92.9376),
            "nagaland": (26.1584, 94.5624),
            "odisha": (20.9517, 85.0985),
            "punjab": (31.1471, 75.3412),
            "rajasthan": (27.0238, 74.2179),
            "sikkim": (27.5330, 88.5122),
            "tamil nadu": (11.1271, 78.6569),
            "telangana": (18.1124, 79.0193),
            "tripura": (23.9408, 91.9882),
            "uttar pradesh": (26.8467, 80.9462),
            "uttarakhand": (30.0668, 79.0193),
            "west bengal": (22.9868, 87.8550),
            "delhi": (28.7041, 77.1025),
            "jammu and kashmir": (34.0837, 74.7973),
            "ladakh": (34.1526, 77.5771)
        }
        
        return state_coordinates.get(state_name.lower(), (0.0, 0.0))


# Global processor instance
event_processor = EventProcessor()