# Add Custom Domain via Azure Portal

## Step-by-Step Instructions

### 1. Go to Azure Portal
- Navigate to: https://portal.azure.com
- Sign in with your Azure account

### 2. Find Your Static Web App
- Search for "Static Web Apps" in the top search bar
- Click on **gaia-frontend** (or find it in your resource group `ai-ta-2`)

### 3. Add Custom Domain
- In the left menu, click **Custom domains**
- Click **Add** button at the top
- Enter domain name: `app.gaia.com`
- Click **Next**

### 4. Choose Validation Method
- Select **CNAME validation** (recommended)
- Azure will show you the CNAME record you need to add

### 5. Add DNS Record
You'll see something like:
```
Type: CNAME
Name: app
Value: purple-stone-099e15c0f.3.azurestaticapps.net
```

**Add this to your DNS provider:**
- Go to where `gaia.com` is hosted (GoDaddy, Namecheap, Azure DNS, etc.)
- Add the CNAME record shown
- Save the DNS record

### 6. Wait for Validation
- Azure will automatically validate (5-15 minutes)
- Status will change from "Pending" to "Valid"
- SSL certificate will be auto-provisioned

### 7. Done!
- Your app will be accessible at: **https://app.gaia.com**
- No more Cisco Umbrella blocking!

---

## Alternative: Fix Cisco Umbrella Blocking (Current Domain)

If you can't set up custom domain, you can whitelist the current domain:

### Option 1: Contact Network Admin
Ask your network administrator to whitelist:
- Domain: `*.azurestaticapps.net`
- Or specifically: `purple-stone-099e15c0f.3.azurestaticapps.net`
- Category: Allow "Newly Seen Domains" for this domain

### Option 2: Use Different Network
- Use mobile hotspot
- Use home network (if not behind corporate firewall)
- Use VPN (if allowed)

### Option 3: Access via Direct IP (if available)
- Check if Azure provides direct IP access
- This bypasses DNS-based blocking

---

## Quick Access Links

- **Azure Portal**: https://portal.azure.com
- **Static Web App**: Search for "gaia-frontend" in Azure Portal
- **Current URL**: https://purple-stone-099e15c0f.3.azurestaticapps.net (blocked by Cisco Umbrella)





