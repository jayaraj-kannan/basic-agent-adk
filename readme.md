# Deploying Your ADK Agent to Google Cloud Run

Follow these steps to deploy your ADK (Agent Development Kit) application to Google Cloud Run.

## Prerequisites

1. **Install the Google Cloud CLI**: If you haven't already, install the `gcloud` CLI tool.
2. **Login to Google Cloud**: Authenticate with your Google account.
   ```bash
   gcloud auth login
   ```
3. **Set your Google Cloud Project**: Replace `[PROJECT_ID]` with your actual project ID (e.g., `12345`).
   ```bash
   gcloud config set project [PROJECT_ID]
   ```

## Deployment Steps

Before deploying, set up the required environment variables. Replace the bracketed placeholders (`[...]`) with your specific configuration:

```bash
# Set your deployment variables
export GOOGLE_CLOUD_PROJECT="[PROJECT_ID]"
export GOOGLE_CLOUD_LOCATION="[REGION]"    # e.g., us-central1
export GOOGLE_API_KEY="[API_KEY]"          # Your Google API Key
export AGENT_PATH="./[agent-folder-name]"  # e.g., ./basic_agent
export SERVICE_NAME="[service-name]"       # e.g., my-basic-agent
export APP_NAME="[app-name]"               # e.g., My Agent UI

# Deploy the ADK app to Cloud Run
adk deploy cloud_run \
    --project=$GOOGLE_CLOUD_PROJECT \
    --region=$GOOGLE_CLOUD_LOCATION \
    --service_name=$SERVICE_NAME \
    --app_name=$APP_NAME \
    --with_ui \
    $AGENT_PATH \
    -- \
    --set-env-vars="GOOGLE_API_KEY=$GOOGLE_API_KEY,GOOGLE_GENAI_USE_ENTERPRISE=0" \
    --allow-unauthenticated
```

> **Note**: This command configures the service to allow unauthenticated access (`--allow-unauthenticated`). For production, consider using tighter security controls and storing your API key in Google Cloud Secret Manager instead of passing it as an environment variable.
