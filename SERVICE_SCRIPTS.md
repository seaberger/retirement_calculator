# Service Management Scripts

This directory contains scripts to manage the Retirement Calculator services (API and Frontend).

## Scripts

### 🟢 `check_services.sh`
Checks the health and status of both API and frontend services. If any service is not running, it will automatically start it.

```bash
./check_services.sh
```

**Features:**
- Checks if services are running on their respective ports
- Verifies API health endpoint
- Automatically starts services if they're not running
- Shows service URLs and documentation links
- Lists all running processes

### 🔴 `stop_services.sh`
Stops both API and frontend services.

```bash
./stop_services.sh
```

**Features:**
- Stops API server on port 8020
- Stops frontend server on port 5177
- Confirms services have been stopped

### 🔄 `restart_services.sh`
Restarts both services (stops then starts).

```bash
./restart_services.sh
```

**Features:**
- Stops all services cleanly
- Waits for services to fully stop
- Starts services fresh

## Service Details

### API Server
- **Port:** 8020
- **URL:** http://localhost:8020
- **Docs:** http://localhost:8020/docs
- **Health:** http://localhost:8020/health
- **Technology:** FastAPI + Uvicorn
- **Auto-reload:** Enabled (watches for code changes)

### Frontend Server
- **Port:** 5177
- **URL:** http://localhost:5177
- **Technology:** Vite + React
- **Auto-reload:** Enabled (hot module replacement)

## Logs

When services are started via these scripts:
- API logs: `api.log`
- Frontend logs: `frontend.log`

## Troubleshooting

### Port Already in Use
If you get a "port already in use" error, the script will attempt to kill the existing process and restart the service.

### Service Won't Start
1. Check the log files for error messages
2. Ensure dependencies are installed:
   ```bash
   # For API
   cd src/backend && uv pip install -r ../../requirements.txt
   
   # For Frontend
   cd frontend && npm install
   ```

### Manual Process Management
To find processes manually:
```bash
# Find API process
lsof -i :8020

# Find Frontend process
lsof -i :5177

# Kill a process by PID
kill -9 <PID>
```

## Requirements

- `uv` for Python package management
- `npm` for frontend package management
- `lsof` command (usually pre-installed on macOS/Linux)
- `curl` for health checks