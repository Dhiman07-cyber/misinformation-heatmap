"""
Unit tests for NLP pipeline components including IndicBERT analyzer,
claim extraction, and event processing functionality.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Set environment for testing
os.environ["MODE"] = "local"

# Import our NLP components
from nlp_analyzer import (
    IndicBERTAnalyzer, LanguageDetectionResult, EntityExtractionResult, 
    TextAnalysisResult, nlp_analyzer
)
from processor import (
    ClaimExtractor, ViralityScorer, EventProcessor, RawEvent,
    ClaimExtractionResult, event_processor
)
from models import (
    EventSource, LanguageCode, ClaimCategory, Claim, ProcessedEvent
)


class TestIndicBERTAnalyzer:
    """Test cases for IndicBERT text analyzer"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.analyzer = IndicBERTAnalyzer()
    
    def test_language_detection_english(self):
        """Test language detection for English text"""
        text = "This is a breaking news story from Mumbai about vaccine safety concerns."
        
        result = self.analyzer.detect_language(text)
        
        assert isinstance(result, LanguageDetectionResult)
        assert result.language == LanguageCode.ENGLISH
        assert result.is_supported == True
        assert 0.0 <= result.confidence <= 1.0
    
    def test_language_detection_hindi(self):
        """Test language detection for Hindi text"""
        text = "यह मुंबई से एक महत्वपूर्ण समाचार है वैक्सीन के बारे में।"
        
        result = self.analyzer.detect_language(text)
        
        assert isinstance(result, LanguageDetectionResult)
        # Note: Actual detection may vary, but should handle gracefully
        assert result.language in [LanguageCode.HINDI, LanguageCode.ENGLISH]
        assert result.is_supported == True
    
    def test_language_detection_short_text(self):
        """Test language detection for very short text"""
        text = "Hi"
        
        result = self.analyzer.detect_language(text)
        
        assert result.language == LanguageCode.ENGLISH  # Default for short text
        assert result.confidence == 0.5
    
    def test_text_preprocessing(self):
        """Test text preprocessing functionality"""
        text = "Breaking: COVID vaccine causes autism!!! @doctor #health http://fake-news.com"
        
        cleaned = self.analyzer.preprocess_text(text, LanguageCode.ENGLISH)
        
        assert "[URL]" in cleaned
        assert "[MENTION]" in cleaned
        assert "health" in cleaned  # Hashtag content preserved
        assert len(cleaned) <= self.analyzer.config["max_text_length"]
    
    def test_entity_extraction_patterns(self):
        """Test pattern-based entity extraction for Indian locations"""
        text = "There was a major incident in Mumbai, Maharashtra. Delhi authorities are investigating."
        
        result = self.analyzer.extract_entities(text, LanguageCode.ENGLISH)
        
        assert isinstance(result, EntityExtractionResult)
        assert any("mumbai" in entity.lower() for entity in result.geographic_entities)
        assert any("maharashtra" in entity.lower() for entity in result.geographic_entities)
        assert any("delhi" in entity.lower() for entity in result.geographic_entities)
    
    def test_indian_geographic_entity_validation(self):
        """Test validation of Indian geographic entities"""
        # Valid Indian entities
        assert self.analyzer._is_indian_geographic_entity("Mumbai") == True
        assert self.analyzer._is_indian_geographic_entity("maharashtra") == True
        assert self.analyzer._is_indian_geographic_entity("Delhi") == True
        
        # Invalid entities
        assert self.analyzer._is_indian_geographic_entity("New York") == False
        assert self.analyzer._is_indian_geographic_entity("London") == False
    
    def test_keyword_extraction(self):
        """Test keyword extraction from text"""
        text = "Breaking news: Dangerous vaccine side effects reported in Mumbai hospitals. Government hiding truth."
        
        keywords = self.analyzer.extract_keywords(text, LanguageCode.ENGLISH, top_k=5)
        
        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        assert any("vaccine" in keyword.lower() for keyword in keywords)
        assert any("dangerous" in keyword.lower() for keyword in keywords)
    
    def test_sentiment_calculation(self):
        """Test sentiment score calculation"""
        positive_text = "Great news! Amazing vaccine success story brings hope and joy."
        negative_text = "Terrible disaster! Dangerous vaccine causes death and destruction."
        neutral_text = "The vaccine was administered at the hospital."
        
        positive_score = self.analyzer.calculate_sentiment_score(positive_text)
        negative_score = self.analyzer.calculate_sentiment_score(negative_text)
        neutral_score = self.analyzer.calculate_sentiment_score(neutral_text)
        
        assert positive_score > 0
        assert negative_score < 0
        assert abs(neutral_score) < abs(positive_score)
        assert -1.0 <= positive_score <= 1.0
        assert -1.0 <= negative_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_text_analysis_integration(self):
        """Test complete text analysis pipeline"""
        text = "Breaking: Fake vaccine distributed in Mumbai causes serious side effects. Maharashtra government denies reports."
        
        # Mock the model components to avoid loading actual models in tests
        with patch.object(self.analyzer, 'generate_embeddings', return_value=None):
            result = await self.analyzer.analyze_text(text)
        
        assert isinstance(result, TextAnalysisResult)
        assert result.original_text == text
        assert len(result.cleaned_text) > 0
        assert result.language_detection.language in [LanguageCode.ENGLISH, LanguageCode.HINDI]
        assert isinstance(result.entities, EntityExtractionResult)
        assert isinstance(result.keywords, list)
        assert -1.0 <= result.sentiment_score <= 1.0
        assert result.processing_time_ms >= 0


