#!/usr/bin/env python3
"""
Topic Modeling for Misinformation Analysis
Categorizes news articles into topics to identify misinformation trends.
"""

import logging
from typing import List, Dict, Tuple
import numpy as np
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import LatentDirichletAllocation, NMF
    from sklearn.cluster import KMeans
except ImportError:
    logger.warning("scikit-learn not available. Install with: pip install scikit-learn")


class TopicModeler:
    """
    Topic modeling for categorizing misinformation and identifying trends
    """
    
    # Predefined topics for Indian misinformation context
    INDIAN_TOPICS = {
        'health_misinformation': {
            'keywords': ['vaccine', 'cure', 'medicine', 'doctor', 'hospital', 'treatment', 
                        'disease', 'corona', 'covid', 'ayush', 'ayurveda', 'homeopathy'],
            'description': 'Health and Medical Misinformation'
        },
        'political_propaganda': {
            'keywords': ['modi', 'bjp', 'congress', 'election', 'government', 'minister',
                        'parliament', 'party', 'politician', 'vote', 'campaign', 'rally'],
            'description': 'Political Propaganda and Manipulation'
        },
        'religious_communal': {
            'keywords': ['hindu', 'muslim', 'christian', 'sikh', 'temple', 'mosque',
                        'church', 'gurudwara', 'religious', 'communal', 'riot', 'attack'],
            'description': 'Religious and Communal Misinformation'
        },
        'conspiracy_theories': {
            'keywords': ['conspiracy', 'secret', 'hidden', 'exposed', 'cover-up', 'shadow',
                        'illuminati', 'agenda', 'plan', 'control', 'manipulate'],
            'description': 'Conspiracy Theories'
        },
        'financial_scams': {
            'keywords': ['money', 'investment', 'scheme', 'loan', 'bank', 'scam',
                        'fraud', 'bitcoin', 'cryptocurrency', 'trading', 'stock', 'rupee'],
            'description': 'Financial Scams and Fraud'
        },
        'celebrity_fake_news': {
            'keywords': ['bollywood', 'actor', 'actress', 'celebrity', 'death', 'scandal',
                        'film', 'movie', 'star', 'khan', 'kapoor', 'kumar'],
            'description': 'Celebrity and Entertainment Fake News'
        },
        'natural_disaster': {
            'keywords': ['earthquake', 'flood', 'tsunami', 'cyclone', 'drought', 'disaster',
                        'weather', 'climate', 'storm', 'landslide', 'fire'],
            'description': 'Natural Disaster Misinformation'
        },
        'technology_myths': {
            'keywords': ['5g', 'technology', 'smartphone', 'internet', 'wifi', 'radiation',
                        'ai', 'robot', 'cyber', 'hacking', 'virus', 'app'],
            'description': 'Technology Myths and Misinformation'
        }
    }
    
    def __init__(self, n_topics: int = 8):
        self.n_topics = n_topics
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        self.lda_model = None
        self.nmf_model = None
        self.kmeans_model = None
        
    def classify_topic_rule_based(self, text: str) -> Dict:
        """
        Classify text into predefined topics using rule-based approach
        Fast and interpretable for Indian context
        """
        text_lower = text.lower()
        topic_scores = {}
        
        for topic_name, topic_info in self.INDIAN_TOPICS.items():
            keywords = topic_info['keywords']
            score = sum(1 for keyword in keywords if keyword in text_lower)
            topic_scores[topic_name] = {
                'score': score,
                'description': topic_info['description']
            }
        
        # Get primary topic (highest score)
        if topic_scores:
            primary_topic = max(topic_scores.items(), key=lambda x: x[1]['score'])
            
            if primary_topic[1]['score'] > 0:
                return {
                    'primary_topic': primary_topic[0],
                    'topic_description': primary_topic[1]['description'],
                    'confidence': min(primary_topic[1]['score'] / 5, 1.0),
                    'all_topics': topic_scores
                }
        
        return {
            'primary_topic': 'general_misinformation',
            'topic_description': 'General/Unclassified Misinformation',
            'confidence': 0.3,
            'all_topics': topic_scores
        }
    
    def fit_lda(self, documents: List[str]):
        """Train LDA topic model on documents"""
        logger.info(f"Training LDA model with {len(documents)} documents...")
        
        # Vectorize documents
        doc_term_matrix = self.vectorizer.fit_transform(documents)
        
        # Train LDA
        self.lda_model = LatentDirichletAllocation(
            n_components=self.n_topics,
            random_state=42,
            max_iter=20
        )
        self.lda_model.fit(doc_term_matrix)
        
        logger.info("LDA model trained successfully")
        
    def fit_nmf(self, documents: List[str]):
        """Train NMF topic model on documents"""
        logger.info(f"Training NMF model with {len(documents)} documents...")
        
        # Vectorize documents
        doc_term_matrix = self.vectorizer.fit_transform(documents)
        
        # Train NMF
        self.nmf_model = NMF(
            n_components=self.n_topics,
            random_state=42,
            max_iter=200
        )
        self.nmf_model.fit(doc_term_matrix)
        
        logger.info("NMF model trained successfully")
    
    def predict_topic_lda(self, text: str) -> Dict:
        """Predict topic using trained LDA model"""
        if not self.lda_model:
            raise ValueError("LDA model not trained. Call fit_lda() first.")
        
        # Transform text
        text_vector = self.vectorizer.transform([text])
        topic_distribution = self.lda_model.transform(text_vector)[0]
        
        # Get dominant topic
        dominant_topic = np.argmax(topic_distribution)
        
        return {
            'dominant_topic': int(dominant_topic),
            'topic_distribution': topic_distribution.tolist(),
            'confidence': float(topic_distribution[dominant_topic])
        }
    
    def get_topic_keywords(self, n_words: int = 10) -> Dict:
        """Get top keywords for each discovered topic"""
        if not self.lda_model and not self.nmf_model:
            raise ValueError("No model trained. Call fit_lda() or fit_nmf() first.")
        
        model = self.lda_model if self.lda_model else self.nmf_model
        feature_names = self.vectorizer.get_feature_names_out()
        
        topics = {}
        for topic_idx, topic in enumerate(model.components_):
            top_indices = topic.argsort()[-n_words:][::-1]
            top_words = [feature_names[i] for i in top_indices]
            topics[f'topic_{topic_idx}'] = top_words
        
        return topics
    
    def analyze_trend(self, documents: List[str], labels: List[int]) -> Dict:
        """
        Analyze misinformation trends
        
        Args:
            documents: List of news article texts
            labels: List of labels (0=real, 1=fake)
        
        Returns:
            Dictionary with trend analysis
        """
        logger.info(f"Analyzing trends from {len(documents)} documents...")
        
        # Classify each document
        topic_counts = defaultdict(lambda: {'fake': 0, 'real': 0, 'total': 0})
        
        for doc, label in zip(documents, labels):
            classification = self.classify_topic_rule_based(doc)
            topic = classification['primary_topic']
            
            topic_counts[topic]['total'] += 1
            if label == 1:
                topic_counts[topic]['fake'] += 1
            else:
                topic_counts[topic]['real'] += 1
        
        # Calculate fake percentage for each topic
        trend_analysis = {}
        for topic, counts in topic_counts.items():
            fake_percentage = (counts['fake'] / counts['total'] * 100) if counts['total'] > 0 else 0
            
            trend_analysis[topic] = {
                'description': self.INDIAN_TOPICS.get(topic, {}).get('description', 'Unknown'),
                'total_articles': counts['total'],
                'fake_count': counts['fake'],
                'real_count': counts['real'],
                'fake_percentage': fake_percentage,
                'risk_level': self._get_risk_level(fake_percentage)
            }
        
        # Sort by fake count
        sorted_trends = dict(sorted(
            trend_analysis.items(),
            key=lambda x: x[1]['fake_count'],
            reverse=True
        ))
        
        return {
            'topic_trends': sorted_trends,
            'total_topics_detected': len(topic_counts),
            'highest_risk_topic': max(sorted_trends.items(), key=lambda x: x[1]['fake_percentage'])[0] if sorted_trends else None
        }
    
    def _get_risk_level(self, fake_percentage: float) -> str:
        """Determine risk level based on fake percentage"""
        if fake_percentage >= 70:
            return 'CRITICAL'
        elif fake_percentage >= 50:
            return 'HIGH'
        elif fake_percentage >= 30:
            return 'MODERATE'
        elif fake_percentage >= 10:
            return 'LOW'
        else:
            return 'MINIMAL'
    
    def generate_topic_report(self, documents: List[str], labels: List[int]) -> str:
        """Generate a human-readable topic analysis report"""
        
        trend_analysis = self.analyze_trend(documents, labels)
        
        report = []
        report.append("=" * 70)
        report.append("MISINFORMATION TOPIC ANALYSIS REPORT")
        report.append("=" * 70)
        report.append(f"\nTotal Topics Analyzed: {trend_analysis['total_topics_detected']}")
        report.append(f"Highest Risk Topic: {trend_analysis['highest_risk_topic']}\n")
        
        report.append("\nTOPIC BREAKDOWN:")
        report.append("-" * 70)
        
        for topic, data in trend_analysis['topic_trends'].items():
            report.append(f"\n📌 {data['description']}")
            report.append(f"   Risk Level: {data['risk_level']}")
            report.append(f"   Total Articles: {data['total_articles']}")
            report.append(f"   Fake: {data['fake_count']} ({data['fake_percentage']:.1f}%)")
            report.append(f"   Real: {data['real_count']}")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)


def demo():
    """Demo the topic modeler"""
    
    # Sample documents
    documents = [
        "BREAKING: Modi government hiding vaccine microchip truth from public",
        "Government announces new healthcare infrastructure plan",
        "EXPOSED: Muslims planning attack on Hindu temples during Diwali",
        "Supreme Court delivers verdict on constitutional matter",
        "URGENT: 5G towers causing coronavirus spread - scientists confirm",
        "Parliamentary committee discusses digital infrastructure policy",
        "VIRAL: Bollywood star death was actually government assassination",
        "Film industry celebrates successful year at box office",
    ]
    
    labels = [1, 0, 1, 0, 1, 0, 1, 0]  # 1=fake, 0=real
    
    # Initialize topic modeler
    modeler = TopicModeler()
    
    # Classify individual documents
    print("\n🔍 Individual Document Classification:")
    print("-" * 70)
    for doc in documents[:3]:
        result = modeler.classify_topic_rule_based(doc)
        print(f"\nText: {doc}")
        print(f"Topic: {result['topic_description']}")
        print(f"Confidence: {result['confidence']:.2f}")
    
    # Generate trend report
    print("\n" + modeler.generate_topic_report(documents, labels))


if __name__ == "__main__":
    demo()
