#!/bin/bash

# UCG News Bot - GCP Cloud Run Job Deployment Script
# This script deploys the bot as a Cloud Run Job triggered by Cloud Scheduler

set -e  # Exit on error

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-YOUR_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
JOB_NAME="ucg-news-bot"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}"
SCHEDULER_NAME="ucg-news-bot-schedule"
BUCKET_NAME="${GCS_BUCKET_NAME:-${PROJECT_ID}-ucg-news-bot}"

echo "========================================="
echo "UCG News Bot - GCP Deployment"
echo "========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Job: ${JOB_NAME}"
echo "Bucket: ${BUCKET_NAME}"
echo "========================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI not found. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "ERROR: Not logged in to gcloud. Run: gcloud auth login"
    exit 1
fi

# Set project
echo "Setting project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    storage.googleapis.com

# Create GCS bucket for database persistence
echo "Setting up Cloud Storage bucket..."
if gsutil ls -b "gs://${BUCKET_NAME}" &> /dev/null; then
    echo "✓ Bucket ${BUCKET_NAME} already exists"
else
    echo "Creating bucket ${BUCKET_NAME}..."
    gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_NAME}"
    echo "✓ Bucket created successfully"
fi

# Build container image
echo "Building container image..."
gcloud builds submit --tag "${IMAGE_NAME}"

# Check if Cloud Run Job already exists
if gcloud run jobs describe "${JOB_NAME}" --region="${REGION}" &> /dev/null; then
    echo "Updating existing Cloud Run Job..."
    gcloud run jobs update "${JOB_NAME}" \
        --image="${IMAGE_NAME}" \
        --region="${REGION}" \
        --max-retries=1 \
        --task-timeout=5m \
        --set-env-vars="CHANNEL_NAME=ucg-news-bot,UCG_EN_X_ID=1798233243185303552,TWITTER_USERNAME=ucg_en,YOUTUBE_CHANNEL_ID=UC0WwX8aoBWRAdQ2bM-FD8TQ,ULTRAMAN_COLUMN_URL=https://ultraman-cardgame.com/page/us/column/column-list,ULTRAMAN_NEWS_URL=https://ultraman-cardgame.com/page/us/news/news-list,DATABASE_PATH=/data/bot_data.db,LOG_LEVEL=INFO,GCS_BUCKET_NAME=${BUCKET_NAME}" \
        --set-secrets="DISCORD_BOT_TOKEN=DISCORD_BOT_TOKEN:latest,X_API_BEARER=X_API_BEARER:latest,YOUTUBE_API_KEY=YOUTUBE_API_KEY:latest"
else
    echo "Creating new Cloud Run Job..."
    gcloud run jobs create "${JOB_NAME}" \
        --image="${IMAGE_NAME}" \
        --region="${REGION}" \
        --max-retries=1 \
        --task-timeout=5m \
        --set-env-vars="CHANNEL_NAME=ucg-news-bot,UCG_EN_X_ID=1798233243185303552,TWITTER_USERNAME=ucg_en,YOUTUBE_CHANNEL_ID=UC0WwX8aoBWRAdQ2bM-FD8TQ,ULTRAMAN_COLUMN_URL=https://ultraman-cardgame.com/page/us/column/column-list,ULTRAMAN_NEWS_URL=https://ultraman-cardgame.com/page/us/news/news-list,DATABASE_PATH=/data/bot_data.db,LOG_LEVEL=INFO,GCS_BUCKET_NAME=${BUCKET_NAME}" \
        --set-secrets="DISCORD_BOT_TOKEN=DISCORD_BOT_TOKEN:latest,X_API_BEARER=X_API_BEARER:latest,YOUTUBE_API_KEY=YOUTUBE_API_KEY:latest"
fi

# Create/Update Cloud Scheduler job
echo "Setting up Cloud Scheduler..."

# Check if scheduler job exists
if gcloud scheduler jobs describe "${SCHEDULER_NAME}" --location="${REGION}" &> /dev/null; then
    echo "Updating existing Cloud Scheduler job..."
    gcloud scheduler jobs update http "${SCHEDULER_NAME}" \
        --location="${REGION}" \
        --schedule="5/15 * * * *" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com"
else
    echo "Creating new Cloud Scheduler job..."
    gcloud scheduler jobs create http "${SCHEDULER_NAME}" \
        --location="${REGION}" \
        --schedule="1/15 * * * *" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
        --time-zone="Etc/UTC"
fi

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Add secrets to Secret Manager:"
echo "   gcloud secrets create DISCORD_BOT_TOKEN --data-file=-"
echo "   gcloud secrets create X_API_BEARER --data-file=-"
echo "   gcloud secrets create YOUTUBE_API_KEY --data-file=-"
echo ""
echo "2. Test the job manually:"
echo "   gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo ""
echo "3. View logs:"
echo "   gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}\" --limit=50"
echo ""
echo "4. The job will run automatically every 15 minutes via Cloud Scheduler"
echo "========================================="
