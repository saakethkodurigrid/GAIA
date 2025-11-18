# 🚀 CI/CD Setup Guide for GAIA Platform

## ✅ Files Created

The following files have been created for your CI/CD pipeline:

```
GAIA/
├── .github/
│   └── workflows/
│       └── ci-cd.yml                    # GitHub Actions workflow
├── backend/
│   ├── Dockerfile                       # Backend Docker image
│   └── .dockerignore                    # Backend Docker ignore
├── frontend/
│   ├── Dockerfile                       # Frontend Docker image
│   ├── nginx.conf                       # Nginx configuration
│   └── .dockerignore                    # Frontend Docker ignore
└── docker-compose.yml                   # Local development setup
```

---

## 📋 Next Steps to Complete Setup

### **Step 1: Create Docker Hub Account (if you don't have one)**

1. Go to https://hub.docker.com/
2. Sign up for a free account
3. Verify your email

### **Step 2: Create Docker Hub Access Token**

1. Log in to Docker Hub
2. Go to: **Account Settings** → **Security** → **Access Tokens**
3. Click **"New Access Token"**
4. Name: `GAIA_CICD_TOKEN`
5. Permissions: **Read & Write**
6. Click **"Generate"**
7. **COPY THE TOKEN** (you won't see it again!)

### **Step 3: Add GitHub Secrets**

1. Go to your GitHub repository
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add these two secrets:

**Secret 1:**
- Name: `DOCKER_HUB_USERNAME`
- Value: `your-dockerhub-username`

**Secret 2:**
- Name: `DOCKER_HUB_TOKEN`
- Value: `paste-your-access-token-here`

### **Step 4: Create cicddev Branch**

```bash
# Make sure you're in the GAIA directory
cd /Users/rabdin/Documents/GaiaPlat/GAIA

# Check current branch
git branch

# Create and switch to cicddev branch
git checkout -b cicddev

# Verify you're on cicddev
git branch
```

### **Step 5: Commit and Push CI/CD Files**

```bash
# Stage all new files
git add .github/
git add backend/Dockerfile
git add backend/.dockerignore
git add frontend/Dockerfile
git add frontend/nginx.conf
git add frontend/.dockerignore
git add docker-compose.yml
git add CI-CD-SETUP-GUIDE.md

# Commit
git commit -m "feat: Add CI/CD pipeline with Docker and GitHub Actions

- Add backend Dockerfile with multi-stage build
- Add frontend Dockerfile with nginx
- Add GitHub Actions workflow for lint, test, and build
- Add docker-compose for local development
- Configure pipeline to trigger on cicddev branch
"

# Push to remote (this will trigger the CI/CD pipeline!)
git push -u origin cicddev
```

### **Step 6: Watch the Pipeline Run**

1. Go to your GitHub repository
2. Click on **"Actions"** tab
3. You should see a new workflow run starting
4. Click on it to watch the progress

**Pipeline Stages:**
```
┌─────────────────┐
│  Backend Lint   │ → Checks Python code formatting
└────────┬────────┘
         ↓
┌─────────────────┐
│  Backend Test   │ → Runs smoke tests and unit tests
└────────┬────────┘
         ↓
┌─────────────────┐
│ Backend Build   │ → Builds and pushes Docker image
└─────────────────┘

┌─────────────────┐
│ Frontend Lint   │ → Checks TypeScript/React code
└────────┬────────┘
         ↓
┌─────────────────┐
│ Frontend Test   │ → Builds frontend and checks output
└────────┬────────┘
         ↓
┌─────────────────┐
│Frontend Build   │ → Builds and pushes Docker image
└─────────────────┘

         ↓
┌─────────────────┐
│    Summary      │ → Shows deployment information
└─────────────────┘
```

---

## 🧪 Test Locally Before Pushing

### **Test Backend Docker Build**
```bash
cd /Users/rabdin/Documents/GaiaPlat/GAIA/backend

# Build image
docker build -t gaia-backend:test .

# Run container
docker run -p 5000:5000 \
  -e DATABASE_URL="sqlite:///./test.db" \
  gaia-backend:test

# Test in another terminal
curl http://localhost:5000/health
```

### **Test Frontend Docker Build**
```bash
cd /Users/rabdin/Documents/GaiaPlat/GAIA/frontend

# Build image
docker build -t gaia-frontend:test .

# Run container
docker run -p 8080:80 gaia-frontend:test

# Open browser
open http://localhost:8080
```

### **Test Full Stack with Docker Compose**
```bash
cd /Users/rabdin/Documents/GaiaPlat/GAIA

# Build and start all services
docker-compose up --build

# Access services:
# - Backend API: http://localhost:5000
# - Frontend: http://localhost:80
# - API Docs: http://localhost:5000/docs

# Stop services
docker-compose down
```

---

## 📊 What Happens When You Push to cicddev

### **On Every Push/PR to cicddev:**

1. **Backend Lint** ✓
   - Black (code formatting)
   - Flake8 (linting)
   - Pylint (static analysis)

2. **Backend Test** ✓
   - Import smoke tests
   - Unit tests (if available)

3. **Backend Build** ✓ (only on push, not PR)
   - Build Docker image
   - Push to Docker Hub with tags:
     - `<username>/gaia-backend:cicddev`
     - `<username>/gaia-backend:cicddev-<commit-sha>`
     - `<username>/gaia-backend:latest`

4. **Frontend Lint** ✓
   - ESLint
   - TypeScript type checking

5. **Frontend Test** ✓
   - Build verification
   - Output validation

6. **Frontend Build** ✓ (only on push, not PR)
   - Build Docker image
   - Push to Docker Hub with tags:
     - `<username>/gaia-frontend:cicddev`
     - `<username>/gaia-frontend:cicddev-<commit-sha>`
     - `<username>/gaia-frontend:latest`

7. **Deployment Summary** ✓
   - Shows published images
   - Provides next steps

---

## 🎯 After Successful Pipeline

### **Pull Your Images**
```bash
# Pull backend
docker pull <your-username>/gaia-backend:latest

# Pull frontend
docker pull <your-username>/gaia-frontend:latest

# Run them
docker run -d -p 5000:5000 <your-username>/gaia-backend:latest
docker run -d -p 80:80 <your-username>/gaia-frontend:latest
```

### **Deploy to Production**

**Using Docker:**
```bash
# On your production server
docker pull <your-username>/gaia-backend:latest
docker pull <your-username>/gaia-frontend:latest
docker-compose up -d
```

**Using Kubernetes:**
```bash
# Update your k8s deployment with new image
kubectl set image deployment/gaia-backend \
  backend=<your-username>/gaia-backend:latest

kubectl set image deployment/gaia-frontend \
  frontend=<your-username>/gaia-frontend:latest
```

---

## 🔧 Customization

### **Change Trigger Branches**

Edit `.github/workflows/ci-cd.yml`:
```yaml
on:
  push:
    branches: [cicddev, main, develop]  # Add more branches
  pull_request:
    branches: [cicddev, main]
```

### **Change Docker Hub Organization**

Edit `.github/workflows/ci-cd.yml`:
```yaml
env:
  DOCKER_HUB_USERNAME: ${{ secrets.DOCKER_HUB_USERNAME }}
  BACKEND_IMAGE_NAME: your-org/gaia-backend   # Change here
  FRONTEND_IMAGE_NAME: your-org/gaia-frontend # Change here
```

### **Add More Tests**

Create test files in:
- Backend: `GAIA/backend/tests/test_*.py`
- Frontend: Add to `package.json` scripts

---

## 🐛 Troubleshooting

### **Pipeline Fails on Lint**
- Check the errors in the Actions log
- Run linters locally:
  ```bash
  cd GAIA/backend
  black --check .
  flake8 .
  ```

### **Docker Build Fails**
- Check Dockerfile syntax
- Test build locally first
- Check if all dependencies are in requirements.txt

### **Images Not Pushed to Docker Hub**
- Verify GitHub secrets are set correctly
- Check Docker Hub token has Read & Write permissions
- Ensure you're pushing to cicddev branch (not PR)

### **Health Check Fails**
- Ensure your app starts correctly
- Check port bindings
- Verify health endpoints work

---

## 📈 Monitoring Pipeline

### **View Pipeline Status**
- Badge: Add to README.md
  ```markdown
  ![CI/CD](https://github.com/<username>/<repo>/workflows/CI%2FCD%20Pipeline/badge.svg?branch=cicddev)
  ```

### **Pipeline Notifications**
- GitHub automatically emails on failures
- Set up Slack/Discord webhooks in repository settings

---

## 🎉 Success Indicators

✅ All checks pass in GitHub Actions  
✅ Images appear in Docker Hub  
✅ Images can be pulled and run  
✅ Health checks pass  
✅ Application works as expected  

---

## 📞 Next Steps After Setup

1. ✅ **Test locally** with docker-compose
2. ✅ **Push to cicddev** and watch pipeline
3. ✅ **Verify images** in Docker Hub
4. ✅ **Deploy to staging** environment
5. ✅ **Test deployed application**
6. ✅ **Merge to main** for production

---

## 🚀 Quick Command Reference

```bash
# Local testing
docker-compose up --build
docker-compose down

# Push to trigger pipeline
git add .
git commit -m "Your message"
git push origin cicddev

# View logs
docker logs gaia-backend
docker logs gaia-frontend

# Pull and run production images
docker pull <username>/gaia-backend:latest
docker pull <username>/gaia-frontend:latest
```

---

**Your CI/CD pipeline is ready! 🎊**

Push to cicddev branch and watch the magic happen! ✨

