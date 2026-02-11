#!/usr/bin/env python3
"""
Training Script for Fine-tuning IndicBERT on Misinformation Detection
Combines the data loader and enhanced IndicBERT processor for end-to-end training.
"""

import sys
import os
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import DataLoader
from enhanced_indicbert_processor import EnhancedIndicBERTProcessor
from advanced_ml_classifier import create_comprehensive_training_data
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train_indicbert_model(
    use_existing_dataset: bool = False,
    dataset_filename: str = "indian_misinformation.csv",
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    test_size: float = 0.2,
    val_size: float = 0.1,
    output_dir: str = "models/finetuned_indicbert",
    apply_quantization: bool = False
):
    """
    Complete training pipeline for IndicBERT fine-tuning
    
    Args:
        use_existing_dataset: Whether to use existing dataset file or create new one
        dataset_filename: Name of dataset file in datasets/ directory
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate for optimizer
        test_size: Fraction of data for test set
        val_size: Fraction of data for validation set
        output_dir: Directory to save fine-tuned model
        apply_quantization: Whether to apply quantization after training
    """
    
    logger.info("🚀 Starting IndicBERT Fine-tuning Pipeline")
    logger.info("=" * 70)
    
    # Step 1: Load Data
    logger.info("\n📊 Step 1: Loading Data")
    data_loader = DataLoader(datasets_dir='datasets')
    
    if use_existing_dataset and os.path.exists(f'datasets/{dataset_filename}'):
        logger.info(f"Loading existing dataset: {dataset_filename}")
        df = data_loader.load_csv(dataset_filename)
    else:
        logger.info("Creating new Indian context dataset...")
        # Combine synthetic dataset from advanced_ml_classifier
        synthetic_df = create_comprehensive_training_data()
        
        # Add Indian-specific examples
        indian_df = data_loader.create_indian_context_dataset()
        
        # Combine datasets
        df = pd.concat([synthetic_df, indian_df], ignore_index=True)
        
        # Save combined dataset
        data_loader.save_processed_dataset(df, "combined_training_data.csv")
        logger.info(f"Created and saved combined dataset with {len(df)} examples")
    
    # Step 2: Preprocess Data
    logger.info("\n🔧 Step 2: Preprocessing Data")
    df = data_loader.preprocess(
        df,
        clean_text=True,
        remove_duplicates=True,
        balance_classes=True  # Balance for better training
    )
    
    # Step 3: Split Data
    logger.info("\n✂️ Step 3: Splitting Data")
    train_df, val_df, test_df = data_loader.split_data(
        df,
        test_size=test_size,
        val_size=val_size
    )
    
    # Step 4: Initialize IndicBERT Processor
    logger.info("\n🧠 Step 4: Initializing IndicBERT Processor")
    processor = EnhancedIndicBERTProcessor(
        model_name="ai4bharat/indic-bert",
        num_labels=2
    )
    
    # Step 5: Fine-tune Model
    logger.info("\n🎓 Step 5: Fine-tuning IndicBERT")
    training_results = processor.fine_tune(
        train_texts=train_df['text'].tolist(),
        train_labels=train_df['label'].tolist(),
        val_texts=val_df['text'].tolist() if len(val_df) > 0 else None,
        val_labels=val_df['label'].tolist() if len(val_df) > 0 else None,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        output_dir=output_dir
    )
    
    logger.info(f"\n📊 Training Results:")
    logger.info(f"  Final Training Accuracy: {training_results['final_train_accuracy']:.4f}")
    if training_results['best_val_accuracy']:
        logger.info(f"  Best Validation Accuracy: {training_results['best_val_accuracy']:.4f}")
    
    # Step 6: Evaluate on Test Set
    if len(test_df) > 0:
        logger.info("\n📈 Step 6: Evaluating on Test Set")
        test_predictions = processor.predict_batch(test_df['text'].tolist())
        
        # Calculate test accuracy
        correct = sum(
            1 for i, pred in enumerate(test_predictions)
            if (pred['prediction'] == 'fake' and test_df.iloc[i]['label'] == 1) or
               (pred['prediction'] == 'real' and test_df.iloc[i]['label'] == 0)
        )
        test_accuracy = correct / len(test_df)
        
        logger.info(f"  Test Set Accuracy: {test_accuracy:.4f}")
        
        # Show some sample predictions
        logger.info("\n🔍 Sample Predictions:")
        for i in range(min(5, len(test_df))):
            text = test_df.iloc[i]['text']
            true_label = 'fake' if test_df.iloc[i]['label'] == 1 else 'real'
            pred = test_predictions[i]
            
            logger.info(f"\n  Text: {text[:80]}...")
            logger.info(f"  True: {true_label}, Predicted: {pred['prediction']}, Confidence: {pred['confidence']:.4f}")
    
    # Step 7: Apply Quantization (Optional)
    if apply_quantization:
        logger.info("\n⚡ Step 7: Applying Quantization")
        processor.quantize_model()
        # Save quantized model
        quantized_output_dir = output_dir + "_quantized"
        processor.save_model(quantized_output_dir)
        logger.info(f"Quantized model saved to {quantized_output_dir}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ Training Pipeline Completed Successfully!")
    logger.info(f"📁 Model saved to: {output_dir}")
    
    return processor, training_results


def test_trained_model(model_dir: str = "models/finetuned_indicbert"):
    """Test the trained model with sample inputs"""
    
    logger.info("🧪 Testing Trained Model")
    logger.info("=" * 70)
    
    # Load model
    processor = EnhancedIndicBERTProcessor()
    processor.load_model(model_dir)
    
    # Test samples
    test_samples = [
        "BREAKING: Modi government secretly selling India to China, conspiracy exposed!",
        "Government of India announces new infrastructure development plan",
        "EXPOSED: Vaccines contain microchips to control population",
        "According to Ministry of Health, COVID-19 cases declining nationwide",
        "URGENT: This miracle cure will shock you - doctors hate it!",
        "Supreme Court delivers verdict on constitutional matter",
    ]
    
    logger.info("\n📝 Test Predictions:\n")
    
    predictions = processor.predict_batch(test_samples)
    
    for text, pred in zip(test_samples, predictions):
        logger.info(f"Text: {text}")
        logger.info(f"Prediction: {pred['prediction'].upper()} (confidence: {pred['confidence']:.4f})")
        logger.info(f"Probabilities: Real={pred['probabilities']['real']:.4f}, Fake={pred['probabilities']['fake']:.4f}")
        logger.info("-" * 70)
    
    logger.info("\n✅ Testing Complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train IndicBERT for misinformation detection")
    parser.add_argument("--mode", type=str, default="train", choices=["train", "test"],
                       help="Mode: train or test")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--learning_rate", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--output_dir", type=str, default="models/finetuned_indicbert",
                       help="Output directory for model")
    parser.add_argument("--quantize", action="store_true", help="Apply quantization after training")
    parser.add_argument("--use_existing", action="store_true", 
                       help="Use existing dataset file")
    parser.add_argument("--dataset", type=str, default="indian_misinformation.csv",
                       help="Dataset filename")
    
    args = parser.parse_args()
    
    if args.mode == "train":
        processor, results = train_indicbert_model(
            use_existing_dataset=args.use_existing,
            dataset_filename=args.dataset,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            output_dir=args.output_dir,
            apply_quantization=args.quantize
        )
    else:
        test_trained_model(model_dir=args.output_dir)
