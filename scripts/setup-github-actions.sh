#!/bin/bash
# Setup script for GitHub Actions Azure authentication
# Run this script to create service principal and federated credentials

set -e

echo "🔐 GAIA GitHub Actions Setup Script"
echo "===================================="
echo ""

# Azure Configuration
SUBSCRIPTION_ID="dab771f2-8670-4bf4-8067-ea813decb669"
RESOURCE_GROUP="ai-ta-2"
TENANT_ID="eccbc9a0-56ca-4467-bacd-c7b7d36ef395"
APP_NAME="gaia-github-actions"
GITHUB_ORG="saakethkodurigrid"
GITHUB_REPO="GAIA"
BRANCH="dev_v1"

echo "Configuration:"
echo "  Subscription ID: $SUBSCRIPTION_ID"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Tenant ID: $TENANT_ID"
echo "  App Name: $APP_NAME"
echo "  GitHub Repo: $GITHUB_ORG/$GITHUB_REPO"
echo "  Branch: $BRANCH"
echo ""

# Check if logged in
echo "Checking Azure login..."
az account show > /dev/null 2>&1 || {
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
}

# Set subscription
echo "Setting subscription..."
az account set --subscription "$SUBSCRIPTION_ID"

# Check if app already exists
APP_ID=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv 2>/dev/null || echo "")

if [ -z "$APP_ID" ] || [ "$APP_ID" == "null" ]; then
    echo "Creating Azure App Registration..."
    APP_ID=$(az ad app create \
        --display-name "$APP_NAME" \
        --query "appId" -o tsv)
    echo "✅ App created: $APP_ID"
else
    echo "✅ App already exists: $APP_ID"
fi

# Create service principal if it doesn't exist
SP_ID=$(az ad sp list --filter "appId eq '$APP_ID'" --query "[0].id" -o tsv 2>/dev/null || echo "")

if [ -z "$SP_ID" ] || [ "$SP_ID" == "null" ]; then
    echo "Creating Service Principal..."
    az ad sp create --id "$APP_ID" > /dev/null
    echo "✅ Service Principal created"
    sleep 5  # Wait for propagation
else
    echo "✅ Service Principal already exists"
fi

# Assign Contributor role to resource group
echo "Assigning Contributor role to resource group..."
az role assignment create \
    --assignee "$APP_ID" \
    --role contributor \
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
    2>/dev/null || echo "⚠️  Role assignment may already exist"

# Assign AcrPush role to container registry
echo "Assigning AcrPush role to container registry..."
az role assignment create \
    --assignee "$APP_ID" \
    --role AcrPush \
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerRegistry/registries/acrgaia" \
    2>/dev/null || echo "⚠️  Role assignment may already exist"

# Create federated credential for GitHub Actions
echo "Creating Federated Credential for GitHub Actions..."
SUBJECT="repo:$GITHUB_ORG/$GITHUB_REPO:ref:refs/heads/$BRANCH"

az ad app federated-credential create \
    --id "$APP_ID" \
    --parameters "{
        \"name\": \"github-actions-$BRANCH\",
        \"issuer\": \"https://token.actions.githubusercontent.com\",
        \"subject\": \"$SUBJECT\",
        \"audiences\": [\"api://AzureADTokenExchange\"]
    }" 2>/dev/null && echo "✅ Federated credential created" || echo "⚠️  Federated credential may already exist"

echo ""
echo "===================================="
echo "✅ Setup Complete!"
echo ""
echo "📋 Add this secret to GitHub:"
echo ""
echo "Repository: https://github.com/$GITHUB_ORG/$GITHUB_REPO/settings/secrets/actions"
echo ""
echo "Secret Name: AZURE_CLIENT_ID"
echo "Secret Value: $APP_ID"
echo ""
echo "===================================="

