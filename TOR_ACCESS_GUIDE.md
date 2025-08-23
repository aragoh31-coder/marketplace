# 🧅 Tor Hidden Service Access Guide

## Your Marketplace Onion URL

Your marketplace is now accessible via Tor at:

```
http://seczzblxgf5cg2srw7tztrd4kyrwilqzroyxpliyuh3mkfcje2lls7id.onion
```

## ✅ Setup Complete

### What's Been Configured:

1. **Tor Service**: Installed and running
2. **Hidden Service**: Configured to forward port 80 to Django (8000)
3. **Django Settings**: Updated to accept the onion domain
4. **Version 3 Onion**: Using the latest, most secure onion service version

## 🌐 How to Access

### Using Tor Browser:

1. **Download Tor Browser** from https://www.torproject.org/
2. **Open Tor Browser**
3. **Enter the onion URL**: 
   ```
   http://seczzblxgf5cg2srw7tztrd4kyrwilqzroyxpliyuh3mkfcje2lls7id.onion
   ```
4. **For Maximum Security**: Set Tor Browser to "Safest" mode
   - Click the shield icon
   - Go to Settings → Privacy & Security
   - Select "Safest"

### Security Features Active:

- ✅ No JavaScript required
- ✅ No external resources
- ✅ End-to-end encryption via Tor
- ✅ Complete anonymity
- ✅ One-Click CAPTCHA working
- ✅ All forms and features functional

## 🔧 Service Management

### Check Tor Status:
```bash
sudo service tor status
```

### Restart Tor:
```bash
sudo service tor restart
```

### View Tor Logs:
```bash
sudo journalctl -u tor -f
```

### Django Server:
The Django server is running on `0.0.0.0:8000` and is accessible via:
- Local: http://localhost:8000
- Tor: http://seczzblxgf5cg2srw7tztrd4kyrwilqzroyxpliyuh3mkfcje2lls7id.onion

## 📱 Mobile Access

You can also access the marketplace on mobile using:
- **Tor Browser for Android**: Available on Google Play
- **Onion Browser for iOS**: Available on App Store

## 🛡️ Important Security Notes

1. **Never share this onion address publicly** if you want to keep the service private
2. **Always verify** you're using HTTPS in production
3. **Keep Tor updated** for the latest security patches
4. **Monitor logs** for suspicious activity

## 🔍 Testing the Service

To verify everything is working:

1. **Home Page**: Should load with the marketplace interface
2. **Login/Register**: One-Click CAPTCHA should appear
3. **Navigation**: All pages should work without JavaScript
4. **Forms**: All forms should submit properly

## 📊 Current Status

- **Tor Service**: ✅ Running
- **Hidden Service**: ✅ Active
- **Django Server**: ✅ Running on port 8000
- **Onion Address**: ✅ Generated and configured

---

**Note**: This onion address is unique to your service. Keep it secure and only share it with trusted users.

**Backup**: The private key for this onion service is stored in:
```
/var/lib/tor/django_marketplace/
```
Make sure to backup this directory to preserve your onion address.