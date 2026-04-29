# Zero-Cost Production Deployment Guide

This guide explains how to deploy the Misinformation Heatmap using a 100% free, production-grade architecture.

## Architecture

*   **Frontend**: Netlify (Global CDN, fast static serving)
*   **Backend**: Hugging Face Spaces (Docker Space, provides 16GB free RAM needed for PyTorch/Transformers)
*   **Database**: Local SQLite (Embedded in Hugging Face Docker, completely eliminating network egress costs)

---

## 🚀 Deployment Steps

### 1. Database (Local SQLite)
No cloud database setup is required. The system is configured to autonomously build and manage an internal SQLite file (`data/enhanced_fake_news.db`) on the Hugging Face server. A native Python script runs an auto-cleaning sequence every cycle to delete data older than 24 hours, ensuring the disk stays lean permanently.

### 2. Backend (Hugging Face Spaces)
1. Create a free account at [Hugging Face](https://huggingface.co).
2. Click **New Space** -> Choose **Docker** as the Space SDK -> Choose **Blank** deployment.
3. Upload the entire project repository to the Space (you can link it via GitHub or upload files directly).
4. **Important**: Change the uploaded `Dockerfile.deploy` to `Dockerfile`.
5. The Space will automatically build and start using Local Mode. Note the URL of your Space (e.g., `https://username-spacename.hf.space`).

### 3. Frontend (Netlify)
1. Open `frontend/index.html`, `frontend/dashboard.html`, and `map/enhanced-india-heatmap.html`.
2. Find the `<script>` block near the bottom of each file and replace `[your-huggingface-space-name]` with your actual HF Space ID in the `API_BASE` variable.
3. Create a free account at [Netlify](https://netlify.com).
4. Drag and drop the `frontend` folder (or link your Git repository and set the publish directory to `/`). Note: Since `map/` is outside `frontend/`, if you want to deploy *everything*, set the root folder as the publish directory, but ideally, restructure them into a single `public/` directory for Netlify. *(For a quick test, you can just zip the repo and upload it to Netlify, serving the root).*

### 4. Keep-Alive Workaround (Cron-job.org)
Hugging Face free Spaces sleep after 48 hours of inactivity.
1. Create a free account at [Cron-job.org](https://cron-job.org).
2. Create a new cron job pointing to your Hugging Face space URL: `https://username-spacename.hf.space/health`
3. Set the schedule to ping every **12 hours**. This keeps the backend permanently active.

---

## ⏪ How to Revert (Zero-Friction Fallback)

If the deployment fails, gets corrupted, or you just want to run the system locally again, you don't need to rewrite any code! The system is designed with a **seamless fallback adapter**.

**To use Cloud Postgres (Optional):**
1. Set the `DATABASE_URL` environment variable locally or in HF secrets.
2. The system will automatically detect the `DATABASE_URL` and instantly start writing to your external cloud database using the same data schemas.

It is 100% safely reversible at any time!
