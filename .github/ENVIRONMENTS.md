# GitHub Environments Configuration
# This file documents the required GitHub environment setup for the CI/CD pipeline

## Environment: dev
- **Protection rules**: None (auto-deploy)
- **Deployment branches**: development, feature/*
- **Secrets**: Inherited from repository

## Environment: staging
- **Protection rules**: None (auto-deploy)
- **Deployment branches**: staging
- **Secrets**: Inherited from repository

## Environment: prd
- **Protection rules**:
  - Required reviewers: 2
  - Wait timer: 10 minutes (optional)
- **Deployment branches**: main only
- **Secrets**: Production-specific secrets (if different)

## Setup Instructions

### 1. Navigate to Repository Settings
Go to: Settings → Environments

### 2. Create `dev` Environment
- Click "New environment"
- Name: `dev`
- No protection rules needed

### 3. Create `staging` Environment
- Click "New environment"
- Name: `staging`
- No protection rules needed (or add reviewers if desired)

### 4. Create `prd` Environment
- Click "New environment"
- Name: `prd`
- Enable protection rules:
  - Required reviewers: Add 2 team members
  - Wait timer: 10 minutes (optional)
  - Deployment branches: Selected branches -> main

### 5. Environment URLs (Auto-configured by workflow)
The workflow automatically sets environment URLs:
- dev: `https://<aks-cluster>.dev.qnt9.io`
- staging: `https://<aks-cluster>.staging.qnt9.io`
- prd: `https://<aks-cluster>.prd.qnt9.io`
