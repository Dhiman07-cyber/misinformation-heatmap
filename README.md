# 🛡️ Misinformation Heatmap

A comprehensive AI-powered system for detecting misinformation in Indian media using advanced machine learning, IndicBERT, satellite verification, and fact-checking integration.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

---

## 📸 Screenshots & Demo

### Main Homepage
> Overview of the whole website

![Analysis Preview](docs/media-assets/Home.png)
*Coming Soon: Add your analysis interface screenshot here*

### Main Dashboard
> Real-time misinformation detection dashboard with live statistics

![Dashboard Preview](docs/media-assets/Dashboard.png)
*Coming Soon: Add your dashboard screenshot here*

### Interactive India Heatmap
> Geographic visualization of misinformation distribution across Indian states

![Heatmap Preview](docs/media-assets/Map.png)
*Coming Soon: Add your heatmap screenshot here*


### 🎥 Video Demo
> Full system walkthrough and feature demonstration

[![Video Demo](https://img.shields.io/badge/▶️-Watch%20Demo-red?style=for-the-badge&logo=youtube)](https://youtube.com/your-video-link)
*Coming Soon: Add your demo video link here*

---

## 🚀 Key Features

- **Advanced AI Analysis**: 5-model ensemble ML classifier (91.0% accuracy, 0.973 ROC-AUC, 91.0% CV F1)
- **IndicBERT Integration**: Indian language embeddings for cultural context
- **Deterministic Detection**: Removed all random simulations for reproducible results
- **Real-time Processing**: 34+ Indian news sources with live RSS ingestion
- **Interactive Visualization**: State-wise heatmap with geographic distribution
- **Multi-layer Verification**: Fact-checking database, satellite geocoding, source credibility
- **Indian Context**: Specialized for Hinglish, regional languages, WhatsApp forwards
- **940-Example Dataset**: Vibrant misinformation dataset (477 fake / 463 real) with 6 source types
- **RESTful API**: Comprehensive API with Swagger documentation
- **Docker Support**: Easy deployment with Docker Compose
- **Scalable Architecture**: Handles high-volume data ingestion

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/NayandG07/misinformation-heatmap.git
cd misinformation-heatmap
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables (Optional)
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your API keys (optional)
# GOOGLE_MAPS_API_KEY=your_google_maps_api_key
# OPENAI_API_KEY=your_openai_key
```

### 4. Initialize Database (First Time Only)
```bash
cd backend
python init_db.py
```

### 5. Run the System
```bash
# From backend directory
python main_application.py

# Or from project root
python backend/main_application.py
```

The system will be available at **http://localhost:8080**

---

## 🌐 Deployment

### Docker Deployment (Recommended)

```bash
# Development mode
docker-compose up --build

# Production mode
docker-compose -f docker-compose.prod.yml up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f app

# Restart services
docker-compose restart
```

### Manual Deployment

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
cd backend
python init_db.py

# 3. Run application
python main_application.py

# 4. Access at http://localhost:8000
```

### Production Deployment

```bash
# Using Gunicorn (recommended for production)
cd backend
gunicorn main_application:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -

# Or use the provided scripts
./scripts/run_local.sh              # Local development
./scripts/docker-dev.sh start       # Docker development
./scripts/docker-prod.sh deploy     # Docker production
```

---

## 📚 Documentation

Complete documentation is available in the [`docs/`](docs/) folder:

- **[📖 Documentation Index](docs/README.md)** - Complete documentation guide
- **[🏗️ Project Structure](docs/PROJECT_STRUCTURE.md)** - Detailed project organization
- **[🔧 Backend Architecture](docs/BACKEND_ARCHITECTURE.md)** - System design and components
- **[🤖 ML Model Documentation](docs/ML_MODEL_DOCUMENTATION.md)** - AI model specifications
- **[🛡️ System Overview](docs/SYSTEM_OVERVIEW.md)** - Complete feature overview
- **[🛠️ Scripts Guide](scripts/README.md)** - Development and deployment scripts

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **IndicBERT**: [AI4Bharat](https://ai4bharat.org/) for Indian language models
- **News Sources**: 30+ Indian news outlets for real-time data
- **Fact-Checkers**: [Alt News](https://www.altnews.in/), [Boom Live](https://www.boomlive.in/), [WebQoof](https://www.thequint.com/news/webqoof) for verification
- **Open Source Community**: Built with FastAPI, scikit-learn, PyTorch, and more
- **Contributors**: Thanks to all contributors who have helped improve this project

---

**🛡️ Built for combating misinformation in Indian media**

**Made with ❤️ for a more informed India**

---

*Last Updated: March 11, 2026*
