# Deployment Guide

This guide deploys the IRIS Molecular Reversal application with:

- **Frontend** → Vercel (free tier)
- **Backend** → Render (free tier with persistent disk)

The Python scientific pipeline is untouched. All statistics, reproducibility audits, and TCGA/GDC downloads run on the Render container exactly as they do locally.

## Prerequisites

- A GitHub account
- A [Render](https://render.com) account (free)
- A [Vercel](https://vercel.com) account (free)

## Step 1 — Push to GitHub

```sh
cd /path/to/ISEF-Althea
git init
git add -A
git commit -m "Initial commit: IRIS Molecular Reversal"
```

Create a **private** repository on GitHub (e.g. `iris-molecular-reversal`), then:

```sh
git remote add origin https://github.com/YOUR_USERNAME/iris-molecular-reversal.git
git branch -M main
git push -u origin main
```

## Step 2 — Deploy Backend on Render

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**.
2. Connect your GitHub repository.
3. Render will auto-detect the `render.yaml` blueprint. Alternatively, configure manually:

| Setting | Value |
|---|---|
| **Name** | `iris-backend` |
| **Root Directory** | `backend` |
| **Runtime** | Docker |
| **Dockerfile Path** | `backend/Dockerfile` |
| **Plan** | Free |

4. Add a **Disk**:
   - Mount Path: `/data`
   - Size: 10 GB

5. Add **Environment Variables**:

| Variable | Value |
|---|---|
| `IRIS_DATA_DIR` | `/data` |
| `PYTHONUNBUFFERED` | `1` |
| `IRIS_CORS_ORIGINS` | `https://YOUR-APP.vercel.app` (update after Vercel deploy) |

6. Click **Create Web Service**. Wait for the build (~2–4 min).

7. **Verify**: visit `https://iris-backend-XXXX.onrender.com/api/v1/health`. You should see:
   ```json
   {"status": "ok", "version": "0.1.0"}
   ```

> **Note**: Render free tier spins down after 15 min of inactivity. The first request after idle takes ~30s to cold-start. Paid plans ($7/mo) eliminate this.

## Step 3 — Deploy Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → Import your GitHub repository.
2. Set:

| Setting | Value |
|---|---|
| **Root Directory** | `frontend` |
| **Framework** | Next.js (auto-detected) |
| **Build Command** | `next build` (default) |
| **Output Directory** | `.next` (default) |

3. Add **Environment Variable**:

| Variable | Value |
|---|---|
| `BACKEND_URL` | `https://iris-backend-XXXX.onrender.com` (your Render URL) |

4. Click **Deploy**. Wait for the build (~1–2 min).

5. After deploy, copy your Vercel URL (e.g. `https://iris-molecular-reversal.vercel.app`).

## Step 4 — Connect CORS

1. Go back to Render → your `iris-backend` service → **Environment**.
2. Update `IRIS_CORS_ORIGINS` to your Vercel URL:
   ```
   https://iris-molecular-reversal.vercel.app
   ```
   For multiple origins, use commas:
   ```
   https://iris-molecular-reversal.vercel.app,https://custom-domain.com
   ```
3. Render will auto-redeploy.

## Step 5 — Verify End-to-End

1. Open your Vercel URL in a browser.
2. Enter `breast cancer` and click **Analyze Cancer**.
3. The frontend proxies API calls to Render. You should see live progress as the backend downloads TCGA data and runs the analysis.

## Architecture (Production)

```
Browser → Vercel (Next.js SSR/SSG)
              │
              └─ /api/* rewrites (next.config.ts)
                    │
                    └─→ Render (FastAPI + persistent /data disk)
                              ├─ GDC downloads cached at /data/cache/
                              ├─ Analysis outputs at /data/analyses/
                              └─ Single-worker thread pool
```

## Environment Variables Summary

| Variable | Where | Purpose |
|---|---|---|
| `BACKEND_URL` | Vercel | Next.js rewrite target for `/api/*` proxy |
| `IRIS_DATA_DIR` | Render | Persistent data root (`/data`) |
| `IRIS_CORS_ORIGINS` | Render | Comma-separated allowed frontend origins |
| `PYTHONUNBUFFERED` | Render | Real-time Python log output |
| `PORT` | Render (auto-set) | Dynamic port binding |

## Local Development (Unchanged)

The local workflow is completely unaffected:

```sh
python3.11 -m venv .venv311
.venv311/bin/pip install -r backend/requirements.lock.txt
npm ci --prefix frontend

# Terminal 1: backend
.venv311/bin/python -m uvicorn app.api.main:app --app-dir backend --host 127.0.0.1 --port 8000

# Terminal 2: frontend
npm run dev --prefix frontend
```

## Troubleshooting

| Problem | Fix |
|---|---|
| CORS errors in browser console | Verify `IRIS_CORS_ORIGINS` on Render matches your Vercel URL exactly (with `https://`, no trailing slash) |
| 502/504 on Vercel | Backend may be cold-starting on Render free tier; wait 30s and retry |
| Analysis times out | Render free tier has no request timeout for background workers; check Render logs for errors |
| Disk full | Increase disk size in Render dashboard or clear old analyses from `/data/analyses/` |
