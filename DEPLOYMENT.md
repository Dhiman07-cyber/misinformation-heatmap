# Zero-Cost Production Deployment Guide

This guide explains how to deploy the Misinformation Heatmap using a 100% free, production-grade architecture.

## Architecture (Zero-Egress Setup)

*   **Backend & Database**: Hugging Face Spaces (Docker Space)
    *   *Why?* By running both the Python API and a Local SQLite database on the same Hugging Face container, we achieve **0 GB of database egress**.
    *   *Retention:* A native Python loop automatically cleans up data older than 24 hours, ensuring the ephemeral disk never fills up.
*   **Frontend**: Netlify (Global CDN, fast static serving)

---

## 🌐 Live Hosted Links
*   **Frontend Web App (Netlify):** [https://misinformation-heatmap.netlify.app](https://misinformation-heatmap.netlify.app)
*   **Backend API (Hugging Face):** [https://huggingface.co/spaces/Ndg07/heatmap](https://huggingface.co/spaces/Ndg07/heatmap)

---

## 🚀 Deployment Steps

### 1. Backend & Database (Hugging Face Spaces)
1. Create a free account at [Hugging Face](https://huggingface.co).
2. Click **New Space** -> Choose **Docker** as the Space SDK -> Choose **Blank** deployment.
3. Upload the entire project repository to the Space.
4. **Important**: Change the uploaded `Dockerfile.deploy` to `Dockerfile`.
5. In your Space settings **Variables and Secrets**, ensure `MODE=local`. Do **NOT** set a `DATABASE_URL`.
6. The Space will automatically build, boot, create a local SQLite database, and begin the 24-hour ingestion cycle automatically!

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

## ⏪ How to Migrate to Postgres (Optional)

If you ever need permanent, long-term storage beyond the 24-hour window, the system is designed with a **seamless fallback adapter**.

**To upgrade to Cloud Postgres (e.g., Supabase / Neon):**
1. Set the `DATABASE_URL` environment variable locally or in Hugging Face secrets.
2. Run your server normally: `uvicorn server:app --reload`
3. The system will automatically detect the `DATABASE_URL` and instantly switch from local SQLite to your Cloud Postgres provider.

It is 100% safely reversible at any time!
