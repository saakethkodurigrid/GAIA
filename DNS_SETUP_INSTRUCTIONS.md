# DNS Setup Instructions for app.gaia.com

## ✅ Custom Domain Added to Azure

The custom domain `app.gaia.com` has been added to your Azure Static Web App.

## 📋 DNS Configuration Required

You need to add a CNAME record to your DNS provider where `gaia.com` is hosted.

### CNAME Record Details:

```
Type:    CNAME
Name:    app
Value:   purple-stone-099e15c0f.3.azurestaticapps.net
TTL:     3600 (or default)
```

### Step-by-Step Instructions:

#### If using GoDaddy:
1. Log in to GoDaddy
2. Go to **My Products** → **DNS** → **gaia.com**
3. Click **Add** → **CNAME**
4. Enter:
   - **Name**: `app`
   - **Value**: `purple-stone-099e15c0f.3.azurestaticapps.net`
   - **TTL**: `1 Hour`
5. Click **Save**

#### If using Namecheap:
1. Log in to Namecheap
2. Go to **Domain List** → **Manage** for `gaia.com`
3. Go to **Advanced DNS** tab
4. Click **Add New Record**
5. Select **CNAME Record**
6. Enter:
   - **Host**: `app`
   - **Value**: `purple-stone-099e15c0f.3.azurestaticapps.net`
   - **TTL**: `Automatic`
7. Click **Save**

#### If using Azure DNS:
```bash
az network dns record-set cname create \
  --resource-group <your-dns-resource-group> \
  --zone-name gaia.com \
  --name app \
  --cname purple-stone-099e15c0f.3.azurestaticapps.net
```

#### If using Cloudflare:
1. Log in to Cloudflare
2. Select `gaia.com` domain
3. Go to **DNS** → **Records**
4. Click **Add record**
5. Select:
   - **Type**: `CNAME`
   - **Name**: `app`
   - **Target**: `purple-stone-099e15c0f.3.azurestaticapps.net`
   - **Proxy status**: `DNS only` (gray cloud)
6. Click **Save**

## ⏱️ Validation Process

After adding the DNS record:

1. **Wait 5-15 minutes** for DNS propagation
2. Azure will automatically detect and validate the CNAME record
3. SSL certificate will be automatically provisioned (free)
4. Your app will be accessible at: **https://app.gaia.com**

## 🔍 Check Validation Status

```bash
az staticwebapp hostname show \
  --name gaia-frontend \
  --resource-group ai-ta-2 \
  --hostname app.gaia.com
```

Look for `"validationState": "Valid"` in the output.

## ✅ Once Validated

- Your app will be accessible at: **https://app.gaia.com**
- SSL certificate is automatically managed by Azure
- No additional configuration needed
- Update Google OAuth redirect URI to: `https://app.gaia.com/api/v1/auth/google/callback`

## 🆘 Troubleshooting

### If validation fails:
1. Verify DNS record is correct
2. Check DNS propagation: `nslookup app.gaia.com`
3. Wait up to 24 hours for full propagation
4. Re-check validation status

### If you don't own gaia.com:
- You'll need to purchase the domain first
- Or use a different domain you own
- Or contact your organization's DNS administrator

## 📝 Current Status

- ✅ Custom domain added to Azure: `app.gaia.com`
- ⏳ Waiting for DNS configuration
- ⏳ Waiting for Azure validation
- ⏳ SSL certificate will auto-provision after validation





