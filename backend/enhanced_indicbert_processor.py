#!/usr/bin/env python3
"""
Enhanced IndicBERT Processor with Fine-tuning Capabilities
Supports both inference and fine-tuning for Indian language misinformation detection.
"""

import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    AutoModel,
    AdamW, 
    get_linear_schedule_with_warmup
)
from typing import Dict, List, Tuple, Optional
import numpy as np
import logging
from tqdm import tqdm
import pickle
from functools import lru_cache

logger = logging.getLogger(__name__)


class MisinformationDataset(Dataset):
    """PyTorch Dataset for misinformation detection"""
    
    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = int(self.labels[idx])
        
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'label': torch.tensor(label, dtype=torch.long)
        }


class EnhancedIndicBERTProcessor:
    """Enhanced IndicBERT processor with fine-tuning and caching"""
    
    def __init__(self, model_name: str = "ai4bharat/indic-bert", num_labels: int = 2):
        self.model_name = model_name
        self.num_labels = num_labels
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = None
        self.model = None
        self.classification_model = None
        self.is_finetuned = False
        
        # Cache for embeddings (LRU cache for efficiency)
        self._embedding_cache = {}
        self.cache_size = 1000
        
        logger.info(f"🧠 Initializing Enhanced IndicBERT on {self.device}")
        self._initialize_model()
    
    def _initialize_model(self, for_classification: bool = False):
        """Initialize IndicBERT model"""
        try:
            logger.info(f"Loading tokenizer from {self.model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            if for_classification:
                logger.info("Loading IndicBERT for sequence classification...")
                self.classification_model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    num_labels=self.num_labels
                )
                self.classification_model.to(self.device)
            else:
                logger.info("Loading base IndicBERT model...")
                self.model = AutoModel.from_pretrained(self.model_name)
                self.model.to(self.device)
            
            logger.info("✅ IndicBERT loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load IndicBERT: {e}")
            raise
    
    @lru_cache(maxsize=1000)
    def get_embeddings(self, text: str) -> np.ndarray:
        """Get IndicBERT embeddings with LRU caching"""
        if not self.model:
            self._initialize_model(for_classification=False)
        
        try:
            # Tokenize
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                padding=True, 
                max_length=512
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get embeddings
            self.model.eval()
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
            
            return embeddings.flatten()
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return np.random.rand(768)
    
    def get_embeddings_batch(self, texts: List[str], batch_size: int = 16) -> np.ndarray:
        """Get embeddings for multiple texts efficiently"""
        if not self.model:
            self._initialize_model(for_classification=False)
        
        all_embeddings = []
        
        self.model.eval()
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                inputs = self.tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    truncation=True,
                    padding=True,
                    max_length=512
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
                all_embeddings.append(embeddings)
        
        return np.vstack(all_embeddings)
    
    def fine_tune(self, 
                  train_texts: List[str],
                  train_labels: List[int],
                  val_texts: Optional[List[str]] = None,
                  val_labels: Optional[List[int]] = None,
                  epochs: int = 3,
                  batch_size: int = 16,
                  learning_rate: float = 2e-5,
                  output_dir: str = "models/finetuned_indicbert",
                  save_steps: int = 500):
        """Fine-tune IndicBERT for misinformation classification"""
        
        logger.info("🚀 Starting IndicBERT fine-tuning...")
        logger.info(f"Training samples: {len(train_texts)}")
        if val_texts:
            logger.info(f"Validation samples: {len(val_texts)}")
        
        # Initialize classification model
        self._initialize_model(for_classification=True)
        
        # Create datasets
        train_dataset = MisinformationDataset(train_texts, train_labels, self.tokenizer)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        val_loader = None
        if val_texts and val_labels:
            val_dataset = MisinformationDataset(val_texts, val_labels, self.tokenizer)
            val_loader = DataLoader(val_dataset, batch_size=batch_size)
        
        # Optimizer and scheduler
        optimizer = AdamW(self.classification_model.parameters(), lr=learning_rate)
        total_steps = len(train_loader) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=int(0.1 * total_steps),
            num_training_steps=total_steps
        )
        
        # Training loop
        best_val_accuracy = 0.0
        
        for epoch in range(epochs):
            logger.info(f"\n📚 Epoch {epoch + 1}/{epochs}")
            
            # Training
            self.classification_model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0
            
            progress_bar = tqdm(train_loader, desc="Training")
            for batch in progress_bar:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['label'].to(self.device)
                
                optimizer.zero_grad()
                
                outputs = self.classification_model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                
                loss = outputs.loss
                logits = outputs.logits
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.classification_model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                
                train_loss += loss.item()
                predictions = torch.argmax(logits, dim=1)
                train_correct += (predictions == labels).sum().item()
                train_total += labels.size(0)
                
                progress_bar.set_postfix({
                    'loss': f'{loss.item():.4f}',
                    'acc': f'{train_correct/train_total:.4f}'
                })
            
            avg_train_loss = train_loss / len(train_loader)
            train_accuracy = train_correct / train_total
            
            logger.info(f"Training Loss: {avg_train_loss:.4f}, Accuracy: {train_accuracy:.4f}")
            
            # Validation
            if val_loader:
                val_accuracy, val_loss = self._evaluate(val_loader)
                logger.info(f"Validation Loss: {val_loss:.4f}, Accuracy: {val_accuracy:.4f}")
                
                # Save best model
                if val_accuracy > best_val_accuracy:
                    best_val_accuracy = val_accuracy
                    self.save_model(output_dir)
                    logger.info(f"💾 Saved best model (accuracy: {val_accuracy:.4f})")
        
        self.is_finetuned = True
        logger.info("✅ Fine-tuning completed!")
        
        return {
            'final_train_accuracy': train_accuracy,
            'best_val_accuracy': best_val_accuracy if val_loader else None
        }
    
    def _evaluate(self, data_loader) -> Tuple[float, float]:
        """Evaluate model on validation/test set"""
        self.classification_model.eval()
        
        total_loss = 0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch in data_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['label'].to(self.device)
                
                outputs = self.classification_model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                
                total_loss += outputs.loss.item()
                predictions = torch.argmax(outputs.logits, dim=1)
                correct += (predictions == labels).sum().item()
                total += labels.size(0)
        
        accuracy = correct / total
        avg_loss = total_loss / len(data_loader)
        
        return accuracy, avg_loss
    
    def predict(self, text: str) -> Dict:
        """Predict misinformation for a single text"""
        if not self.classification_model:
            raise ValueError("Model not trained or loaded. Call fine_tune() or load_model() first.")
        
        self.classification_model.eval()
        
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.classification_model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)
            prediction = torch.argmax(logits, dim=1).item()
        
        return {
            'prediction': 'fake' if prediction == 1 else 'real',
            'confidence': probabilities[0][prediction].item(),
            'probabilities': {
                'real': probabilities[0][0].item(),
                'fake': probabilities[0][1].item()
            }
        }
    
    def predict_batch(self, texts: List[str], batch_size: int = 16) -> List[Dict]:
        """Predict misinformation for multiple texts"""
        if not self.classification_model:
            raise ValueError("Model not trained or loaded. Call fine_tune() or load_model() first.")
        
        results = []
        self.classification_model.eval()
        
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                inputs = self.tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    truncation=True,
                    padding=True,
                    max_length=512
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                outputs = self.classification_model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1)
                predictions = torch.argmax(logits, dim=1)
                
                for j, pred in enumerate(predictions):
                    results.append({
                        'prediction': 'fake' if pred.item() == 1 else 'real',
                        'confidence': probabilities[j][pred].item(),
                        'probabilities': {
                            'real': probabilities[j][0].item(),
                            'fake': probabilities[j][1].item()
                        }
                    })
        
        return results
    
    def save_model(self, output_dir: str):
        """Save fine-tuned model"""
        os.makedirs(output_dir, exist_ok=True)
        
        if self.classification_model:
            self.classification_model.save_pretrained(output_dir)
            self.tokenizer.save_pretrained(output_dir)
            logger.info(f"Model saved to {output_dir}")
        else:
            logger.warning("No classification model to save")
    
    def load_model(self, model_dir: str):
        """Load fine-tuned model"""
        try:
            logger.info(f"Loading fine-tuned model from {model_dir}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self.classification_model = AutoModelForSequenceClassification.from_pretrained(model_dir)
            self.classification_model.to(self.device)
            self.is_finetuned = True
            logger.info("✅ Fine-tuned model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def quantize_model(self):
        """Apply dynamic quantization for faster inference"""
        if not self.classification_model:
            logger.warning("No classification model to quantize")
            return
        
        logger.info("🔧 Applying dynamic quantization...")
        
        self.classification_model = torch.quantization.quantize_dynamic(
            self.classification_model,
            {torch.nn.Linear},
            dtype=torch.qint8
        )
        
        logger.info("✅ Model quantized successfully (expected 2-3x speedup)")
    
    def analyze_indian_context(self, text: str) -> Dict:
        """Analyze Indian context and cultural references"""
        text_lower = text.lower()
        
        # Indian political terms
        political_terms = [
            'modi', 'rahul gandhi', 'bjp', 'congress', 'aap', 'parliament', 'lok sabha',
            'rajya sabha', 'chief minister', 'governor', 'president', 'prime minister'
        ]
        
        # Indian cultural terms
        cultural_terms = [
            'bollywood', 'cricket', 'ipl', 'festival', 'diwali', 'holi', 'eid',
            'temple', 'mosque', 'gurudwara', 'church', 'hindu', 'muslim', 'sikh', 'christian'
        ]
        
        # Indian economic terms
        economic_terms = [
            'rupee', 'rbi', 'gst', 'demonetization', 'digital india', 'make in india',
            'startup india', 'skill india', 'jan dhan', 'aadhaar'
        ]
        
        # Indian geographic terms
        geographic_terms = [
            'kashmir', 'punjab', 'kerala', 'tamil nadu', 'maharashtra', 'gujarat',
            'bengal', 'assam', 'bihar', 'uttar pradesh', 'rajasthan', 'karnataka'
        ]
        
        analysis = {
            'political_context': sum(1 for term in political_terms if term in text_lower),
            'cultural_context': sum(1 for term in cultural_terms if term in text_lower),
            'economic_context': sum(1 for term in economic_terms if term in text_lower),
            'geographic_context': sum(1 for term in geographic_terms if term in text_lower),
            'indian_relevance_score': 0
        }
        
        # Calculate Indian relevance score
        total_context = sum(analysis.values()) - analysis['indian_relevance_score']
        analysis['indian_relevance_score'] = min(total_context / 10, 1.0)
        
        return analysis