class TestClaimExtractor:
    """Test cases for claim extraction functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.extractor = ClaimExtractor()
    
    def test_misinformation_pattern_detection(self):
        """Test detection of misinformation patterns"""
        # Create mock text analysis result
        text_analysis = Mock(spec=TextAnalysisResult)
        text_analysis.cleaned_text = "COVID vaccine causes autism and is dangerous for children"
        text_analysis.language_detection = Mock()
        text_analysis.language_detection.language = LanguageCode.ENGLISH
        text_analysis.entities = Mock()
        text_analysis.entities.entities = ["vaccine", "children"]
        text_analysis.entities.geographic_entities = []
        text_analysis.sentiment_score = -0.5
        
        result = self.extractor.extract_claims(text_analysis)
        
        assert isinstance(result, ClaimExtractionResult)
        assert len(result.claims) > 0
        assert any(claim.category == ClaimCategory.HEALTH for claim in result.claims)
        assert result.confidence_score > 0
    
    def test_sentence_based_claim_extraction(self):
        """Test extraction of claims from individual sentences"""
        text = "The vaccine is proven to be dangerous. Government officials are hiding the truth from public."
        
        sentences = self.extractor._split_into_sentences(text)
        assert len(sentences) == 2
        
        # Test claim scoring
        score1 = self.extractor._calculate_sentence_claim_score(sentences[0])
        score2 = self.extractor._calculate_sentence_claim_score(sentences[1])
        
        assert score1 > 0.5  # Should be detected as a claim
        assert score2 > 0.5  # Should be detected as a claim
    
    def test_claim_categorization(self):
        """Test automatic categorization of claims"""
        health_text = "Vaccine causes serious side effects and health problems"
        politics_text = "Government is rigging the election results"
        disaster_text = "Earthquake was artificially created by government"
        
        assert self.extractor._categorize_claim(health_text) == ClaimCategory.HEALTH
        assert self.extractor._categorize_claim(politics_text) == ClaimCategory.POLITICS
        assert self.extractor._categorize_claim(disaster_text) == ClaimCategory.DISASTER
    
    def test_geographic_claim_detection(self):
        """Test detection of claims about geographic entities"""
        sentence = "Mumbai is under attack by dangerous vaccine side effects"
        
        contains_claim = self.extractor._contains_geographic_claim(sentence, "Mumbai")
        assert contains_claim == True
        
        normal_sentence = "Mumbai is a beautiful city in Maharashtra"
        contains_normal = self.extractor._contains_geographic_claim(normal_sentence, "Mumbai")
        assert contains_normal == False
    
    def test_claim_deduplication(self):
        """Test removal of duplicate claims"""
        claim1 = Claim(text="Vaccine is dangerous for health", confidence=0.8)
        claim2 = Claim(text="Vaccines are dangerous for human health", confidence=0.7)  # Similar
        claim3 = Claim(text="Government is hiding election fraud", confidence=0.9)  # Different
        
        claims = [claim1, claim2, claim3]
        unique_claims = self.extractor._deduplicate_claims(claims)
        
        assert len(unique_claims) == 2  # Should remove one duplicate
        # Should keep the higher confidence claim
        health_claims = [c for c in unique_claims if "vaccine" in c.text.lower()]
        assert len(health_claims) == 1
        assert health_claims[0].confidence == 0.8  # Higher confidence kept
    
    def test_text_similarity_calculation(self):
        """Test text similarity calculation for deduplication"""
        text1 = "Vaccine is dangerous for health"
        text2 = "Vaccines are dangerous for human health"
        text3 = "Government is hiding the truth"
        
        similarity_high = self.extractor._calculate_text_similarity(text1, text2)
        similarity_low = self.extractor._calculate_text_similarity(text1, text3)
        
        assert similarity_high > similarity_low
        assert 0.0 <= similarity_high <= 1.0
        assert 0.0 <= similarity_low <= 1.0


class TestViralityScorer:
    """Test cases for virality scoring functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.scorer = ViralityScorer()
    
    def test_source_credibility_scores(self):
        """Test that source credibility scores are properly configured"""
        assert EventSource.NEWS in self.scorer.source_credibility
        assert EventSource.TWITTER in self.scorer.source_credibility
        assert 0.0 <= self.scorer.source_credibility[EventSource.NEWS] <= 1.0
        assert 0.0 <= self.scorer.source_credibility[EventSource.TWITTER] <= 1.0
    
    def test_content_virality_calculation(self):
        """Test virality calculation based on content characteristics"""
        # Create mock text analysis with high emotional content
        text_analysis = Mock(spec=TextAnalysisResult)
        text_analysis.sentiment_score = -0.8  # Highly negative
        text_analysis.original_text = "BREAKING: URGENT WARNING about dangerous vaccine conspiracy!"
        
        # Create mock claims
        claims = [
            Claim(text="Vaccine conspiracy", confidence=0.9),
            Claim(text="Government cover-up", confidence=0.8)
        ]
        
        content_score = self.scorer._calculate_content_virality(text_analysis, claims)
        
        assert 0.0 <= content_score <= 1.0
        assert content_score > 0.5  # Should be high due to emotional content and viral keywords
    
    def test_engagement_virality_calculation(self):
        """Test virality calculation based on engagement metrics"""
        high_engagement = {"likes": 1000, "shares": 200, "comments": 100}
        low_engagement = {"likes": 10, "shares": 1, "comments": 2}
        no_engagement = None
        
        high_score = self.scorer._calculate_engagement_virality(high_engagement)
        low_score = self.scorer._calculate_engagement_virality(low_engagement)
        neutral_score = self.scorer._calculate_engagement_virality(no_engagement)
        
        assert high_score > low_score
        assert neutral_score == 0.5
        assert 0.0 <= high_score <= 1.0
        assert 0.0 <= low_score <= 1.0
    
    def test_timing_virality_calculation(self):
        """Test virality calculation based on content timing"""
        now = datetime.utcnow()
        recent = now - timedelta(minutes=30)
        old = now - timedelta(days=5)
        
        recent_score = self.scorer._calculate_timing_virality(recent)
        old_score = self.scorer._calculate_timing_virality(old)
        
        assert recent_score > old_score
        assert 0.0 <= recent_score <= 1.0
        assert 0.0 <= old_score <= 1.0
    
    def test_complete_virality_scoring(self):
        """Test complete virality score calculation"""
        # Create test raw event
        raw_event = RawEvent(
            source=EventSource.TWITTER,  # Lower credibility source
            original_text="URGENT: Vaccine conspiracy exposed! Government hiding truth!",
            timestamp=datetime.utcnow(),
            metadata={},
            engagement_metrics={"likes": 500, "shares": 100, "comments": 50}
        )
        
        # Create mock text analysis
        text_analysis = Mock(spec=TextAnalysisResult)
        text_analysis.sentiment_score = -0.7
        text_analysis.original_text = raw_event.original_text
        
        # Create mock claims
        claims = [Claim(text="Vaccine conspiracy", confidence=0.9)]
        
        virality_score = self.scorer.calculate_virality_score(raw_event, text_analysis, claims)
        
        assert 0.0 <= virality_score <= 1.0
        assert virality_score > 0.3  # Should be relatively high due to factors


