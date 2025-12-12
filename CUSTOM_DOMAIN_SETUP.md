# Custom Domain Setup for Azure Static Web Apps

## Why Use a Custom Domain?

Azure Static Web Apps generate random subdomains like `purple-stone-099e15c0f.3.azurestaticapps.net` which can be blocked by security services like Cisco Umbrella because they're "Newly Seen Domains".

A custom domain (e.g., `app.gaia.com` or `gaia.yourdomain.com`) is:
- ✅ Less likely to be blocked by security services
- ✅ More professional
- ✅ Easier to remember
- ✅ Better for branding

## Option 1: Add Custom Domain via Azure Portal

### Steps:

1. **Go to Azure Portal**
   - Navigate to: https://portal.azure.com
   - Find your Static Web App: `purple-stone`

2. **Add Custom Domain**
   - Go to **Settings** → **Custom domains**
   - Click **Add**
   - Enter your domain (e.g., `app.gaia.com`)
   - Choose validation method:
     - **DNS Validation** (recommended)
     - **HTML Validation**

3. **Configure DNS**
   - Add the CNAME record provided by Azure to your DNS provider
   - Example:
     ```
     Type: CNAME
     Name: app (or @ for root domain)
     Value: purple-stone-099e15c0f.3.azurestaticapps.net
     ```

4. **Wait for Validation**
   - Azure will validate the domain (usually 5-10 minutes)
   - Once validated, SSL certificate is automatically provisioned

## Option 2: Add Custom Domain via Azure CLI

```bash
# Add custom domain
az staticwebapp hostname set \
  --name purple-stone \
  --resource-group ai-ta-2 \
  --hostname app.gaia.com

# Check status
az staticwebapp hostname show \
  --name purple-stone \
  --resource-group ai-ta-2 \
  --hostname app.gaia.com
```

## Option 3: Use Azure Static Web Apps with Azure DNS

If you don't have a domain yet:

1. **Buy a Domain** (if needed)
   - Azure Domain Services
   - GoDaddy, Namecheap, etc.

2. **Set up Azure DNS Zone**
   ```bash
   # Create DNS zone
   az network dns zone create \
     --resource-group ai-ta-2 \
     --name gaia.com
   
   # Add A record or CNAME
   az network dns record-set cname create \
     --resource-group ai-ta-2 \
     --zone-name gaia.com \
     --name app \
     --cname purple-stone-099e15c0f.3.azurestaticapps.net
   ```

## Quick Fix: Whitelist Current Domain

If you have access to Cisco Umbrella admin panel:

1. **Log in to Cisco Umbrella Dashboard**
2. **Go to Policies** → **Web Content Filtering**
3. **Add Exception:**
   - Domain: `*.azurestaticapps.net`
   - Or specific: `purple-stone-099e15c0f.3.azurestaticapps.net`
   - Category: Allow "Newly Seen Domains" for this domain

## Alternative: Use Different Network

If you can't change the domain or whitelist:

- **Use mobile hotspot** (bypasses corporate network)
- **Use VPN** (if allowed)
- **Use different ISP/network**
- **Test from home network** (if not behind corporate firewall)

## Verify Deployment

Check if the app is actually accessible:

```bash
# Check if app is running
curl -I https://purple-stone-099e15c0f.3.azurestaticapps.net

# Should return HTTP 200 or 301/302
```

## Current Status

- **Backend**: ✅ Running at `https://gaia-backend.politefield-9abbbc93.eastus.azurecontainerapps.io`
- **Frontend**: ✅ Deployed at `https://purple-stone-099e15c0f.3.azurestaticapps.net`
- **Issue**: 🔴 Blocked by Cisco Umbrella (network-level, not code issue)

## Next Steps

1. **Immediate**: Try from different network (mobile hotspot)
2. **Short-term**: Contact network admin to whitelist domain
3. **Long-term**: Set up custom domain for professional deployment





