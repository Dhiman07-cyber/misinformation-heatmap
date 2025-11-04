#!/usr/bin/env python3
"""
Data validation utilities for ensuring quality of ingested events.
Implements multi-layer filtering and validation logic.
"""

import logging
import re
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

from .base_connector import RawEvent

logger = logging.getLogger(__name__)


class DataValidator:
    """Multi-layer data validation for raw events."""
    
    def __init__(self, config: Dict = None):
        """Initialize validator with configuration.
        
        Args:
            config: Validation configuration dictionary
        """
        self.config = config or {}
        
        # Content quality thresholds
        self.min_content_length = self.config.get('min_content_length', 10)
        self.max_content_length = self.config.get('max_content_length', 50000)
        self.min_word_count = self.config.get('min_word_count', 3)
        
        # Language settings
        self.allowed_languages = set(self.config.get('allowed_languages', [
            'en', 'hi', 'bn', 'te', 'ta', 'mr', 'gu', 'kn', 'ml', 'or', 'pa', 'as'
        ]))
        
        # Geographic relevance
        self.require_india_relevance = self.config.get('require_india_relevance', True)
        
        # Spam and quality filters
        self.spam_keywords = set(self.config.get('spam_keywords', [
            'buy now', 'click here', 'limited offer', 'act now', 'free money',
            'earn money', 'work from home', 'get rich quick', 'miracle cure',
            'lose weight fast', 'enlargement', 'viagra', 'casino', 'lottery'
        ]))
        
        # Indian context keywords for relevance checking
        self.india_keywords = set([
            'india', 'indian', 'bharat', 'bharatiya', 'delhi', 'mumbai', 'bangalore',
            'chennai', 'kolkata', 'hyderabad', 'pune', 'ahmedabad', 'surat', 'jaipur',
            'lucknow', 'kanpur', 'nagpur', 'indore', 'bhopal', 'visakhapatnam', 'patna',
            'vadodara', 'ludhiana', 'agra', 'nashik', 'faridabad', 'meerut', 'rajkot',
            'kalyan', 'vasai', 'varanasi', 'srinagar', 'aurangabad', 'dhanbad', 'amritsar',
            'navi mumbai', 'allahabad', 'ranchi', 'howrah', 'coimbatore', 'jabalpur',
            'gwalior', 'vijayawada', 'jodhpur', 'madurai', 'raipur', 'kota', 'guwahati',
            'chandigarh', 'solapur', 'hubli', 'tiruchirappalli', 'bareilly', 'mysore',
            'tiruppur', 'gurgaon', 'aligarh', 'jalandhar', 'bhubaneswar', 'salem',
            'warangal', 'mira', 'bhiwandi', 'thiruvananthapuram', 'bhavnagar', 'dehradun',
            'durgapur', 'asansol', 'nanded', 'kolhapur', 'ajmer', 'gulbarga', 'jamnagar',
            'ujjain', 'loni', 'siliguri', 'jhansi', 'ulhasnagar', 'nellore', 'jammu',
            'sangli', 'belgaum', 'mangalore', 'ambattur', 'tirunelveli', 'malegaon',
            'gaya', 'jalgaon', 'udaipur', 'maheshtala'
        ])
        
        # Indian states and union territories
        self.indian_states = set([
            'andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh',
            'goa', 'gujarat', 'haryana', 'himachal pradesh', 'jharkhand', 'karnataka',
            'kerala', 'madhya pradesh', 'maharashtra', 'manipur', 'meghalaya', 'mizoram',
            'nagaland', 'odisha', 'punjab', 'rajasthan', 'sikkim', 'tamil nadu',
            'telangana', 'tripura', 'uttar pradesh', 'uttarakhand', 'west bengal',
            'andaman and nicobar islands', 'chandigarh', 'dadra and nagar haveli',
            'daman and diu', 'delhi', 'lakshadweep', 'puducherry', 'jammu and kashmir',
            'ladakh'
        ])
        
        # Statistics
        self.stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'failure_reasons': {}
        }
    
    def validate_event(self, event: RawEvent) -> tuple[bool, Optional[str]]:
        """Validate a raw event through multiple layers.
        
        Args:
            event: RawEvent to validate
            
        Returns:
            Tuple of (is_valid, failure_reason)
        """
        self.stats['total_validated'] += 1
        
        try:
            # Layer 1: Basic validation
            is_valid, reason = self._validate_basic(event)
            if not is_valid:
                self._record_failure(reason)
                return False, reason
            
            # Layer 2: Content quality
            is_valid, reason = self._validate_content_quality(event)
            if not is_valid:
                self._record_failure(reason)
                return False, reason
            
            # Layer 3: Language validation
            is_valid, reason = self._validate_language(event)
            if not is_valid:
                self._record_failure(reason)
                return False, reason
            
            # Layer 4: Geographic relevance
            if self.require_india_relevance:
                is_valid, reason = self._validate_india_relevance(event)
                if not is_valid:
                    self._record_failure(reason)
                    return False, reason
            
            # Layer 5: Spam and quality filtering
            is_valid, reason = self._validate_not_spam(event)
            if not is_valid:
                self._record_failure(reason)
                return False, reason
            
            # All validations passed
            self.stats['passed'] += 1
            return True, None
            
        except Exception as e:
            logger.error(f"Validation error for event {event.event_id}: {e}")
            self._record_failure(f"validation_error: {str(e)}")
            return False, f"validation_error: {str(e)}"
    
    def _validate_basic(self, event: RawEvent) -> tuple[bool, Optional[str]]:
        """Basic validation checks."""
        
        # Check required fields
        if not event.content:
            return False, "empty_content"
        
        if not event.source_id:
            return False, "missing_source_id"
        
        if not event.timestamp:
            return False, "missing_timestamp"
        
        # Check content length
        content_length = len(event.content)
        if content_length < self.min_content_length:
            return False, f"content_too_short: {content_length} < {self.min_content_length}"
        
        if content_length > self.max_content_length:
            return False, f"content_too_long: {content_length} > {self.max_content_length}"
        
        # Check word count
        word_count = len(event.content.split())
        if word_count < self.min_word_count:
            return False, f"insufficient_words: {word_count} < {self.min_word_count}"
        
        # Check timestamp is reasonable (not too old or in future)
        now = datetime.now(event.timestamp.tzinfo or None)
        age = now - event.timestamp
        
        if age.days > 30:  # Older than 30 days
            return False, f"content_too_old: {age.days} days"
        
        if age.total_seconds() < -3600:  # More than 1 hour in future
            return False, "content_from_future"
        
        return True, None
    
    def _validate_content_quality(self, event: RawEvent) -> tuple[bool, Optional[str]]:
        """Validate content quality and structure."""
        
        content = event.content.lower()
        
        # Check for excessive repetition
        words = content.split()
        if len(words) > 10:
            unique_words = set(words)
            repetition_ratio = len(unique_words) / len(words)
            if repetition_ratio < 0.3:  # Less than 30% unique words
                return False, f"excessive_repetition: {repetition_ratio:.2f}"
        
        # Check for excessive capitalization
        if len(event.content) > 50:
            caps_ratio = sum(1 for c in event.content if c.isupper()) / len(event.content)
            if caps_ratio > 0.5:  # More than 50% uppercase
                return False, f"excessive_caps: {caps_ratio:.2f}"
        
        # Check for excessive punctuation
        punct_count = sum(1 for c in event.content if c in '!?.,;:')
        if len(words) > 0:
            punct_ratio = punct_count / len(words)
            if punct_ratio > 0.3:  # More than 30% punctuation to words ratio
                return False, f"excessive_punctuation: {punct_ratio:.2f}"
        
        # Check for minimum sentence structure
        sentences = re.split(r'[.!?]+', event.content)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if len(valid_sentences) == 0 and len(words) > 20:
            return False, "no_sentence_structure"
        
        return True, None
    
    def _validate_language(self, event: RawEvent) -> tuple[bool, Optional[str]]:
        """Validate language is in allowed set."""
        
        if not self.allowed_languages:
            return True, None  # No language restrictions
        
        # Use detected language or try to detect
        language = event.language
        if not language:
            language = self._detect_language_simple(event.content)
        
        if language and language not in self.allowed_languages:
            return False, f"unsupported_language: {language}"
        
        return True, None
    
    def _validate_india_relevance(self, event: RawEvent) -> tuple[bool, Optional[str]]:
        """Validate content is relevant to India."""
        
        content_lower = event.content.lower()
        title_lower = (event.title or "").lower()
        
        # Check for India-related keywords
        text_to_check = f"{content_lower} {title_lower}"
        
        # Direct keyword matching
        for keyword in self.india_keywords:
            if keyword in text_to_check:
                return True, None
        
        # Check for Indian states
        for state in self.indian_states:
            if state in text_to_check:
                return True, None
        
        # Check location hint
        if event.location_hint:
            location_lower = event.location_hint.lower()
            if any(keyword in location_lower for keyword in self.india_keywords):
                return True, None
            if any(state in location_lower for state in self.indian_states):
                return True, None
        
        # Check metadata for India relevance
        if event.metadata:
            metadata_str = str(event.metadata).lower()
            if any(keyword in metadata_str for keyword in self.india_keywords):
                return True, None
        
        return False, "not_india_relevant"
    
    def _validate_not_spam(self, event: RawEvent) -> tuple[bool, Optional[str]]:
        """Validate content is not spam or low quality."""
        
        content_lower = event.content.lower()
        
        # Check for spam keywords
        for spam_keyword in self.spam_keywords:
            if spam_keyword in content_lower:
                return False, f"spam_keyword: {spam_keyword}"
        
        # Check for excessive URLs
        url_count = len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', event.content))
        word_count = len(event.content.split())
        if word_count > 0 and url_count / word_count > 0.2:  # More than 20% URLs
            return False, f"excessive_urls: {url_count}/{word_count}"
        
        # Check for excessive numbers (might indicate spam/ads)
        number_count = len(re.findall(r'\b\d+\b', event.content))
        if word_count > 0 and number_count / word_count > 0.3:  # More than 30% numbers
            return False, f"excessive_numbers: {number_count}/{word_count}"
        
        # Check for promotional language patterns
        promo_patterns = [
            r'\b(call|contact|visit)\s+(?:us\s+)?(?:at\s+)?\+?\d{10,}',  # Phone numbers
            r'\b(?:only|just)\s+(?:rs\.?|₹)\s*\d+',  # Price mentions
            r'\b(?:free|discount|offer|sale)\b.*\b(?:today|now|limited)\b',  # Promotional offers
        ]
        
        for pattern in promo_patterns:
            if re.search(pattern, content_lower):
                return False, f"promotional_content: {pattern}"
        
        return True, None
    
    def _detect_language_simple(self, content: str) -> Optional[str]:
        """Simple language detection based on script."""
        
        if not content:
            return None
        
        # Count characters by script
        latin_count = sum(1 for c in content if ord(c) < 256 and c.isalpha())
        devanagari_count = sum(1 for c in content if 0x0900 <= ord(c) <= 0x097F)
        bengali_count = sum(1 for c in content if 0x0980 <= ord(c) <= 0x09FF)
        tamil_count = sum(1 for c in content if 0x0B80 <= ord(c) <= 0x0BFF)
        telugu_count = sum(1 for c in content if 0x0C00 <= ord(c) <= 0x0C7F)
        gujarati_count = sum(1 for c in content if 0x0A80 <= ord(c) <= 0x0AFF)
        
        total_alpha = sum([latin_count, devanagari_count, bengali_count, tamil_count, telugu_count, gujarati_count])
        
        if total_alpha == 0:
            return None
        
        # Determine dominant script
        if latin_count / total_alpha > 0.7:
            return 'en'
        elif devanagari_count / total_alpha > 0.5:
            return 'hi'  # Could also be Marathi, but Hindi is more common
        elif bengali_count / total_alpha > 0.5:
            return 'bn'
        elif tamil_count / total_alpha > 0.5:
            return 'ta'
        elif telugu_count / total_alpha > 0.5:
            return 'te'
        elif gujarati_count / total_alpha > 0.5:
            return 'gu'
        
        return 'en'  # Default to English
    
    def _record_failure(self, reason: str):
        """Record validation failure statistics."""
        self.stats['failed'] += 1
        if reason not in self.stats['failure_reasons']:
            self.stats['failure_reasons'][reason] = 0
        self.stats['failure_reasons'][reason] += 1
    
    def get_stats(self) -> Dict:
        """Get validation statistics."""
        stats = self.stats.copy()
        if stats['total_validated'] > 0:
            stats['pass_rate'] = stats['passed'] / stats['total_validated']
            stats['fail_rate'] = stats['failed'] / stats['total_validated']
        else:
            stats['pass_rate'] = 0.0
            stats['fail_rate'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset validation statistics."""
        self.stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'failure_reasons': {}
        }