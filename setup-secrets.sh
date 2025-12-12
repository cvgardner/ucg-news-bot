#!/bin/bash

# UCG News Bot - GCP Secret Manager Setup Script
# This script helps you securely add your credentials to GCP Secret Manager

set -e

PROJECT_ID="${GCP_PROJECT_ID:-YOUR_PROJECT_ID}"

echo "========================================="
echo "UCG News Bot - Secret Setup"
echo "========================================="
echo "Project: ${PROJECT_ID}"
echo ""
echo "This script will help you create secrets in GCP Secret Manager."
echo "You'll be prompted to enter each credential."
echo ""
echo "IMPORTANT: Your credentials will be stored securely in Secret Manager"
echo "and will NOT be visible in logs or command history."
echo "========================================="
echo ""

# Set project
gcloud config set project "${PROJECT_ID}"

# Enable Secret Manager API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

echo ""
echo "Please enter your credentials when prompted."
echo "Press Ctrl+C to cancel at any time."
echo ""

# Discord Bot Token
echo "1/3: Discord Bot Token"
echo -n "Enter your Discord Bot Token: "
read -s DISCORD_BOT_TOKEN
echo ""

if [ -z "$DISCORD_BOT_TOKEN" ]; then
    echo "ERROR: Discord Bot Token cannot be empty"
    exit 1
fi

echo "$DISCORD_BOT_TOKEN" | gcloud secrets create DISCORD_BOT_TOKEN \
    --data-file=- \
    --replication-policy="automatic" 2>/dev/null || \
echo "$DISCORD_BOT_TOKEN" | gcloud secrets versions add DISCORD_BOT_TOKEN --data-file=-

echo "✓ Discord Bot Token saved"
echo ""

# X API Bearer Token
echo "2/3: X/Twitter API Bearer Token"
echo -n "Enter your X API Bearer Token: "
read -s X_API_BEARER
echo ""

if [ -z "$X_API_BEARER" ]; then
    echo "ERROR: X API Bearer Token cannot be empty"
    exit 1
fi

echo "$X_API_BEARER" | gcloud secrets create X_API_BEARER \
    --data-file=- \
    --replication-policy="automatic" 2>/dev/null || \
echo "$X_API_BEARER" | gcloud secrets versions add X_API_BEARER --data-file=-

echo "✓ X API Bearer Token saved"
echo ""

# YouTube API Key
echo "3/3: YouTube API Key"
echo -n "Enter your YouTube API Key: "
read -s YOUTUBE_API_KEY
echo ""

if [ -z "$YOUTUBE_API_KEY" ]; then
    echo "ERROR: YouTube API Key cannot be empty"
    exit 1
fi

echo "$YOUTUBE_API_KEY" | gcloud secrets create YOUTUBE_API_KEY \
    --data-file=- \
    --replication-policy="automatic" 2>/dev/null || \
echo "$YOUTUBE_API_KEY" | gcloud secrets versions add YOUTUBE_API_KEY --data-file=-

echo "✓ YouTube API Key saved"
echo ""

echo "========================================="
echo "Secrets Setup Complete!"
echo "========================================="
echo ""
echo "All secrets have been securely stored in Secret Manager."
echo ""
echo "Next step: Run ./deploy.sh to deploy your bot"
echo "========================================="
