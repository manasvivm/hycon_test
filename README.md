# HyCON Equipment Management System - Deployment Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Prerequisites](#prerequisites)
5. [Backend Setup](#backend-setup)
6. [Frontend Setup](#frontend-setup)
7. [Database Configuration](#database-configuration)
8. [Environment Variables](#environment-variables)
9. [Production Deployment](#production-deployment)
10. [Security Considerations](#security-considerations)
11. [Maintenance & Monitoring](#maintenance--monitoring)
12. [Troubleshooting](#troubleshooting)

---

## System Overview

HyCON Equipment Management System is a full-stack web application designed to manage laboratory equipment usage, track sessions, and provide analytics for administrative oversight.

### Key Features
- **User Authentication & Authorization** (Admin/Employee roles)
- **Equipment Management** (CRUD operations, status tracking)
- **Session Management** (Start/end sessions, log past usage, time conflict detection)
- **Analytics Dashboard** (Equipment utilization, user activity, filtered reports)
- **Admin Panel** (Equipment management, session filtering, data export to CSV/PDF)

---

## Architecture

```
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│                 │          │                 │          │                 │
│  React Frontend │◄────────►│  FastAPI Backend│◄────────►│  PostgreSQL DB  │
│  (Port 5173)    │   HTTP   │  (Port 8000)    │   SQL    │  (Port 5432)    │
│                 │          │                 │          │                 │
└─────────────────┘          └─────────────────┘          └─────────────────┘
```

**Frontend**: Single Page Application (SPA) built with React
**Backend**: RESTful API built with FastAPI
**Database**: PostgreSQL with SQLAlchemy ORM
**Authentication**: JWT-based token authentication

---

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+
- **Database**: PostgreSQL 14+
- **Authentication**: 
  - python-jose[cryptography] (JWT tokens)
  - passlib[bcrypt] (Password hashing)
- **ASGI Server**: Uvicorn
- **Migration Tool**: Alembic
- **Additional Libraries**:
  - python-multipart (File uploads)
  - python-dateutil (Date parsing)

### Frontend
- **Framework**: React 18.2+
- **Build Tool**: Vite 4.5+
- **Routing**: React Router DOM 6+
- **State Management**: React Query (TanStack Query)
- **HTTP Client**: Axios
- **UI Components**: 
  - Headless UI (Accessible components)
  - Heroicons (Icon library)
- **Styling**: TailwindCSS 3+
- **Charts**: Recharts 2.10+
- **Date Utilities**: date-fns

---

## Prerequisites

### Server Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended) or Windows Server 2019+
- **RAM**: Minimum 4GB (8GB+ recommended for production)
- **CPU**: 2+ cores
- **Disk Space**: 10GB+ for application and database


### Software Requirements
- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher
- **npm**: 9.x or higher
- **PostgreSQL**: 14 or higher
- **Reverse Proxy**: Nginx or Apache (for production)
- **Process Manager**: systemd, supervisord, or PM2

---

## Backend Setup

### 1. Clone Repository
```bash
cd /opt/
git clone <repository-url> hycon
cd hycon/backend
```

### 2. Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment Configuration
Create `.env` file in `backend/` directory:

```env
# Database Configuration
DATABASE_URL=postgresql://hycon_user:secure_password@localhost:5432/hycon_db

# Security
SECRET_KEY=your-secret-key-min-32-characters-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Settings (Frontend URL)
FRONTEND_URL=http://your-company-domain.com

# Application Settings
DEBUG=False
ENVIRONMENT=production
```

**Generate SECRET_KEY**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. Database Setup

#### Create PostgreSQL Database
```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql

-- Create database and user
CREATE DATABASE hycon_db;
CREATE USER hycon_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE hycon_db TO hycon_user;
ALTER DATABASE hycon_db OWNER TO hycon_user;

-- Exit
\q
```

#### Run Migrations
```bash
cd backend
alembic upgrade head
```

### 6. Create Initial Admin User
```bash
# Run Python shell
python

# Execute in Python shell:
from app.database import SessionLocal
from app.crud import create_user
from app.schemas import UserCreate
from app.models import UserRole

db = SessionLocal()

admin_user = UserCreate(
    name="Admin User",
    email="admin@company.com",
    password="ChangeThisPassword123!",
    role=UserRole.ADMIN
)

create_user(db, admin_user)
db.close()
print("Admin user created successfully!")
exit()
```

### 7. Test Backend Server
```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode (see Production Deployment section)
```

### Backend API Documentation
Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Frontend Setup

### 1. Navigate to Frontend Directory
```bash
cd /opt/hycon/frontend
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Environment Configuration
Create `.env` file in `frontend/` directory:

```env
# API Configuration
VITE_API_URL=http://your-company-domain.com/api

# OR for development
VITE_API_URL=http://localhost:8000
```

### 4. Build for Production
```bash
npm run build
```

This creates optimized production files in `frontend/dist/` directory.

### 5. Test Frontend (Development)
```bash
npm run dev
```
Access at: http://localhost:5173

---

## Database Configuration

### Database Schema
The system uses the following main tables:
- **users**: User accounts with roles (admin/employee)
- **equipment**: Laboratory equipment with status tracking
- **usage_sessions**: Equipment usage sessions with timestamps
- **description_history**: Autocomplete suggestions for descriptions

### Connection Pooling (Production)
Add to `backend/app/database.py`:

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Backup Strategy
```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/opt/backups/hycon"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U hycon_user hycon_db > "$BACKUP_DIR/hycon_db_$DATE.sql"

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
```

Add to crontab:
```bash
0 2 * * * /opt/scripts/backup_hycon.sh
```

---

## Environment Variables

### Backend (.env)
```env
# Required
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key-32-chars-minimum
FRONTEND_URL=https://your-domain.com

# Optional
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=False
ENVIRONMENT=production
MAX_UPLOAD_SIZE=10485760  # 10MB
```

### Frontend (.env)
```env
VITE_API_URL=https://your-domain.com/api
```

---

## Production Deployment

### Option 1: Systemd Service (Linux)

#### Backend Service
Create `/etc/systemd/system/hycon-backend.service`:

```ini
[Unit]
Description=HyCON Equipment Management Backend
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/hycon/backend
Environment="PATH=/opt/hycon/backend/venv/bin"
ExecStart=/opt/hycon/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start Service**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable hycon-backend
sudo systemctl start hycon-backend
sudo systemctl status hycon-backend
```

### Option 2: Nginx Reverse Proxy

Create `/etc/nginx/sites-available/hycon`:

```nginx
# Backend API
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-company-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-company-domain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/your-cert.crt;
    ssl_certificate_key /etc/ssl/private/your-key.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Frontend Static Files
    root /opt/hycon/frontend/dist;
    index index.html;

    # Frontend SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API Proxy
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }

    # WebSocket support (if needed in future)
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Logging
    access_log /var/log/nginx/hycon-access.log;
    error_log /var/log/nginx/hycon-error.log;
}
```

**Enable Site**:
```bash
sudo ln -s /etc/nginx/sites-available/hycon /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Option 3: Docker Deployment (Optional)

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    container_name: hycon-db
    environment:
      POSTGRES_DB: hycon_db
      POSTGRES_USER: hycon_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always

  backend:
    build: ./backend
    container_name: hycon-backend
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://hycon_user:secure_password@postgres:5432/hycon_db
      SECRET_KEY: your-secret-key-here
      FRONTEND_URL: https://your-domain.com
    ports:
      - "8000:8000"
    restart: always

  frontend:
    build: ./frontend
    container_name: hycon-frontend
    environment:
      VITE_API_URL: https://your-domain.com/api
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: always

volumes:
  postgres_data:
```

---

## Security Considerations

### 1. Database Security
- Use strong passwords (minimum 16 characters)
- Restrict PostgreSQL to local connections only
- Enable SSL connections to database
- Regular security updates

### 2. Application Security
- Change default SECRET_KEY
- Use HTTPS in production (SSL/TLS certificates)
- Implement rate limiting on API endpoints
- Regular dependency updates (`pip list --outdated`)
- Set secure CORS origins

### 3. Server Security
- Enable firewall (ufw/iptables)
- Keep OS updated
- Use fail2ban for brute-force protection
- Disable root SSH login
- Use SSH keys instead of passwords

### 4. Application-Level Security
```python
# Add rate limiting in backend/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to login endpoint
@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(...):
    ...
```

---

## Maintenance & Monitoring

### Logging

#### Backend Logging
Add to `backend/app/main.py`:

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            '/var/log/hycon/backend.log',
            maxBytes=10485760,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)
```

#### Monitor Logs
```bash
# Backend logs
sudo tail -f /var/log/hycon/backend.log

# Nginx logs
sudo tail -f /var/log/nginx/hycon-access.log
sudo tail -f /var/log/nginx/hycon-error.log

# System service logs
sudo journalctl -u hycon-backend -f
```

### Health Checks

Add endpoint in `backend/app/main.py`:

```python
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Check database connection
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
```

### Monitoring Script
```bash
#!/bin/bash
# /opt/scripts/monitor_hycon.sh

HEALTH_URL="https://your-domain.com/api/health"
RESPONSE=$(curl -s $HEALTH_URL)

if echo "$RESPONSE" | grep -q "healthy"; then
    echo "$(date): System healthy"
else
    echo "$(date): System unhealthy - $RESPONSE"
    # Send alert (email, Slack, etc.)
    systemctl restart hycon-backend
fi
```

Add to crontab:
```bash
*/5 * * * * /opt/scripts/monitor_hycon.sh >> /var/log/hycon/monitor.log 2>&1
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection
psql -U hycon_user -d hycon_db -h localhost

# Check DATABASE_URL format
DATABASE_URL=postgresql://user:password@host:port/database
```

#### 2. CORS Errors
Update `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Update this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 3. Frontend Build Errors
```bash
# Clear cache and rebuild
rm -rf node_modules package-lock.json
npm install
npm run build
```

#### 4. Migration Errors
```bash
# Reset migrations (CAUTION: data loss)
alembic downgrade base
alembic upgrade head

# Or create new migration
alembic revision --autogenerate -m "description"
alembic upgrade head
```

#### 5. Permission Issues
```bash
# Fix ownership
sudo chown -R www-data:www-data /opt/hycon
sudo chmod -R 755 /opt/hycon

# Fix log directory
sudo mkdir -p /var/log/hycon
sudo chown www-data:www-data /var/log/hycon
```

### Debug Mode

Enable debug logging:
```python
# backend/app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Performance Optimization

### Backend Optimization
1. **Database Indexes**: Already configured on foreign keys
2. **Connection Pooling**: Configured in database.py
3. **Uvicorn Workers**: Use `--workers 4` (number of CPU cores)
4. **Query Optimization**: Use `joinedload()` for relationships

### Frontend Optimization
1. **Build Optimization**: Already configured in Vite
2. **Code Splitting**: Automatic with React Router
3. **Asset Compression**: Enable in Nginx
4. **Caching**: Configure browser caching

Nginx caching configuration:
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

---

## API Endpoints Reference

### Authentication
- `POST /auth/login` - User login (returns JWT token)
- `GET /auth/me` - Get current user info
- `GET /auth/users` - Get all users (admin only)

### Equipment
- `GET /equipment/` - List all equipment
- `GET /equipment/{id}` - Get equipment details
- `POST /equipment/` - Create equipment (admin only)
- `PUT /equipment/{id}` - Update equipment (admin only)
- `DELETE /equipment/{id}` - Delete equipment (admin only)

### Sessions
- `POST /sessions/start` - Start new session
- `PUT /sessions/{id}/end` - End session
- `POST /sessions/log-past-usage` - Log past usage
- `GET /sessions/my-sessions` - Get user's sessions
- `GET /sessions/my-active` - Get active sessions
- `GET /sessions/` - Get all sessions with filters (admin)

### Analytics (Admin)
- `GET /analytics/equipment-utilization` - Equipment usage stats
- `GET /analytics/user-activity` - User activity stats
- `GET /analytics/generate-report` - Generate PDF report

---

## Default Credentials

**Development Only** (Change in production):
- Admin: `admin@hycon.com` / `admin123`
- Employee: `john.doe@hycon.com` / `user123`

**Production**: Create secure credentials as shown in Backend Setup section.

---

## Support & Contact

For technical support or issues:
- **Repository**: [Link to your internal Git repository]
- **Documentation**: This README
- **Contact**: [Your IT team contact information]

---

## Version Information

- **Application Version**: 1.0.0
- **Last Updated**: November 2025
- **Python Version**: 3.11+
- **Node.js Version**: 18.x+
- **PostgreSQL Version**: 14+

---

## License

Proprietary - Internal Use Only
© 2025 [Your Company Name]. All rights reserved.
