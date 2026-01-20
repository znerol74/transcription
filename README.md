# Email Voice Message Transcription Service

Automated service that monitors a Microsoft 365 mailbox, transcribes WAV audio attachments using OpenAI Whisper, and appends transcriptions directly to email bodies.

## Features

- Monitors Microsoft 365 mailbox for emails with WAV attachments
- Transcribes audio using state-of-the-art Whisper AI model
- Appends transcriptions to original emails while preserving read/unread status
- Configurable transcription quality (tiny/base/small/medium/large models)
- Two deployment modes: scheduled job or continuous daemon
- Production-ready Docker container
- Comprehensive logging and error handling

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Microsoft 365 App Registration with required permissions:
  - `Mail.ReadWrite` (Application permission)
  - `Mail.ReadWrite.Shared` (if accessing shared mailbox)

### 2. Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Microsoft 365 credentials and preferences:

```env
CLIENT_ID=your-azure-app-client-id
TENANT_ID=your-azure-tenant-id
CLIENT_SECRET=your-azure-app-client-secret
TARGET_EMAIL=callback@your-domain.com
WHISPER_MODEL=small
START_DATE=2024-01-01T00:00:00Z
```

### 3. Build Docker Image

```bash
docker-compose build
```

This downloads the Whisper model during build time (only once).

### 4. Run Service

**Option A: Scheduled Job Mode (Recommended)**

Run once and exit - schedule externally via cron/systemd/Kubernetes:

```bash
# Run manually
docker-compose run --rm transcription-service

# Or setup cron (every 2 minutes):
# Add to /etc/cron.d/email-transcription:
*/2 * * * * cd /path/to/project && docker-compose run --rm transcription-service >> /var/log/transcription.log 2>&1
```

**Option B: Daemon Mode**

Run continuously with internal scheduler:

```bash
docker-compose up -d transcription-daemon
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLIENT_ID` | ✅ | - | Microsoft 365 App Client ID |
| `TENANT_ID` | ✅ | - | Microsoft 365 Tenant ID |
| `CLIENT_SECRET` | ✅ | - | Microsoft 365 App Client Secret |
| `TARGET_EMAIL` | ✅ | - | Email address of mailbox to monitor |
| `CHECK_INTERVAL_SECONDS` | ❌ | 120 | How often to check emails (daemon mode) |
| `START_DATE` | ❌ | 2024-01-01T00:00:00Z | Only process emails after this date |
| `WHISPER_MODEL` | ❌ | small | AI model size (tiny/base/small/medium/large) |
| `TRANSCRIPTION_MARKER` | ❌ | `--- AUTOMATISCHES TRANSKRIPT ---` | Text marker for transcriptions |
| `LOG_LEVEL` | ❌ | INFO | Logging verbosity |

### Whisper Model Selection

Choose based on accuracy vs. performance trade-off:

| Model | RAM | Speed | Quality | Use Case |
|-------|-----|-------|---------|----------|
| `tiny` | ~1GB | Fastest | Basic | Testing only |
| `base` | ~1GB | Very Fast | Good | High volume, lower quality acceptable |
| `small` | ~2GB | Fast | Very Good | **Recommended - Best balance** |
| `medium` | ~5GB | Moderate | Excellent | Better accuracy needed |
| `large` | ~10GB | Slow | Best | Maximum accuracy critical |

## Microsoft 365 App Registration

### Setup Steps

1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
2. Click "New registration"
3. Name: "Email Transcription Service"
4. Supported account types: "Single tenant"
5. Click "Register"

### Configure API Permissions

1. Go to "API permissions"
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Choose "Application permissions"
5. Add:
   - `Mail.ReadWrite` (required)
   - `Mail.ReadWrite.Shared` (if using shared mailbox)
6. Click "Grant admin consent"

### Create Client Secret

1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Description: "Transcription Service"
4. Expires: Choose duration (recommended: 24 months)
5. Click "Add"
6. **Copy the secret value immediately** (only shown once)

