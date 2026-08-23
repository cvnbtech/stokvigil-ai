#!/bin/bash
# ====================================================================
# Deployment Script for Google Cloud Run (Free Tier)
# Package ID: com.app.stokvigil
# ====================================================================

set -e

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="asia-south1" # Mumbai region for low latency to Indian markets
SERVICE_NAME="stokvigil-backend"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: Google Cloud project ID not set. Run 'gcloud config set project <PROJECT_ID>' first."
    exit 1
fi

echo "🚀 Building and submitting Docker image to Artifact Registry..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .

echo "📦 Deploying $SERVICE_NAME to Google Cloud Run (Region: $REGION)..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --min-instances 0 \
    --max-instances 3 \
    --update-env-vars ENVIRONMENT=production

echo "✅ Deployment successful! Service URL:"
gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)'
