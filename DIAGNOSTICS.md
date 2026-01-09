# Server Diagnostics Guide

## Current Status
✅ Server is running on port 5000
✅ All routes are registered correctly
✅ Templates are loading without errors
✅ Database is initialized

## If You're Still Seeing Errors:

### Step 1: Clear Browser Cache
1. Press `Ctrl + Shift + Delete`
2. Select "Cached images and files"
3. Select "All time"
4. Click "Clear data"

### Step 2: Hard Refresh
- Press `Ctrl + F5` or `Ctrl + Shift + R`

### Step 3: Try Incognito/Private Window
- Open a new incognito/private window
- Go to http://127.0.0.1:5000

### Step 4: Check Browser Console
1. Press `F12` to open Developer Tools
2. Go to the Console tab
3. Look for any red error messages
4. Share the error message if you see one

### Step 5: Test Server Directly
1. Go to http://127.0.0.1:5000/test
2. You should see "Server is Working!"
3. If you see an error, note the exact error message

### Step 6: Verify Server is Running
1. Open PowerShell
2. Run: `netstat -an | Select-String ":5000"`
3. You should see: `TCP    127.0.0.1:5000         0.0.0.0:0              LISTENING`

### Step 7: Restart Server
1. Stop the server (Ctrl+C in the terminal)
2. Run: `python app.py` from the backend directory
3. Wait for "Running on http://127.0.0.1:5000" message

## Common Issues:

### Issue: "Could not build url for endpoint 'admin'"
**Solution**: This has been fixed. Clear browser cache and restart server.

### Issue: Page loads but shows errors
**Solution**: Check browser console (F12) for JavaScript errors.

### Issue: Server not responding
**Solution**: 
1. Check if port 5000 is in use
2. Restart the server
3. Try a different port: `app.run(debug=True, port=5001)`

### Issue: Template errors
**Solution**: All templates have been verified. Clear cache and restart.

## Test URLs:
- http://127.0.0.1:5000/ - Main dashboard
- http://127.0.0.1:5000/test - Test page
- http://127.0.0.1:5000/api/appointments - API test

## Still Not Working?
Please provide:
1. The exact error message from browser console (F12)
2. The URL you're trying to access
3. What happens when you visit http://127.0.0.1:5000/test

