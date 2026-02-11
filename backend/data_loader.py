#!/usr/bin/env python3
"""
Data Loader for Misinformation Detection Datasets
Supports CSV, JSON, and custom formats for training the ML model.
"""

import pandas as pd
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DataLoader:
    """Load and preprocess datasets for misinformation detection"""
    
    def __init__(self, datasets_dir: str = "datasets"):
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        
    def load_csv(self, filename: str, text_column: str = 'text', 
                 label_column: str = 'label', source_column: Optional[str] = 'source') -> pd.DataFrame:
        """Load dataset from CSV file"""
        filepath = self.datasets_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")
        
        df = pd.read_csv(filepath)
        
        # Validate required columns
        if text_column not in df.columns:
            raise ValueError(f"Text column '{text_column}' not found in CSV")
        if label_column not in df.columns:
            raise ValueError(f"Label column '{label_column}' not found in CSV")
        
        # Standardize column names
        result_df = pd.DataFrame({
            'text': df[text_column],
            'label': df[label_column]
        })
        
        if source_column and source_column in df.columns:
            result_df['source'] = df[source_column]
        else:
            result_df['source'] = 'unknown'
        
        logger.info(f"Loaded {len(result_df)} examples from {filename}")
        return result_df
    
    def load_json(self, filename: str) -> pd.DataFrame:
        """Load dataset from JSON file"""
        filepath = self.datasets_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Validate required fields
        if 'text' not in df.columns or 'label' not in df.columns:
            raise ValueError("JSON must contain 'text' and 'label' fields")
        
        if 'source' not in df.columns:
            df['source'] = 'unknown'
        
        logger.info(f"Loaded {len(df)} examples from {filename}")
        return df
    
    def load_multiple(self, filenames: List[str]) -> pd.DataFrame:
        """Load and combine multiple dataset files"""
        dfs = []
        
        for filename in filenames:
            try:
                if filename.endswith('.csv'):
                    df = self.load_csv(filename)
                elif filename.endswith('.json'):
                    df = self.load_json(filename)
                else:
                    logger.warning(f"Unsupported file format: {filename}")
                    continue
                
                dfs.append(df)
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")
        
        if not dfs:
            raise ValueError("No datasets were successfully loaded")
        
        combined_df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Combined {len(dfs)} datasets: {len(combined_df)} total examples")
        
        return combined_df
    
    def preprocess(self, df: pd.DataFrame, 
                   clean_text: bool = True,
                   remove_duplicates: bool = True,
                   balance_classes: bool = False) -> pd.DataFrame:
        """Preprocess the dataset"""
        
        original_size = len(df)
        
        # Remove rows with missing text or labels
        df = df.dropna(subset=['text', 'label'])
        logger.info(f"Removed {original_size - len(df)} rows with missing data")
        
        # Clean text
        if clean_text:
            df['text'] = df['text'].apply(self._clean_text)
        
        # Remove duplicates
        if remove_duplicates:
            before = len(df)
            df = df.drop_duplicates(subset=['text'])
            logger.info(f"Removed {before - len(df)} duplicate entries")
        
        # Balance classes (optional)
        if balance_classes:
            df = self._balance_classes(df)
        
        # Ensure labels are binary (0 or 1)
        df['label'] = df['label'].astype(int)
        
        logger.info(f"Final dataset: {len(df)} examples")
        logger.info(f"  - Fake/Misinformation: {(df['label'] == 1).sum()}")
        logger.info(f"  - Legitimate: {(df['label'] == 0).sum()}")
        
        return df
    
    def _clean_text(self, text: str) -> str:
        """Clean text data"""
        if not isinstance(text, str):
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove URLs (optional - can keep for source analysis)
        # text = re.sub(r'http\S+|www\S+', '', text)
        
        return text.strip()
    
    def _balance_classes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Balance classes using undersampling"""
        
        fake_count = (df['label'] == 1).sum()
        real_count = (df['label'] == 0).sum()
        
        logger.info(f"Before balancing: Fake={fake_count}, Real={real_count}")
        
        # Undersample the majority class
        min_count = min(fake_count, real_count)
        
        fake_samples = df[df['label'] == 1].sample(n=min_count, random_state=42)
        real_samples = df[df['label'] == 0].sample(n=min_count, random_state=42)
        
        balanced_df = pd.concat([fake_samples, real_samples]).sample(frac=1, random_state=42)
        
        logger.info(f"After balancing: {len(balanced_df)} examples ({min_count} each class)")
        
        return balanced_df
    
    def split_data(self, df: pd.DataFrame, 
                   test_size: float = 0.2,
                   val_size: float = 0.1,
                   random_seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split data into train, validation, and test sets"""
        
        # First split: train+val vs test
        train_val, test = train_test_split(
            df, test_size=test_size, random_state=random_seed, stratify=df['label']
        )
        
        # Second split: train vs val
        if val_size > 0:
            val_size_adjusted = val_size / (1 - test_size)
            train, val = train_test_split(
                train_val, test_size=val_size_adjusted, random_state=random_seed, stratify=train_val['label']
            )
        else:
            train = train_val
            val = pd.DataFrame(columns=df.columns)
        
        logger.info(f"Data split: Train={len(train)}, Val={len(val)}, Test={len(test)}")
        
        return train, val, test
    
    def save_processed_dataset(self, df: pd.DataFrame, filename: str):
        """Save processed dataset"""
        filepath = self.datasets_dir / filename
        df.to_csv(filepath, index=False)
        logger.info(f"Saved processed dataset to {filepath}")
    
    def create_indian_context_dataset(self, output_filename: str = "indian_misinformation.csv"):
        """Create a custom dataset focused on Indian context"""
        
        # Expanded dataset with more Indian-specific examples
        data = {
            'text': [
                # Fake news examples
                "BREAKING: Modi government secretly selling India to China, leaked documents reveal massive conspiracy",
                "EXPOSED: Aadhaar data being used to control population through 5G towers across India",
                "SHOCKING: Rahul Gandhi admits to being a Pakistani agent in leaked audio recording",
                "URGENT: Cow urine cures coronavirus - AYUSH ministry hiding this truth from public",
                "VIRAL: Muslim communities planning nationwide attack on Hindu festivals this Diwali",
                "ALERT: Government adding microchips in new currency notes to track citizens",
                "BREAKING: Bollywood actors involved in massive drug and human trafficking ring",
                "EXPOSED: Indian Army losing territory to China but media not reporting truth",
                "SHOCKING: COVID vaccine contains pig DNA - Muslims and Hindus should avoid",
                "URGENT: Modi planning to sell Taj Mahal to American hotel chain",
                
                # Legitimate news examples
                "Government of India announces new infrastructure development plan worth 100 lakh crore rupees",
                "Supreme Court delivers landmark verdict on right to privacy in India",
                "According to Ministry of Health, India records 2000 new COVID-19 cases today",
                "Reserve Bank of India maintains repo rate at 6.5 percent in latest policy meeting",
                "Parliament passes bill to provide 33% reservation for women in legislative bodies",
                "Indian Space Research Organisation successfully launches communication satellite GSAT-30",
                "Ministry of Education announces new National Education Policy implementation guidelines",
                "Election Commission releases schedule for upcoming state assembly elections in five states",
                "Chief Justice of India inaugurates new court complex in Delhi High Court",
                "Finance Minister presents union budget with focus on infrastructure and healthcare spending"
            ],
            'label': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'source': ['Unknown', 'Social Media', 'WhatsApp Forward', 'Fake News Site', 'Unknown',
                      'Facebook Post', 'Unknown', 'Twitter Rumor', 'WhatsApp Forward', 'Conspiracy Blog',
                      'PTI', 'The Hindu', 'Ministry of Health', 'Economic Times', 'NDTV',
                      'ISRO Official', 'Press Information Bureau', 'Election Commission', 'Bar and Bench', 'Indian Express']
        }
        
        df = pd.DataFrame(data)
        self.save_processed_dataset(df, output_filename)
        
        logger.info(f"Created Indian context dataset: {output_filename}")
        return df


def main():
    """Demo usage of DataLoader"""
    loader = DataLoader(datasets_dir='datasets')
    
    # Create a sample Indian context dataset
    indian_df = loader.create_indian_context_dataset()
    
    # Preprocess
    processed_df = loader.preprocess(indian_df, balance_classes=False)
    
    # Split data
    train, val, test = loader.split_data(processed_df, test_size=0.2, val_size=0.1)
    
    print("\n✅ Data pipeline ready!")
    print(f"📊 Training samples: {len(train)}")
    print(f"📊 Validation samples: {len(val)}")
    print(f"📊 Test samples: {len(test)}")


if __name__ == "__main__":
    main()
