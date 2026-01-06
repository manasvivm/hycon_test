# HyCON Equipment Management - Deployment Guide

## Overview

HyCON is a lab equipment management system with:

- **Backend:** FastAPI Python app (runs on port 8000)
- **Frontend:** React web app (static files - serve with any web server on port 80/443)
- **Database:** PostgreSQL

---

## Prerequisites

Install these on Windows Server:

1. **Python 3.11+** - https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during install
2. **Node.js 18+** - https://nodejs.org/
3. **PostgreSQL 14+** - https://www.postgresql.org/download/windows/
4. **NSSM** - https://nssm.cc/download (to run backend as Windows Service)
5. **Web Server** - Choose one:
   - IIS (recommended for Windows)
   - Apache
   - Nginx
   - Or any static file server

---

## Step 1: Get the Code

Clone or extract to `C:\inetpub\wwwroot\hycon`:

```cmd
cd C:\inetpub\wwwroot
git clone https://github.com/manasvivm/hycon_test.git hycon
```

---

## Step 2: Setup PostgreSQL Database

Open Command Prompt as Administrator:

```cmd
psql -U postgres
```

Run these SQL commands:

```sql
-- Create database and user
CREATE DATABASE hycon_db;
CREATE USER hycon_user WITH ENCRYPTED PASSWORD 'YourSecurePassword123!';

-- Grant database-level privileges
GRANT ALL PRIVILEGES ON DATABASE hycon_db TO hycon_user;
ALTER DATABASE hycon_db OWNER TO hycon_user;

-- Connect to the database
\c hycon_db

-- Grant schema privileges (required for PostgreSQL 15+)
GRANT ALL ON SCHEMA public TO hycon_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hycon_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hycon_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO hycon_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO hycon_user;

-- Exit
\q
```

---

## Step 3: Configure Backend (.env file)

Copy the template and edit:

```cmd
cd C:\inetpub\wwwroot\hycon\backend
copy .env.example .env
notepad .env
```

**Edit `.env` and set these values:**

```env
# REQUIRED - Update with your actual values
DATABASE_URL=postgresql://hycon_user:YourSecurePassword123!@localhost:5432/hycon_db
SECRET_KEY=<generate-with-command-below>
FRONTEND_URL=https://your-company-domain.com
ENVIRONMENT=production
DEBUG=False

# OPTIONAL - Only if email notifications needed
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USER=noreply@company.com
SMTP_PASSWORD=EmailPassword
SMTP_FROM_EMAIL=noreply@company.com
SMTP_FROM_NAME=HYCON Lab Management
```

**Generate SECRET_KEY:**

```cmd
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and paste it as `SECRET_KEY` value in `.env`.

---

## Step 4: Setup Backend Python App

Install dependencies:

```cmd
cd C:\inetpub\wwwroot\hycon\backend
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Initialize database (creates tables and mock data):

```cmd
python run.py
```

Press `Ctrl+C` after you see "Uvicorn running on http://0.0.0.0:8000".

This creates:
- Database tables
- Mock users (admin@hycon.com / admin123)
- Sample equipment and sessions

---

## Step 5: Install Backend as Windows Service

Use NSSM to run backend automatically:

```cmd
# Run Command Prompt as Administrator

# Install service
nssm install HyconBackend "C:\inetpub\wwwroot\hycon\backend\venv\Scripts\python.exe" "C:\inetpub\wwwroot\hycon\backend\run.py"

# Configure service
nssm set HyconBackend AppDirectory "C:\inetpub\wwwroot\hycon\backend"
nssm set HyconBackend Start SERVICE_AUTO_START
nssm set HyconBackend Description "HyCON Equipment Management Backend"

# Start service
nssm start HyconBackend
```

**Verify backend is running:**

```cmd
curl http://localhost:8000/health
```

Or open in browser: http://localhost:8000/docs

---

## Step 6: Setup Frontend React App

Build the frontend:

```cmd
cd C:\inetpub\wwwroot\hycon\frontend
npm install
npm run build
```

This creates `frontend\dist` folder with optimized files.

---

## Step 7: Deploy Frontend (Choose Your Web Server)

The frontend is just static files in `frontend\dist` folder. Serve them with any web server.

### Option A: IIS (Windows)

1. Open **IIS Manager** (run `inetmgr`)
2. Right-click **Sites** > **Add Website**
   - **Site name:** HyconFrontend
   - **Physical path:** `C:\inetpub\wwwroot\hycon\frontend\dist`
   - **Port:** 80
3. **Install URL Rewrite Module:** https://www.iis.net/downloads/microsoft/url-rewrite
4. Add rewrite rule to route all requests to `index.html` (for React Router)

