# Railway Deployment Guide

## Prerequisites
- GitHub account with repo: https://github.com/Ashok7890-reddy/caps-final.git
- Railway account (sign up at https://railway.app)

## Step-by-Step Deployment

### 1. Push Code to GitHub
```bash
git add .
git commit -m "Add Railway deployment config"
git push origin main
```

### 2. Create Railway Project

1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Choose `Ashok7890-reddy/caps-final`
5. Railway will auto-detect the configuration

### 3. Add PostgreSQL Database

1. In your Railway project, click "+ New"
2. Select "Database" → "PostgreSQL"
3. Railway will provision a PostgreSQL instance
4. Database credentials are auto-injected as environment variables

### 4. Add Redis

1. Click "+ New" again
2. Select "Database" → "Redis"
3. Redis connection URL is auto-injected

### 5. Configure Environment Variables

In Railway project settings, add these variables:

**Backend Service:**
```
ENVIRONMENT=production
DB_HOST=${{Postgres.PGHOST}}
DB_PORT=${{Postgres.PGPORT}}
DB_NAME=${{Postgres.PGDATABASE}}
DB_USER=${{Postgres.PGUSER}}
DB_PASSWORD=${{Postgres.PGPASSWORD}}
REDIS_HOST=${{Redis.REDIS_HOST}}
REDIS_PORT=${{Redis.REDIS_PORT}}
REDIS_PASSWORD=${{Redis.REDIS_PASSWORD}}
PORT=8000
PYTHONUNBUFFERED=1
```

**Frontend Service (if deploying separately):**
```
VITE_API_URL=https://your-backend-url.railway.app/api/v1
NODE_ENV=production
```

### 6. Deploy

Railway will automatically:
- Install Python dependencies from `backend/requirements.txt`
- Install Node.js dependencies from `frontend/package.json`
- Build the frontend with `npm run build`
- Start the backend with `uvicorn`

### 7. Get Your Live URL

Once deployed, Railway provides:
- Backend API: `https://your-app-name.railway.app`
- API Docs: `https://your-app-name.railway.app/api/v1/docs`

### 8. Serve Frontend

**Option A: Serve from Backend (Recommended)**
Update `backend/main.py` to serve the built frontend:

```python
from fastapi.staticfiles import StaticFiles

# Add after creating the app
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

**Option B: Deploy Frontend Separately on Vercel**
1. Go to https://vercel.com
2. Import your GitHub repo
3. Set root directory to `frontend`
4. Add environment variable: `VITE_API_URL=https://your-backend.railway.app/api/v1`
5. Deploy

## Monitoring

- View logs in Railway dashboard
- Check health: `https://your-app.railway.app/health`
- API docs: `https://your-app.railway.app/api/v1/docs`

## Troubleshooting

**Build fails:**
- Check Railway logs for errors
- Verify `requirements.txt` and `package.json` are correct

**Database connection fails:**
- Ensure PostgreSQL service is running
- Check environment variables are properly linked

**Frontend not loading:**
- Verify build completed successfully
- Check static file serving is configured

## Cost Estimate

Railway free tier includes:
- $5 credit per month
- Enough for small demos and testing
- Upgrade to hobby plan ($5/month) for production use

## Updates

To deploy updates:
```bash
git add .
git commit -m "Your update message"
git push origin main
```

Railway auto-deploys on every push to main branch.

---

**Live Demo URL:** Will be available after deployment at:
`https://caps-final-production.up.railway.app` (or similar)
