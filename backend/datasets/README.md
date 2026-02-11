# Datasets Directory

This directory contains datasets for training and evaluating the misinformation detection model.

## Supported Formats
- CSV files with columns: `text`, `label`, `source` (optional)
- JSON files with format: `[{"text": "...", "label": 0/1, "source": "..."}]`

## Dataset Structure
- `label`: 0 = legitimate news, 1 = fake/misinformation
- `text`: The news article content (title + body)
- `source`: Optional source attribution

## Recommended Datasets
1. **LIAR Dataset**: Political statements fact-checking
2. **ISOT Fake News Dataset**: Real and fake news articles
3. **FakeNewsNet**: Social media fake news
4. **Indian Context**: Custom datasets focusing on Indian media

## Usage
Place your dataset files here and use the `data_loader.py` utility to load them for training.
