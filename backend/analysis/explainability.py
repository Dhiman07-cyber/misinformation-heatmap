#!/usr/bin/env python3
"""
Explainability Engine for Misinformation Detection
Provides interpretable explanations for why content is classified as fake/real.
"""

import re
import logging
from typing import Dict, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class ExplainabilityEngine:
    """
    Generate human-readable explanations for misinformation predictions
    """
    
    def __init__(self):
        # Sensational keywords that trigger fake news alerts
        self.sensational_keywords = [
            'breaking', 'urgent', 'shocking', 'exclusive', 'exposed', 'revealed',
            'secret', 'hidden', 'conspiracy', 'cover-up', 'scandal', 'bombshell',
            'viral', 'must see', 'unbelievable', 'incredible'
        ]
        
        # Emotional manipulation words
        self.emotional_keywords = [
            'outraged', 'furious', 'devastated', 'terrified', 'shocked',
            'disgusted', 'betrayed', 'angry', 'hate'
        ]
        
        # Clickbait patterns
        self.clickbait_patterns = [
            r'you (won\'t|will not) believe',
            r'\d+ (things|ways|reasons|facts)',
            r'this will shock',
            r'number \d+ will',
            r'what happens next'
        ]
        
        # Credible attribution patterns
        self.attribution_patterns = [
            'according to', 'sources say', 'officials confirm', 'study shows',
            'research indicates', 'data reveals', 'experts believe', 'report states',
            'ministry announced', 'government stated'
        ]
    
    def explain_prediction(self, text: str, prediction_result: Dict) -> Dict:
        """
        Generate comprehensive explanation for a prediction
        
        Args:
            text: The article text
            prediction_result: Result from FakeNewsDetector
        
        Returns:
            Dictionary with explanation details
        """
        
        # Extract highlighted snippets
        highlighted = self.extract_highlighted_snippets(text, prediction_result)
        
        # Generate reason summary
        reasons = self.generate_reasons(text, prediction_result)
        
        # Get flagged keywords
        flagged_keywords = self.get_flagged_keywords(text)
        
        # Calculate explanation confidence
        explanation_confidence = self._calculate_explanation_confidence(
            reasons, flagged_keywords
        )
        
        return {
            'highlighted_snippets': highlighted,
            'reasons': reasons,
            'flagged_keywords': flagged_keywords,
            'explanation_confidence': explanation_confidence,
            'summary': self._generate_summary(prediction_result, reasons)
        }
    
    def extract_highlighted_snippets(self, text: str, prediction_result: Dict) -> List[Dict]:
        """
        Extract and highlight text snippets that contributed to the prediction
        """
        snippets = []
        sentences = self._split_into_sentences(text)
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            
            # Check for sensational language
            sensational_found = [
                keyword for keyword in self.sensational_keywords 
                if keyword in sentence_lower
            ]
            
            # Check for emotional manipulation
            emotional_found = [
                keyword for keyword in self.emotional_keywords
                if keyword in sentence_lower
            ]
            
            # Check for clickbait patterns
            clickbait_found = any(
                re.search(pattern, sentence_lower)
                for pattern in self.clickbait_patterns
            )
            
            # Check for lack of attribution
            has_attribution = any(
                pattern in sentence_lower
                for pattern in self.attribution_patterns
            )
            
            # Calculate sentence risk score
            risk_score = 0
            reasons = []
            
            if sensational_found:
                risk_score += 0.3
                reasons.append(f"Sensational language: {', '.join(sensational_found)}")
            
            if emotional_found:
                risk_score += 0.3
                reasons.append(f"Emotional manipulation: {', '.join(emotional_found)}")
            
            if clickbait_found:
                risk_score += 0.2
                reasons.append("Clickbait pattern detected")
            
            if not has_attribution and len(sentence.split()) > 10:
                risk_score += 0.2
                reasons.append("Lacks source attribution")
            
            # Only include high-risk sentences
            if risk_score >= 0.3:
                snippets.append({
                    'sentence': sentence,
                    'position': i,
                    'risk_score': min(risk_score, 1.0),
                    'reasons': reasons
                })
        
        # Sort by risk score and return top 5
        snippets.sort(key=lambda x: x['risk_score'], reverse=True)
        return snippets[:5]
    
    def generate_reasons(self, text: str, prediction_result: Dict) -> List[str]:
        """Generate list of reasons for the classification"""
        
        reasons = []
        text_lower = text.lower()
        
        # Check components from prediction
        components = prediction_result.get('components', {})
        
        # ML Classification reason
        ml_result = components.get('ml_classification', {})
        if ml_result.get('fake_probability', 0) > 0.6:
            reasons.append(f"ML model confidence: {ml_result.get('fake_probability', 0):.2%} fake probability")
        
        # Linguistic analysis
        linguistic = components.get('linguistic_analysis', {})
        if linguistic.get('sensational_words', 0) > 2:
            reasons.append(f"Contains {linguistic.get('sensational_words')} sensational words")
        
        if linguistic.get('emotional_words', 0) > 1:
            reasons.append(f"Uses {linguistic.get('emotional_words')} emotional manipulation words")
        
        if linguistic.get('clickbait_patterns', 0) > 0:
            reasons.append("Contains clickbait patterns")
        
        # Source credibility
        source_cred = components.get('source_credibility', {})
        if source_cred.get('credibility_score', 0.5) < 0.4:
            reasons.append(f"Low source credibility ({source_cred.get('source_type', 'unknown')} source)")
        
        # Fact checking
        fact_check = components.get('fact_checking', {})
        if fact_check.get('checked') and fact_check.get('verdict') == 'false':
            reasons.append(f"Debunked by {fact_check.get('source', 'fact-checkers')}")
        
        # Satellite verification
        satellite = components.get('satellite_verification')
        if satellite and not satellite.get('verified'):
            reasons.append("Location claim could not be verified")
        
        # Cross-reference
        cross_ref = components.get('cross_reference_score', 0.5)
        if cross_ref < 0.4:
            reasons.append("Limited corroboration from other sources")
        
        # Add general linguistic flags
        if not any(pattern in text_lower for pattern in self.attribution_patterns):
            reasons.append("Lacks proper source attribution")
        
        if text.count('!') > 3:
            reasons.append("Excessive use of exclamation marks")
        
        # Limit to top 8 reasons
        return reasons[:8]
    
    def get_flagged_keywords(self, text: str) -> Dict[str, List[str]]:
        """Get all flagged keywords by category"""
        
        text_lower = text.lower()
        
        flagged = {
            'sensational': [
                word for word in self.sensational_keywords 
                if word in text_lower
            ],
            'emotional': [
                word for word in self.emotional_keywords
                if word in text_lower
            ],
            'clickbait_patterns': [
                pattern for pattern in self.clickbait_patterns
                if re.search(pattern, text_lower)
            ]
        }
        
        # Remove empty categories
        return {k: v for k, v in flagged.items() if v}
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitter
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_explanation_confidence(self, reasons: List[str], 
                                         flagged_keywords: Dict) -> float:
        """Calculate confidence in the explanation"""
        
        # More reasons and flagged keywords = higher confidence
        reason_score = min(len(reasons) / 8, 1.0) * 0.6
        keyword_score = min(sum(len(v) for v in flagged_keywords.values()) / 10, 1.0) * 0.4
        
        return reason_score + keyword_score
    
    def _generate_summary(self, prediction_result: Dict, reasons: List[str]) -> str:
        """Generate a human-readable summary"""
        
        verdict = prediction_result.get('verdict', 'uncertain')
        confidence = prediction_result.get('confidence', 0)
        
        if verdict == 'fake':
            summary = f"This content is classified as **LIKELY FAKE** with {confidence:.0%} confidence. "
        elif verdict == 'real':
            summary = f"This content appears to be **LIKELY REAL** with {confidence:.0%} confidence. "
        else:
            summary = f"This content is **UNCERTAIN** and requires further verification. "
        
        if reasons:
            top_reasons = reasons[:3]
            summary += f"Key indicators: {', '.join(top_reasons)}."
        
        return summary
    
    def generate_detailed_report(self, text: str, prediction_result: Dict) -> str:
        """Generate a detailed explainability report"""
        
        explanation = self.explain_prediction(text, prediction_result)
        
        report = []
        report.append("=" * 70)
        report.append("MISINFORMATION DETECTION EXPLANATION")
        report.append("=" * 70)
        
        # Summary
        report.append(f"\n{explanation['summary']}\n")
        
        # Reasons
        report.append("REASONS FOR CLASSIFICATION:")
        report.append("-" * 70)
        for i, reason in enumerate(explanation['reasons'], 1):
            report.append(f"{i}. {reason}")
        
        # Flagged keywords
        if explanation['flagged_keywords']:
            report.append(f"\nFLAGGED KEYWORDS:")
            report.append("-" * 70)
            for category, keywords in explanation['flagged_keywords'].items():
                report.append(f"  {category.upper()}: {', '.join(keywords)}")
        
        # Highlighted snippets
        if explanation['highlighted_snippets']:
            report.append(f"\nHIGH-RISK SNIPPETS:")
            report.append("-" * 70)
            for snippet in explanation['highlighted_snippets'][:3]:
                report.append(f"\n📍 \"{snippet['sentence']}\"")
                report.append(f"   Risk Score: {snippet['risk_score']:.2f}")
                report.append(f"   Issues: {', '.join(snippet['reasons'])}")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)


def demo():
    """Demo the explainability engine"""
    
    # Sample text
    sample_text = """
    BREAKING: Government hiding shocking vaccine microchip truth! 
    This urgent revelation will shock you! Secret documents exposed by anonymous sources 
    reveal the terrifying conspiracy. You won't believe what they're hiding from us!
    """
    
    # Mock prediction result
    mock_result = {
        'verdict': 'fake',
        'confidence': 0.87,
        'components': {
            'ml_classification': {'fake_probability': 0.85},
            'linguistic_analysis': {'sensational_words': 4, 'emotional_words': 2, 'clickbait_patterns': 1},
            'source_credibility': {'credibility_score': 0.2, 'source_type': 'unknown'},
            'fact_checking': {'checked': False}
        }
    }
    
    engine = ExplainabilityEngine()
    
    # Generate explanation
    explanation = engine.explain_prediction(sample_text, mock_result)
    
    print("\n🔍 Explainability Demo:")
    print(engine.generate_detailed_report(sample_text, mock_result))


if __name__ == "__main__":
    demo()
