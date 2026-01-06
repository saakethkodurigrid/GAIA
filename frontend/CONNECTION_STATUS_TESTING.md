# Connection Status Indicator - Testing Guide

## Overview
The Connection Status Indicator has been successfully implemented across all test pages (MCQ, Coding, and System Design). This guide explains how to test the functionality.

## What Was Implemented

### 1. **ConnectionStatus Component**
- Location: `src/components/ConnectionStatus.tsx`
- Detects online/offline browser events
- Shows banner at top of screen when connection changes
- Auto-hides after 5 seconds when online (stays visible when offline)

### 2. **Integration**
The component has been integrated into:
- ✅ MCQ Test Page (`src/app/Candidate/MCQPage.tsx`)
- ✅ Coding Test Page (`src/app/Candidate/CodingTestPage.tsx`)
- ✅ System Design Page (`src/app/Candidate/SystemDesignPage.tsx`)

## How to Test

### Method 1: Browser DevTools (Recommended)

1. **Start the application:**
   ```bash
   cd GAIA/frontend
   npm run dev
   ```

2. **Navigate to any test page:**
   - MCQ: `/test/mcq`
   - Coding: `/test/coding`
   - System Design: `/test/system-design`

3. **Open Chrome DevTools:**
   - Press `F12` or `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows)
   - Go to the **Network** tab
   - Click the dropdown that says **"No throttling"**
   - Select **"Offline"**

4. **Observe:**
   - 🔴 Red banner should appear at the top: "⚠️ No internet connection!"
   - Banner has a pulsing animation
   - Banner stays visible while offline

5. **Restore connection:**
   - In DevTools Network tab, select **"No throttling"** again
   
6. **Observe:**
   - 🟢 Green banner should appear: "✅ Connection restored!"
   - Banner automatically disappears after 5 seconds

### Method 2: Network Disconnect (Real-world Test)

1. **Start the test**

2. **Disconnect your WiFi/Ethernet:**
   - Mac: Turn off WiFi in menu bar
   - Windows: Disable network adapter
   - Or unplug ethernet cable

3. **Observe:**
   - Red warning banner appears

4. **Reconnect network**

5. **Observe:**
   - Green success banner appears
   - Disappears after 5 seconds

### Method 3: Airplane Mode

1. **Enter a test page**

2. **Enable Airplane Mode** on your computer

3. **Observe:**
   - Red warning banner appears

4. **Disable Airplane Mode**

5. **Observe:**
   - Green success banner appears

## Expected Behavior

### When Going Offline:
- ✅ Red banner appears immediately
- ✅ Shows warning icon
- ✅ Message: "⚠️ No internet connection! Your answers are saved locally but cannot be uploaded to the server. Please reconnect soon."
- ✅ Banner has pulsing animation
- ✅ Banner stays visible until connection is restored

### When Coming Back Online:
- ✅ Red banner changes to green
- ✅ Shows checkmark icon
- ✅ Message: "✅ Connection restored! Your answers are being saved to the server."
- ✅ Banner auto-hides after 5 seconds

## Technical Details

### Browser APIs Used:
- `navigator.onLine` - Check current connection status
- `window.addEventListener('online')` - Detect connection restore
- `window.addEventListener('offline')` - Detect connection loss

### Styling:
- Fixed position at top of screen (`z-index: 50`)
- Red background (`bg-red-600`) for offline
- Green background (`bg-green-600`) for restored
- Smooth transitions and animations
- Accessible with ARIA attributes

## Known Limitations

1. **Browser API Limitations:**
   - `navigator.onLine` only detects if the browser is connected to a network
   - It does NOT detect if the network has actual internet access
   - Example: Connected to WiFi with no internet will still show as "online"

2. **Slow Connections:**
   - The indicator only shows offline/online status
   - It doesn't detect slow/degraded connections

3. **Server Issues:**
   - If the backend server is down but internet is working, the indicator won't show
   - This only tracks network connectivity, not API availability

## Future Enhancements (Not Implemented Yet)

- [ ] Track API call failures (distinguish between network issues and server issues)
- [ ] Show warning when heartbeat fails
- [ ] Display countdown before auto-submission
- [ ] Manual retry button when offline
- [ ] Show last successful save timestamp

## Troubleshooting

### Banner doesn't appear when going offline:
- Check browser console for errors
- Verify component is imported correctly
- Ensure you're on a test page (not landing page)

### Banner appears but doesn't auto-hide:
- This is expected behavior when offline (stays visible)
- Only auto-hides when connection is restored

### Network tab shows offline but banner doesn't appear:
- Hard refresh the page (`Cmd+Shift+R` or `Ctrl+Shift+R`)
- Clear browser cache

## Verification Checklist

- [ ] Red banner appears when going offline
- [ ] Green banner appears when connection restores
- [ ] Green banner auto-hides after 5 seconds
- [ ] Component works on MCQ page
- [ ] Component works on Coding page
- [ ] Component works on System Design page
- [ ] Console logs show connection state changes
- [ ] No TypeScript/linter errors

---

## Success! ✅

The Connection Status Indicator has been successfully implemented and is ready for testing. It provides real-time feedback to candidates about their internet connectivity during tests.

