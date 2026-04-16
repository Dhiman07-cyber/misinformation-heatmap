# Zero-Cost Production Deployment Guide

This guide explains how to deploy the Misinformation Heatmap using a 100% free, production-grade architecture.

## Architecture

*   **Frontend**: Netlify (Global CDN, fast static serving)
*   **Backend**: Hugging Face Spaces (Docker Space, provides 16GB free RAM needed for PyTorch/Transformers)
*   **Database**: Supabase (Free tier PostgreSQL for persistent storage)

---

## 🚀 Deployment Steps

### 1. Database (Supabase)
1. Create a free account at [Supabase](https://supabase.com).
2. Create a new project.
3. Once the database is ready, go to the SQL Editor.
4. Copy the contents of `supabase_schema.sql` (found in this repository root) and run it to create the necessary tables.
5. Go to **Project Settings > Database** and copy the **Connection String (URI)**.
   *(Make sure to replace `[YOUR-PASSWORD]` with your actual database password).*

### 2. Backend (Hugging Face Spaces)
1. Create a free account at [Hugging Face](https://huggingface.co).
2. Click **New Space** -> Choose **Docker** as the Space SDK -> Choose **Blank** deployment.
3. Upload the entire project repository to the Space (you can link it via GitHub or upload files directly).
4. **Important**: Change the uploaded `Dockerfile.deploy` to `Dockerfile`.
5. Go to your Space settings and add the following **Secret** (Environment Variable):
   *   `DATABASE_URL`: *(Paste the Supabase connection string you copied in Step 1)*
6. The Space will automatically build and start. Note the URL of your Space (e.g., `https://username-spacename.hf.space`).

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

**To go back to Local SQLite mode:**
1. Do **NOT** set the `DATABASE_URL` environment variable locally.
2. Run your server normally: `uvicorn server:app --reload`
3. The system will automatically detect the missing `DATABASE_URL` and instantly fall back to using the local `data/enhanced_fake_news.db` SQLite file.

It is 100% safely reversible at any time!
