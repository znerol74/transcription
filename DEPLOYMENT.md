# Quick Deployment Guide

## For IT Admin - Production Deployment

### Step 1: Prepare Environment

1. **Copy and configure environment file:**
   ```bash
   cp .env.example .env
   nano .env  # or use your preferred editor
   ```

2. **Required values to fill in `.env`:**
   - `CLIENT_ID` - From Azure App Registration
   - `TENANT_ID` - From Azure App Registration
   - `CLIENT_SECRET` - From Azure App Registration
   - `TARGET_EMAIL` - Mailbox to monitor (e.g., callback@ctmr-so.at)
   - `START_DATE` - Process emails from this date forward (ISO format)
   - `WHISPER_MODEL` - Choose: small (recommended), medium, or large

### Step 2: Build Container

```bash
# Build with default model (small)
docker-compose build

# Or build with specific model
WHISPER_MODEL=medium docker-compose build
```

**Build time:** 5-10 minutes (downloads AI model)

### Step 3: Choose Deployment Mode

#### Option A: Scheduled Job (Recommended for Production)

**Advantages:**
- Better resource usage (container stops when idle)
- Easier debugging (clear start/end)
- Standard cloud-native practice

**Setup with cron:**

```bash
# Test run first
docker-compose run --rm transcription-service

# If successful, add to cron
crontab -e

# Add this line (runs every 2 minutes):
*/2 * * * * cd /path/to/transcript && /usr/local/bin/docker-compose run --rm transcription-service >> /var/log/email-transcription.log 2>&1
```

**Setup with systemd timer:**

```bash
# Create service file: /etc/systemd/system/email-transcription.service
[Unit]
Description=Email Voice Transcription Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/path/to/transcript
ExecStart=/usr/local/bin/docker-compose run --rm transcription-service
StandardOutput=journal
StandardError=journal

# Create timer file: /etc/systemd/system/email-transcription.timer
[Unit]
Description=Run email transcription every 2 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=2min

[Install]
WantedBy=timers.target

# Enable and start
sudo systemctl enable email-transcription.timer
sudo systemctl start email-transcription.timer
sudo systemctl status email-transcription.timer
```

#### Option B: Daemon Mode (Continuous Service)

**Advantages:**
- Self-contained (no external scheduler)
- Single command deployment

**Setup:**

```bash
# Start daemon
docker-compose up -d transcription-daemon

# Check status
docker-compose ps

# View logs
docker-compose logs -f transcription-daemon
```

### Step 4: Monitor Service

**Check logs:**
```bash
# Daemon mode
docker-compose logs -f transcription-daemon

# Scheduled job mode
tail -f /var/log/email-transcription.log
# or
journalctl -u email-transcription.service -f
```

**Check resources:**
```bash
docker stats email-transcription-daemon
```

**Verify processing:**
- Send test email with WAV attachment
- Check logs for processing confirmation
- Verify transcription appended to email in mailbox

### Step 5: Adjust Configuration

**Change check interval (daemon mode only):**
```bash
# Edit .env
CHECK_INTERVAL_SECONDS=300  # 5 minutes

# Restart service
docker-compose restart transcription-daemon
```

**Change Whisper model:**
```bash
# Edit .env
WHISPER_MODEL=medium  # or large

# Rebuild container
docker-compose build

# Restart (or re-run for job mode)
docker-compose up -d transcription-daemon
```

**Change start date:**
```bash
# Edit .env
START_DATE=2024-02-01T00:00:00Z

# No rebuild needed, just restart
docker-compose restart transcription-daemon
```

## Memory Requirements

| Model | Recommended RAM | Docker Memory Limit |
|-------|----------------|---------------------|
| small | 2-3 GB | 4 GB |
| medium | 5-6 GB | 8 GB |
| large | 10-12 GB | 16 GB |

Set in docker-compose.yml or .env:
```yaml
mem_limit: 8g  # Adjust based on model
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs transcription-daemon

# Check configuration
docker-compose config
```

### Authentication errors
- Verify Azure App credentials in .env
- Check API permissions granted
- Test manually: `docker-compose run --rm transcription-service`

### Out of memory
- Check model size vs available RAM
- Reduce WHISPER_MODEL (large → medium → small)
- Increase system RAM or Docker memory limit

### No emails processed
- Check START_DATE is before emails you want to process
- Verify TARGET_EMAIL is correct
- Check emails have WAV attachments
- Look for transcription marker (already processed)

## Kubernetes Deployment (Optional)

For Kubernetes, use CronJob for scheduled execution:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: email-transcription
spec:
  schedule: "*/2 * * * *"  # Every 2 minutes
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: transcription
            image: email-transcription:latest
            command: ["python", "-u", "-m", "app.main", "--mode", "once"]
            envFrom:
            - secretRef:
                name: email-transcription-secrets
            resources:
              requests:
                memory: "4Gi"
                cpu: "1000m"
              limits:
                memory: "8Gi"
                cpu: "2000m"
          restartPolicy: OnFailure
```

## Maintenance

### Update service
```bash
# Pull latest code
git pull

# Rebuild
docker-compose build

# Restart
docker-compose up -d transcription-daemon
# or update cron/systemd timer
```

### View statistics
```bash
# Count processed emails (look for "processed" in logs)
docker-compose logs transcription-daemon | grep "processed"

# Check average processing time
docker-compose logs transcription-daemon | grep "complete in"
```

### Backup configuration
```bash
# Backup .env file securely
cp .env .env.backup
chmod 600 .env.backup
```

## Security Checklist

- [ ] .env file has restricted permissions (600)
- [ ] .env file is NOT in version control
- [ ] CLIENT_SECRET rotated regularly (every 6-12 months)
- [ ] Minimal API permissions granted
- [ ] Container runs as non-root user (default in Dockerfile)
- [ ] Logs don't contain sensitive data
- [ ] Server has firewall configured
- [ ] Docker daemon secured

## Support Contacts

For technical issues:
- Review README.md for detailed documentation
- Check container logs for error messages
- Verify Microsoft 365 API status

---

**Pro Tip:** Start with scheduled job mode (Option A) for easier debugging and monitoring. Switch to daemon mode later if preferred.
