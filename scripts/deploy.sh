#!/bin/bash
# Deploy Motif to Cloud Run
set -e

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="motif"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Building image..."
gcloud builds submit --tag "${IMAGE}" .

echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 5

echo "Done! Service URL:"
gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format 'value(status.url)'