class TestEventProcessor:
    """Test cases for complete event processing pipeline"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.processor = EventProcessor()
    
    def test_geographic_info_extraction(self):
        """Test extraction of geographic information from text analysis"""
        # Create mock text analysis with Indian geographic entities
        text_analysis = Mock(spec=TextAnalysisResult)
        text_analysis.entities = Mock()
        text_analysis.entities.indian_states = ["Maharashtra"]
        text_analysis.entities.geographic_entities = ["Mumbai", "Maharashtra"]
        
        metadata = {}
        
        region_hint, lat, lon = self.processor._extract_geographic_info(text_analysis, metadata)
        
        assert region_hint == "Maharashtra"
        assert lat != 0.0 or lon != 0.0  # Should have coordinates
    
    def test_geographic_info_from_metadata(self):
        """Test extraction of geographic information from metadata"""
        text_analysis = Mock(spec=TextAnalysisResult)
        text_analysis.entities = Mock()
        text_analysis.entities.indian_states = []
        text_analysis.entities.geographic_entities = []
        
        metadata = {
            "location": {
                "lat": 19.0760,
                "lon": 72.8777,
                "region": "Mumbai"
            }
        }
        
        region_hint, lat, lon = self.processor._extract_geographic_info(text_analysis, metadata)
        
        assert region_hint == "Mumbai"
        assert lat == 19.0760
        assert lon == 72.8777
    
    def test_state_coordinates_lookup(self):
        """Test lookup of coordinates for Indian states"""
        maharashtra_coords = self.processor._get_state_coordinates("Maharashtra")
        delhi_coords = self.processor._get_state_coordinates("Delhi")
        invalid_coords = self.processor._get_state_coordinates("InvalidState")
        
        assert maharashtra_coords != (0.0, 0.0)
        assert delhi_coords != (0.0, 0.0)
        assert invalid_coords == (0.0, 0.0)
    
    @pytest.mark.asyncio
    async def test_event_processing_pipeline(self):
        """Test complete event processing pipeline"""
        # Create test raw event
        raw_event = RawEvent(
            source=EventSource.NEWS,
            original_text="Breaking news from Mumbai: Vaccine side effects reported in Maharashtra hospitals.",
            timestamp=datetime.utcnow(),
            metadata={"source_url": "https://example.com/news"}
        )
        
        # Mock the NLP analyzer to avoid loading actual models
        with patch('processor.nlp_analyzer') as mock_nlp:
            # Setup mock text analysis result
            mock_analysis = Mock(spec=TextAnalysisResult)
            mock_analysis.language_detection = Mock()
            mock_analysis.language_detection.language = LanguageCode.ENGLISH
            mock_analysis.entities = Mock()
            mock_analysis.entities.entities = ["vaccine", "hospitals"]
            mock_analysis.entities.geographic_entities = ["Mumbai", "Maharashtra"]
            mock_analysis.entities.indian_states = ["Maharashtra"]
            mock_analysis.sentiment_score = -0.3
            mock_analysis.processing_time_ms = 150
            mock_analysis.metadata = {"test": True}
            
            mock_nlp.analyze_text.return_value = mock_analysis
            
            # Process the event
            processed_event = await self.processor.process_event(raw_event)
        
        assert processed_event is not None
        assert isinstance(processed_event, ProcessedEvent)
        assert processed_event.source == EventSource.NEWS
        assert processed_event.original_text == raw_event.original_text
        assert processed_event.region_hint == "Maharashtra"
        assert 0.0 <= processed_event.virality_score <= 1.0
        assert processed_event.event_id is not None


class TestNLPIntegration:
    """Integration tests for NLP pipeline components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self):
        """Test end-to-end processing without actual model loading"""
        text = "Urgent warning: Dangerous vaccine distributed in Mumbai causes serious health problems. Maharashtra government denies all reports."
        
        # Test individual components
        analyzer = IndicBERTAnalyzer()
        extractor = ClaimExtractor()
        scorer = ViralityScorer()
        
        # Test language detection
        lang_result = analyzer.detect_language(text)
        assert lang_result.language == LanguageCode.ENGLISH
        
        # Test text preprocessing
        cleaned_text = analyzer.preprocess_text(text, lang_result.language)
        assert len(cleaned_text) > 0
        
        # Test entity extraction
        entities = analyzer.extract_entities(cleaned_text, lang_result.language)
        assert len(entities.geographic_entities) > 0
        
        # Test keyword extraction
        keywords = analyzer.extract_keywords(cleaned_text, lang_result.language)
        assert len(keywords) > 0
        
        # Test sentiment analysis
        sentiment = analyzer.calculate_sentiment_score(cleaned_text)
        assert -1.0 <= sentiment <= 1.0
    
    def test_error_handling(self):
        """Test error handling in NLP components"""
        analyzer = IndicBERTAnalyzer()
        
        # Test with empty text
        result = analyzer.detect_language("")
        assert result.language == LanguageCode.ENGLISH  # Default fallback
        
        # Test with very long text
        long_text = "word " * 1000
        cleaned = analyzer.preprocess_text(long_text, LanguageCode.ENGLISH)
        assert len(cleaned) <= analyzer.config["max_text_length"]
        
        # Test with special characters
        special_text = "!@#$%^&*()_+{}|:<>?[]\\;'\",./"
        entities = analyzer.extract_entities(special_text, LanguageCode.ENGLISH)
        assert isinstance(entities, EntityExtractionResult)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])