### Get IDs

- **CLIENT_ID**: Application (client) ID from Overview page
- **TENANT_ID**: Directory (tenant) ID from Overview page
- **CLIENT_SECRET**: Secret value from previous step

## Usage

### Monitoring Logs

**Scheduled Job Mode:**
```bash
# View output from last run
docker-compose run --rm transcription-service
```

**Daemon Mode:**
```bash
# View live logs
docker-compose logs -f transcription-daemon

# View recent logs
docker-compose logs --tail=100 transcription-daemon
```

### Resource Monitoring

```bash
# Check memory/CPU usage
docker stats email-transcription-daemon

# Or for job mode (while running)
docker stats email-transcription
```

### Stopping Service

**Daemon Mode:**
```bash
docker-compose down
```

**Scheduled Job:**
```bash
# Remove cron entry or disable systemd timer
```

## How It Works

1. Service connects to Microsoft 365 mailbox
2. Fetches emails with WAV attachments received after `START_DATE`
3. Skips emails already containing the transcription marker
4. For each new email:
   - Downloads WAV attachments
   - Transcribes using Whisper AI
   - Appends transcription to email body
   - Preserves original read/unread status
5. Repeats based on deployment mode

### Email Example

**Before:**
```
Subject: Voice Message from Patient
Attachments: VoiceMessage_1.wav

[Original email body]
```

**After:**
```
Subject: Voice Message from Patient
Attachments: VoiceMessage_1.wav

[Original email body]

--- AUTOMATISCHES TRANSKRIPT ---
[VoiceMessage_1.wav]
Grüß Gott, ich bräuchte einen Termin für ein MRT fürs Knie. Danke.
```

## Troubleshooting

### Authentication Fails

- Verify CLIENT_ID, TENANT_ID, CLIENT_SECRET are correct
- Check API permissions are granted (admin consent required)
- Ensure TARGET_EMAIL exists and is accessible
- For shared mailboxes, verify `Mail.ReadWrite.Shared` permission

### No Emails Processed

- Check START_DATE - emails before this date are ignored
- Verify emails have WAV attachments
- Check if emails already have transcription marker
- Review logs for filtering details

### Transcription Fails

- Ensure WAV files are valid audio format
- Check memory limits (increase if using large model)
- Verify ffmpeg is installed (included in Docker image)
- Review logs for specific Whisper errors

### Container OOM (Out of Memory)

- Reduce WHISPER_MODEL (large → medium → small)
- Increase MEMORY_LIMIT in docker-compose.yml
- Check host system has enough RAM

## Development

### Local Testing (without Docker)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run service
python -m app.main --mode once
```

### Project Structure

```
transcript/
├── app/
│   ├── __init__.py
│   ├── main.py              # Service entry point
│   ├── config.py            # Configuration management
│   ├── email_client.py      # Microsoft 365 operations
│   ├── transcription.py     # Whisper transcription
│   └── utils.py             # Logging and helpers
├── data/                     # Test audio files
├── tests/                    # Unit tests
├── Dockerfile                # Container definition
├── docker-compose.yml        # Deployment configuration
├── requirements.txt          # Python dependencies
├── .env.example             # Configuration template
└── README.md                # This file
```

## Security Considerations

- Never commit `.env` file to version control
- Rotate CLIENT_SECRET regularly
- Use minimal API permissions required
- Run container as non-root user (configured in Dockerfile)
- Review logs for sensitive information before sharing

## Support

For issues, please check:

1. Docker logs for error details
2. Microsoft 365 API permissions and quotas
3. Network connectivity to Microsoft services
4. System resources (RAM, CPU, disk space)

## License

MIT License - See LICENSE file for details

## Credits

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [O365 Python Library](https://github.com/O365/python-o365) - Microsoft 365 API

---

**Note**: This service processes sensitive audio data. Ensure compliance with data protection regulations (GDPR, HIPAA, etc.) when handling voice messages containing personal information.
