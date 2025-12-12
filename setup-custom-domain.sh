#!/bin/bash

# Custom Domain Setup Script for Azure Static Web App
# Usage: ./setup-custom-domain.sh <domain-name>
# Example: ./setup-custom-domain.sh app.gaia.com

set -e

DOMAIN_NAME="${1}"
RESOURCE_GROUP="ai-ta-2"
STATIC_WEB_APP_NAME="gaia-frontend"
DEFAULT_HOSTNAME="purple-stone-099e15c0f.3.azurestaticapps.net"

if [ -z "$DOMAIN_NAME" ]; then
    echo "❌ Error: Domain name is required"
    echo ""
    echo "Usage: $0 <domain-name>"
    echo "Example: $0 app.gaia.com"
    exit 1
fi

echo "=== Setting up custom domain: $DOMAIN_NAME ==="
echo ""

# Step 1: Add custom domain to Azure Static Web App
echo "Step 1: Adding custom domain to Azure Static Web App..."
az staticwebapp hostname set \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --hostname "$DOMAIN_NAME" \
    --validation-method "cname-delegation" \
    --output table

echo ""
echo "✅ Custom domain added to Azure Static Web App"
echo ""

# Step 2: Get validation details
echo "Step 2: Getting validation details..."
VALIDATION_INFO=$(az staticwebapp hostname show \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --hostname "$DOMAIN_NAME" \
    --query "{validationToken:validationToken, hostname:hostname}" \
    -o json 2>/dev/null || echo "{}")

echo ""
echo "=== DNS Configuration Required ==="
echo ""
echo "Add the following CNAME record to your DNS provider:"
echo ""
echo "  Type: CNAME"
echo "  Name: $DOMAIN_NAME (or subdomain part if using subdomain)"
echo "  Value: $DEFAULT_HOSTNAME"
echo "  TTL: 3600 (or default)"
echo ""
echo "Example DNS records:"
echo "  - If domain is 'app.gaia.com':"
echo "    Name: app"
echo "    Value: $DEFAULT_HOSTNAME"
echo ""
echo "  - If domain is 'www.gaia.com':"
echo "    Name: www"
echo "    Value: $DEFAULT_HOSTNAME"
echo ""
echo "  - If domain is 'gaia.com' (root domain):"
echo "    Name: @"
echo "    Value: $DEFAULT_HOSTNAME"
echo ""

# Step 3: Wait for validation
echo "Step 3: Waiting for DNS validation..."
echo "Azure will automatically validate the domain once DNS propagates (usually 5-15 minutes)"
echo ""
echo "Check validation status with:"
echo "  az staticwebapp hostname show \\"
echo "    --name $STATIC_WEB_APP_NAME \\"
echo "    --resource-group $RESOURCE_GROUP \\"
echo "    --hostname $DOMAIN_NAME"
echo ""
echo "Once validated, SSL certificate will be automatically provisioned."
echo ""
echo "✅ Setup initiated! Complete DNS configuration to finish."