### Option B: Nginx

Create config file `/etc/nginx/sites-available/hycon`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root C:/inetpub/wwwroot/hycon/frontend/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### Option C: Apache

Add to your Apache config:

```apache
<VirtualHost *:80>
    DocumentRoot "C:/inetpub/wwwroot/hycon/frontend/dist"
    <Directory "C:/inetpub/wwwroot/hycon/frontend/dist">
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>
</VirtualHost>
```

### Option D: Simple HTTP Server (Development/Testing Only)

```cmd
cd C:\inetpub\wwwroot\hycon\frontend\dist
python -m http.server 80
```

**Important:** All options must route non-file requests to `index.html` for React Router to work.

---

## Step 8: Configure Firewall

Allow required ports:

```cmd
# Run as Administrator
netsh advfirewall firewall add rule name="HyCON Backend" dir=in action=allow protocol=TCP localport=8000
netsh advfirewall firewall add rule name="HyCON HTTP" dir=in action=allow protocol=TCP localport=80
netsh advfirewall firewall add rule name="HyCON HTTPS" dir=in action=allow protocol=TCP localport=443
```

---

## Step 9: Verification

**Check backend service:**
```cmd
sc query HyconBackend
```
Should show: `STATE: 4 RUNNING`

**Check web server status:**

IIS:
```cmd
iisreset /status
```

Nginx:
```cmd
nginx -t && systemctl status nginx
```

Apache:
```cmd
httpd -t && net start Apache2.4
```

**Test URLs:**
- Backend API: http://localhost:8000/docs
- Frontend: http://localhost (or http://server-ip)
- From another machine (via VPN): http://your-company-domain.com

**Restart services if needed:**

Backend:
```cmd
nssm restart HyconBackend
```

Web server (choose yours):
```cmd
iisreset          # IIS
nginx -s reload   # Nginx
httpd -k restart  # Apache
```

---

## Default Login Credentials

After deployment, login with:
- **Email:** admin@hycon.com
- **Password:** admin123

⚠️ **Change this immediately after first login!**

---

## Managing the Application

### Backend Service Commands:
```cmd
nssm start HyconBackend      # Start
nssm stop HyconBackend       # Stop
nssm restart HyconBackend    # Restart
nssm status HyconBackend     # Check status
```

### Web Server Commands:

**IIS:**
```cmd
iisreset                     # Restart
iisreset /stop              # Stop
iisreset /start             # Start
```

**Nginx:**
```cmd
nginx -s reload             # Reload config
systemctl stop nginx        # Stop
systemctl start nginx       # Start
systemctl restart nginx     # Restart
```

**Apache:**
```cmd
httpd -k restart            # Restart
net stop Apache2.4          # Stop
net start Apache2.4         # Start
```

### View Logs:
- Backend: **Event Viewer** > Windows Logs > Application (look for "HyconBackend")
- Web server logs: Check your web server's log directory
  - IIS: `C:\inetpub\logs\LogFiles\`
  - Nginx: `/var/log/nginx/`
  - Apache: `logs/` directory in Apache installation

---

## Updating the Application

When code changes are pushed to GitHub:

```cmd
# Stop backend service
nssm stop HyconBackend

# Pull latest code
cd C:\inetpub\wwwroot\hycon
git pull origin main

# Update backend dependencies (if needed)
cd backend
venv\Scripts\activate
pip install -r requirements.txt

# Rebuild frontend (if frontend changed)
cd ..\frontend
npm install
npm run build

# Restart backend service
nssm start HyconBackend

# Restart web server (choose yours)
iisreset              # IIS
nginx -s reload       # Nginx
httpd -k restart      # Apache
```

---

## Troubleshooting

### Backend won't start
```cmd
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Check Python path
where python

# Check Event Viewer for errors
eventvwr
```

### Frontend shows blank page
```cmd
# Verify build files exist
dir C:\inetpub\wwwroot\hycon\frontend\dist

# Verify web server is configured to route all requests to index.html
# This is required for React Router to work

# Check web server error logs for details
```

### Database connection error
```cmd
# Verify PostgreSQL is running
services.msc
# Look for postgresql-x64-14 service

# Test database connection
psql -U hycon_user -d hycon_db -h localhost
# Enter password when prompted
```

---

## Security Notes

- Change default admin password immediately
- Keep `.env` file secure (never commit to git)
- Use strong passwords for PostgreSQL
- Generate a unique SECRET_KEY for production
- Consider setting up SSL certificate for HTTPS

---

## Support

- **Developer:** Manasvi Varma
- **GitHub:** https://github.com/manasvivm/hycon_test
- **Configuration template:** `backend/.env.example`
