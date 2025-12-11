# Azure Portal Custom Domain Form - What to Enter

## Current Form Fields:

### Option 1: If you have Azure DNS Zone for `gaia.com`

**DNS zone:**
- Select: `gaia.com` (if it exists in your Azure subscription)
- This will auto-create the DNS records

**Subdomain:**
- Enter: `app`
- This creates `app.gaia.com`

**Full domain:**
- Leave empty (or it will auto-fill to `app.gaia.com`)

---

### Option 2: If you DON'T have Azure DNS Zone (Most Common)

**DNS zone:**
- Leave as: `(None)` or don't select anything

**Subdomain:**
- Leave empty

**Full domain:**
- Enter: `app.gaia.com`
- This will show you the CNAME record to add manually

---

## Recommended: Use Option 2 (Full Domain)

Since you're likely using an external DNS provider (GoDaddy, Namecheap, etc.):

1. **DNS zone:** Leave empty/None
2. **Subdomain:** Leave empty  
3. **Full domain:** Enter `app.gaia.com`
4. Click **Next** or **Add**

Azure will then show you:
- The CNAME record to add: `app` → `purple-stone-099e15c0f.3.azurestaticapps.net`
- Where to add it (your DNS provider)

---

## After Clicking Add:

1. Azure will show you the DNS record to add
2. Go to your DNS provider (where `gaia.com` is hosted)
3. Add the CNAME record shown
4. Wait 5-15 minutes for validation
5. SSL certificate will auto-provision
6. Access at: **https://app.gaia.com**

---

## Quick Summary:

**What to enter:**
- DNS zone: (None/Empty)
- Subdomain: (Empty)
- Full domain: `app.gaia.com`

Then click **Add** and follow the DNS instructions Azure provides.





