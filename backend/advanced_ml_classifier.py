#!/usr/bin/env python3
"""
Advanced ML Classifier for Misinformation Detection
- Loads training data from structured CSV dataset (760+ examples)
- Multiple algorithms (Naive Bayes, SVM, Random Forest, Logistic Regression, Gradient Boosting)
- Feature engineering with TF-IDF, linguistic features, and Indian-context features
- Hinglish-aware with expanded fake news patterns
- Cross-validation, per-class metrics, and performance reporting
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
)
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score,
    f1_score, roc_auc_score
)
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import MinMaxScaler
import re
import os
import json
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import pickle
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure NLTK data is available
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)


class LinguisticFeatureExtractor(BaseEstimator, TransformerMixin):
    """Extract linguistic features that indicate misinformation"""

    def __init__(self):
        self.sia = SentimentIntensityAnalyzer()

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        features = []

        for text in X:
            text_lower = text.lower()
            words = text.split()
            word_count = max(len(words), 1)

            # Feature 1: Sensational keywords count (normalized)
            sensational_keywords = [
                'breaking', 'urgent', 'shocking', 'exclusive', 'exposed', 'revealed',
                'secret', 'hidden', 'conspiracy', 'cover-up', 'scandal', 'bombshell',
                'viral', 'trending', 'must see', 'unbelievable', 'incredible', 'amazing',
                'alert', 'proof', 'leaked', 'caught', 'busted', 'warning',
                # Additional sensational patterns
                'suppressed', 'banned', 'deleted', 'censored', 'silenced',
                'whistleblower', 'classified', 'blackout', 'hidden camera',
                'insider reveals', 'mainstream media hiding', 'doctors hate',
                'forward before deleted', 'share before removed'
            ]
            sensational_count = sum(1 for kw in sensational_keywords if kw in text_lower)
            sensational_ratio = sensational_count / word_count

            # Feature 2: Emotional manipulation words (normalized)
            emotional_words = [
                'outraged', 'furious', 'devastated', 'terrified', 'shocked',
                'disgusted', 'betrayed', 'abandoned', 'threatened', 'angry',
                'horrifying', 'nightmare', 'deadly', 'catastrophic', 'crisis'
            ]
            emotional_count = sum(1 for w in emotional_words if w in text_lower)
            emotional_ratio = emotional_count / word_count

            # Feature 3: Attribution indicators (binary)
            attribution_indicators = [
                'according to', 'sources say', 'officials confirm', 'study shows',
                'research indicates', 'data reveals', 'experts believe', 'report states',
                'published in', 'peer-reviewed', 'government says', 'ministry of',
                'official statement', 'press release', 'data from', 'survey finds'
            ]
            has_attribution = 1.0 if any(ind in text_lower for ind in attribution_indicators) else 0.0

            # Feature 4: Excessive punctuation ratios
            exclamation_ratio = text.count('!') / word_count
            question_ratio = text.count('?') / word_count
            ellipsis_count = text.count('...') / word_count

            # Feature 5: ALL CAPS ratio
            caps_words = sum(1 for w in words if w.isupper() and len(w) > 2)
            caps_ratio = caps_words / word_count

            # Feature 6: Sentiment extremity (VADER)
            sentiment = self.sia.polarity_scores(text)
            sentiment_extremity = abs(sentiment['compound'])
            negative_sentiment = abs(sentiment['neg'])

            # Feature 7: Text length features
            text_length = len(text)
            avg_word_length = sum(len(w) for w in words) / word_count
            # Very short texts are more suspicious (WhatsApp forwards)
            is_very_short = 1.0 if text_length < 100 else 0.0

            # Feature 8: Clickbait patterns
            clickbait_patterns = [
                r'\d+ (things|ways|reasons|facts)',
                r'you (won\'t|will not) believe',
                r'this (will|might) (shock|surprise) you',
                r'number \d+ will',
                r'what happens next',
                r'doctors hate',
                r'one (simple|weird) trick'
            ]
            clickbait_count = sum(1 for p in clickbait_patterns if re.search(p, text_lower))

            # Feature 9: Urgency language
            urgency_words = [
                'now', 'immediately', 'right now', 'hurry', 'before it\'s too late',
                'act fast', 'don\'t wait', 'last chance', 'share before deleted',
                'forward to', 'spread the word', 'wake up'
            ]
            urgency_count = sum(1 for u in urgency_words if u in text_lower)

            # Feature 10: Numerical claim density
            number_pattern = re.findall(r'\d+', text)
            number_density = len(number_pattern) / word_count

            # Feature 11: Source credibility signals (lack of)
            no_source = 1.0 if not any(sig in text_lower for sig in [
                'says', 'said', 'reported', 'confirmed', 'announced',
                'stated', 'according', 'ministry', 'department', 'official'
            ]) else 0.0

            features.append([
                sensational_count,
                sensational_ratio,
                emotional_count,
                emotional_ratio,
                has_attribution,
                exclamation_ratio,
                question_ratio,
                ellipsis_count,
                caps_ratio,
                sentiment_extremity,
                negative_sentiment,
                is_very_short,
                avg_word_length,
                clickbait_count,
                urgency_count,
                number_density,
                no_source
            ])

        return np.array(features)


class IndianContextFeatureExtractor(BaseEstimator, TransformerMixin):
    """Extract India-specific features that indicate misinformation"""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        features = []

        for text in X:
            text_lower = text.lower()
            words = text.split()
            word_count = max(len(words), 1)

            # Feature 1: Hindi/Hinglish sensational keywords
            hindi_sensational = [
                'khatre mein', 'sabko batao', 'sach samne aaya', 'janta jaago',
                'share karo', 'forward karo', 'exposed', 'parda faash',
                'sarkaar', 'chupa raha', 'media blackout', 'sachchi news',
                'ye dekho', 'video dekho', 'photo dekho', 'sabko batao'
            ]
            hindi_sensational_count = sum(1 for kw in hindi_sensational if kw in text_lower)

            # Feature 2: WhatsApp forward patterns
            whatsapp_patterns = [
                'forward to', 'share to', 'send to', 'forward karo',
                '10 logo', '10 people', 'before deleted',
                'share before', 'ye message', 'group mein', 'sabko bhejo',
                'please share', 'must share', 'jarur share', 'zaroor forward'
            ]
            whatsapp_count = sum(1 for p in whatsapp_patterns if p in text_lower)

            # Feature 3: Communal trigger patterns
            communal_triggers = [
                'hindu khatre', 'muslim attack', 'love jihad', 'conversion',
                'temple destroy', 'mandir tod', 'mosque', 'masjid',
                'communal', 'riot', 'lynching', 'mob', 'religious violence',
                'anti-national', 'deshdrohi', 'traitor', 'jihad'
            ]
            communal_count = sum(1 for t in communal_triggers if t in text_lower)

            # Feature 4: Fake official/authority patterns
            fake_authority = [
                'government ne kaha', 'sarkar ka aadesh', 'pm ne bola',
                'who ne maana', 'doctor ne confirm', 'scientist ne bola',
                'nasa confirmed', 'un ne kaha', 'supreme court ne',
                'rbi ne bola', 'army ne kaha'
            ]
            fake_authority_count = sum(1 for f in fake_authority if f in text_lower)

            # Feature 5: Miracle/cure claims (India-specific)
            miracle_claims = [
                'cure', 'theek', 'ilaaj', 'upchar', 'ramban', 'miracle',
                'ayurvedic cure', 'desi nuskha', 'gharelu upay',
                'haldi', 'tulsi', 'neem', 'cow urine', 'gaumutra',
                'patanjali', 'baba ramdev',
                # Additional miracle/pseudoscience patterns
                'miracle cure', 'ancient remedy', 'natural cure', '100% effective',
                'doctors hiding', 'pharma hiding', 'permanently cures', 'guaranteed cure',
                'theek ho jata', 'cancer theek', 'dawai nahi chahiye', 'bilkul theek'
            ]
            miracle_count = sum(1 for m in miracle_claims if m in text_lower)

            # Feature 6: Inflated statistics (crore, lakh with large numbers)
            inflated_stats = len(re.findall(
                r'\d+\s*(crore|lakh|billion|million|percent|%)', text_lower
            ))

            # Feature 7: India-specific credibility signals
            indian_credible = [
                'pib', 'pti', 'ani', 'ians', 'press trust',
                'doordarshan', 'all india radio', 'prasar bharati',
                'ministry of', 'niti aayog', 'rbi', 'sebi',
                'isro', 'drdo', 'icar', 'icmr', 'aiims',
                'supreme court', 'high court', 'election commission'
            ]
            has_indian_source = 1.0 if any(s in text_lower for s in indian_credible) else 0.0

            # Feature 8: Deepfake/media manipulation indicators
            media_manipulation = [
                'old photo', 'old video', 'cropped', 'morphed', 'doctored',
                'fake photo', 'fake video', 'edited', 'photoshopped',
                'out of context', 'misleading', 'actually from', 'different country',
                'ai generated', 'deepfake'
            ]
            media_manip_count = sum(1 for m in media_manipulation if m in text_lower)

            features.append([
                hindi_sensational_count,
                whatsapp_count,
                communal_count,
                fake_authority_count,
                miracle_count,
                inflated_stats,
                has_indian_source,
                media_manip_count
            ])

        return np.array(features)


def load_training_data():
    """Load training data from CSV dataset file"""
    dataset_path = Path(__file__).parent / 'datasets' / 'indian_misinformation_v4.csv'

    if not dataset_path.exists():
        logger.warning(f"Dataset file not found at {dataset_path}, falling back to built-in data")
        return _create_fallback_training_data()

    try:
        df = pd.read_csv(dataset_path)

        # Validate required columns
        required_cols = ['text', 'label']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Dataset must contain columns: {required_cols}")

        # Clean data
        df = df.dropna(subset=['text', 'label'])
        df['text'] = df['text'].astype(str).str.strip()
        df['label'] = df['label'].astype(int)
        df = df[df['text'].str.len() > 10]  # Remove very short entries

        # Remove duplicates
        df = df.drop_duplicates(subset=['text'])

        fake_count = (df['label'] == 1).sum()
        real_count = (df['label'] == 0).sum()
        logger.info(f"Loaded dataset from {dataset_path}: {len(df)} examples "
                     f"(fake: {fake_count}, real: {real_count})")

        return df

    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return _create_fallback_training_data()


def _create_fallback_training_data():
    """Minimal fallback dataset if CSV is unavailable"""
    examples = [
        ("BREAKING: Government secretly controlling weather with 5G towers!", 1),
        ("EXPOSED: Hidden documents reveal vaccine microchips are real", 1),
        ("SHOCKING: Cow urine cures cancer - doctors hiding truth!", 1),
        ("ALERT: All bank accounts will be frozen tomorrow - withdraw now!", 1),
        ("Hindu khatre mein hai - 2025 tak India Islamic desh ban jayega", 1),
        ("VIRAL: Miracle herb cures diabetes in 3 days - pharma hates this", 1),
        ("URGENT: WhatsApp band hone wala hai - forward karo 10 logo ko", 1),
        ("EXPOSED: EVM machines rigged in elections - video proof!", 1),
        ("Share before deleted - secret plan of government exposed!", 1),
        ("BREAKING: Earthquake predicted for Delhi next week - evacuate!", 1),
        ("Government announces new infrastructure development plan for northeast India", 0),
        ("Parliament passes bill to improve healthcare access in rural areas", 0),
        ("According to RBI, GDP growth rate stands at 6.8 percent this quarter", 0),
        ("ISRO successfully launches communication satellite from Sriharikota", 0),
        ("Supreme Court delivers verdict on constitutional matter regarding privacy", 0),
        ("Medical study published in AIIMS journal shows effectiveness of new treatment", 0),
        ("Stock market shows steady growth this quarter on strong corporate earnings", 0),
        ("Weather department forecasts normal monsoon this year across India", 0),
        ("India signs bilateral fisheries agreement with Sri Lanka for sustainable fishing", 0),
        ("Fact-check: Viral claim about banning Rs 500 notes is FALSE says RBI", 0),
    ]
    df = pd.DataFrame(examples, columns=['text', 'label'])
    logger.warning(f"Using fallback dataset with only {len(df)} examples")
    return df


def build_advanced_classifier():
    """Build advanced ensemble classifier with multiple algorithms"""

    # Load training data from CSV
    df = load_training_data()

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        df['text'], df['label'], test_size=0.2, random_state=42, stratify=df['label']
    )

    logger.info(f"Training set: {len(X_train)} examples")
    logger.info(f"Test set: {len(X_test)} examples")

    # --- Feature Engineering ---
    # TF-IDF on words: lowered min_df for better coverage
    tfidf_words = TfidfVectorizer(
        max_features=8000,
        stop_words='english',
        ngram_range=(1, 3),
        min_df=1,
        max_df=0.85,
        sublinear_tf=True
    )

    # TF-IDF on character n-grams: captures misspellings and transliteration
    tfidf_chars = TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(3, 6),
        max_features=3000,
        min_df=1,
        max_df=0.9,
        sublinear_tf=True
    )

    # Linguistic feature extractor
    linguistic_features = LinguisticFeatureExtractor()

    # Indian context feature extractor
    indian_features = IndianContextFeatureExtractor()

    # Combine all features
    feature_union = FeatureUnion([
        ('tfidf_words', tfidf_words),
        ('tfidf_chars', tfidf_chars),
        ('linguistic', linguistic_features),
        ('indian_context', indian_features)
    ])

    # --- Ensemble Classifier ---
    nb_classifier = MultinomialNB(alpha=0.05)
    svm_classifier = SVC(kernel='linear', probability=True, C=1.5, class_weight='balanced')
    rf_classifier = RandomForestClassifier(
        n_estimators=200, max_depth=20, random_state=42, class_weight='balanced'
    )
    lr_classifier = LogisticRegression(
        C=2.0, max_iter=1000, solver='lbfgs', class_weight='balanced'
    )
    gb_classifier = GradientBoostingClassifier(
        n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42
    )

    # 5-model ensemble with soft voting
    ensemble_classifier = VotingClassifier([
        ('nb', nb_classifier),
        ('svm', svm_classifier),
        ('rf', rf_classifier),
        ('lr', lr_classifier),
        ('gb', gb_classifier)
    ], voting='soft', weights=[1, 2, 2, 2, 2])

    # Final pipeline
    classifier_pipeline = Pipeline([
        ('features', feature_union),
        ('classifier', ensemble_classifier)
    ])

    # --- Training ---
    logger.info("Training advanced 5-model ensemble classifier...")
    classifier_pipeline.fit(X_train, y_train)

    # --- Evaluation ---
    logger.info("Evaluating classifier performance...")

    # Cross-validation with stratified folds
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(classifier_pipeline, X_train, y_train, cv=cv, scoring='f1')
    logger.info(f"Cross-validation F1: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")

    # Test set evaluation
    y_pred = classifier_pipeline.predict(X_test)
    y_proba = classifier_pipeline.predict_proba(X_test)[:, 1]

    test_accuracy = accuracy_score(y_test, y_pred)
    test_f1 = f1_score(y_test, y_pred)
    test_auc = roc_auc_score(y_test, y_proba)

    logger.info(f"Test accuracy: {test_accuracy:.3f}")
    logger.info(f"Test F1 score: {test_f1:.3f}")
    logger.info(f"Test ROC-AUC: {test_auc:.3f}")

    # Detailed classification report
    report = classification_report(
        y_test, y_pred, target_names=['Legitimate', 'Misinformation'], output_dict=True
    )
    logger.info("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Legitimate', 'Misinformation']))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    logger.info(f"Confusion Matrix:\n{cm}")

    # Save metrics to JSON
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'dataset_size': len(df),
        'train_size': len(X_train),
        'test_size': len(X_test),
        'cv_f1_mean': round(cv_scores.mean(), 4),
        'cv_f1_std': round(cv_scores.std(), 4),
        'test_accuracy': round(test_accuracy, 4),
        'test_f1': round(test_f1, 4),
        'test_roc_auc': round(test_auc, 4),
        'classification_report': report,
        'confusion_matrix': cm.tolist()
    }

    metrics_path = Path(__file__).parent / 'models' / 'training_metrics.json'
    metrics_path.parent.mkdir(exist_ok=True)
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Training metrics saved to {metrics_path}")

    # Sample predictions
    logger.info("\nSample Predictions:")
    test_samples = [
        "BREAKING: Government hiding shocking truth about vaccines - pharma exposed!",
        "Government announces new healthcare policy for rural India",
        "URGENT: Secret documents reveal conspiracy to overthrow democracy",
        "Research study published in Nature shows benefits of exercise",
        "VIRAL: This miracle cure will shock you - doctors HATE it!",
        "Parliament passes education reform bill with bipartisan support",
        "Hindu khatre mein hai - forward karo sabko ye video!",
        "According to ISRO chairman, Chandrayaan-3 data analysis is progressing well",
        "EXPOSED: EVM machines rigged - video proof showing hacking",
        "Fact-check: Viral claim about government banning cash is FALSE says RBI",
    ]

    for sample in test_samples:
        prediction = classifier_pipeline.predict([sample])[0]
        probability = classifier_pipeline.predict_proba([sample])[0]
        label = "FAKE" if prediction == 1 else "REAL"
        confidence = max(probability)
        fake_prob = probability[1] if len(probability) > 1 else 0.5
        logger.info(f"  [{label}] (conf={confidence:.3f}, fake_p={fake_prob:.3f}) "
                     f"'{sample[:60]}...'")

    return classifier_pipeline


def save_classifier(classifier, filename=None):
    """Save the trained classifier"""
    if filename is None:
        filename = str(Path(__file__).parent / 'models' / 'advanced_misinformation_classifier.pkl')
    Path(filename).parent.mkdir(exist_ok=True)
    with open(filename, 'wb') as f:
        pickle.dump(classifier, f)
    logger.info(f"Classifier saved to {filename}")


class _CustomUnpickler(pickle.Unpickler):
    """Custom unpickler that resolves classes saved under __main__ back to this module.

    When advanced_ml_classifier.py is run directly (python advanced_ml_classifier.py),
    pickle stores custom classes as '__main__.LinguisticFeatureExtractor' etc.
    When those pickled models are later loaded from a different entry-point
    (e.g. main_application.py), Python tries to find the class in __main__ and fails.
    This unpickler transparently redirects those lookups back to this module.
    """
    def find_class(self, module, name):
        if module == '__main__':
            import advanced_ml_classifier
            if hasattr(advanced_ml_classifier, name):
                return getattr(advanced_ml_classifier, name)
        return super().find_class(module, name)


def load_classifier(filename=None):
    """Load a trained classifier"""
    if filename is None:
        filename = str(Path(__file__).parent / 'models' / 'advanced_misinformation_classifier.pkl')
    try:
        with open(filename, 'rb') as f:
            classifier = _CustomUnpickler(f).load()
        logger.info(f"Classifier loaded from {filename}")
        return classifier
    except FileNotFoundError:
        logger.warning(f"Classifier file {filename} not found, building new one...")
        classifier = build_advanced_classifier()
        save_classifier(classifier, filename)
        return classifier


if __name__ == "__main__":
    print("🧠 Building Advanced ML Classifier for Misinformation Detection")
    print("=" * 70)

    # Build and train classifier
    classifier = build_advanced_classifier()

    # Save classifier
    save_classifier(classifier)

    print("\n✅ Advanced classifier built and saved successfully!")
    print("📊 Ready for integration with real-time system")