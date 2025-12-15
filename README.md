# Slack Daily Report Bot

A Python-based Slack bot that collects daily reports from team members and generates AI-powered summaries using OpenRouter. Summaries are stored in a PostgreSQL database.

## Features

- 🚀 **Global Shortcut**: Trigger daily report collection with a Slack shortcut
- 📝 **Thread-based Collection**: Team members reply in threads with their daily updates
- 🤖 **AI Summaries**: Automatic summarization using Google Gemini 2.0 Flash
- ⏰ **Scheduled Reports**: Generates master report at midnight EST
- 🔄 **Hot Reload Config**: Update channel configuration without restarting
- 💬 **Manual Trigger**: Test command to generate reports on demand

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Enable **Socket Mode** in Settings > Socket Mode
3. Create an **App-Level Token** with `connections:write` scope (save as `SLACK_APP_TOKEN`)
4. Under **OAuth & Permissions**, add these Bot Token Scopes:
   - `chat:write`
   - `chat:write.public`
   - `channels:read`
   - `users:read`
   - `reactions:add`
   - `commands`
5. Install the app to your workspace and copy the **Bot User OAuth Token** (save as `SLACK_BOT_TOKEN`)
6. Get your **Signing Secret** from Basic Information (save as `SLACK_SIGNING_SECRET`)

### 3. Create a Workflow Function

1. Go to **Interactivity & Shortcuts** in your Slack app settings
2. Enable Interactivity
3. Go to **Functions** (in the left sidebar)
4. Click **Create New Function**
5. Fill in:
   - **Name**: Start Daily Report
   - **Description**: Start collecting daily reports from team members
   - **Callback ID**: `start_daily_report`
6. **Add Output Parameters** (optional):
   - `channels_count` (number)
   - `status` (string)
7. Click **Create**

### 4. Create a Workflow (Slack Workspace)

1. Go to **Slash Commands** and create a new command:
   - **Command**: `/trigger_report`
   - **Short Description**: Manually trigger report generation
   - **Usage Hint**: (leave empty)

### 5. Get OpenRouter API Key

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up and navigate to API Keys
3. Create a new API key (save as `OPENROUTER_API_KEY`)
4. Add a payment method if needed for usage beyond free tier

### 6. Set Up PostgreSQL Database

You'll need a PostgreSQL database to store generated summaries. You can use:
- A local PostgreSQL installation
- A cloud provider like [Heroku Postgres](https://www.heroku.com/postgres), [Supabase](https://supabase.com), [Railway](https://railway.app), or [Neon](https://neon.tech)

The connection URL format is:
```
postgresql://username:password@host:port/database
```

Example:
```
postgresql://myuser:mypassword@localhost:5432/reportbot
```

### 7. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
```
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token
SLACK_APP_TOKEN=xapp-your-actual-app-token
SLACK_SIGNING_SECRET=your-actual-signing-secret
OPENROUTER_API_KEY=your-actual-openrouter-key
DATABASE_URL=postgresql://username:password@host:port/database
TIMEZONE=America/New_York
AI_MODEL=google/gemini-2.0-flash-exp:free
CONFIG_FILE=config.json
```

### 8. Configure Channels

Edit `config.json` to specify your channels and subteams:

```json
{
  "channels": [
    {
      "id": "C123456789",
      "name": "#engineering",
      "subteam": "Engineering Team"
    },
    {
      "id": "C987654321",
      "name": "#design",
      "subteam": "Design Team"
    }
  ],
  "masterReportChannel": "C111111111"
}
```

**To find channel IDs:**
1. Right-click on a channel in Slack
2. Select "View channel details"
3. Scroll to the bottom - the channel ID is at the bottom

## Usage

### Start the Bot

```bash
python app.py
```

You should see:
```
2025-12-12 11:00:00 - reportbot - INFO - Starting Slack Report Bot
2025-12-12 11:00:00 - reportbot - INFO - Using AI Model: google/gemini-2.0-flash-exp:free
2025-12-12 11:00:00 - reportbot - INFO - Timezone: America/New_York
2025-12-12 11:00:00 - reportbot - INFO - Socket Mode handler initialized
⚡️ Bolt app is running!
```

### Daily Workflow

1. **Trigger Report Collection**: 
   - **Scheduled**: Let your Slack Workflow run automatically at the time you configured
   - **Manual**: Run your workflow from the channel or Workflow Builder
2. **Team Members Respond**: They reply in the threads with what they did today
3. **Automatic Processing**: At midnight EST, the bot:
   - Collects all thread replies
   - Generates AI summaries for each channel/subteam
   - Creates a master report
   - Posts the master report to the configured channel
   - Clears the storage for the next day

### Testing

To test without waiting for midnight, use the slash command:
```
/trigger_report
```

This will immediately process all collected reports and send the master report.

### Reloading Configuration

You can update `config.json` while the bot is running. The configuration is reloaded each time:
- You trigger the daily report shortcut
- The midnight job runs
- You use the `/trigger_report` command

## Project Structure

```
reportbot/
├── app.py                          # Main application entry point
├── config.json                     # Channel and subteam configuration
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (not in git)
├── .env.example                   # Environment variables template
├── handlers/
│   ├── report_action.py           # Handles report collection shortcut
│   └── message_collector.py       # Collects thread replies
├── jobs/
│   └── midnight_report.py         # Scheduled report generation
├── services/
│   └── openrouter.py              # OpenRouter API client
└── utils/
    ├── logger.py                  # Logging configuration
    ├── storage.py                 # In-memory report storage
    └── database.py                # PostgreSQL database management
```

## Troubleshooting

**Bot doesn't respond to shortcuts:**
- Check that Socket Mode is enabled
- Verify `SLACK_APP_TOKEN` has `connections:write` scope
- Ensure the shortcut callback ID is exactly `start_daily_report`

**Reports not being collected:**
- Check bot permissions include `chat:write`, `users:read`, `reactions:add`
- Verify the bot is in the channels (or use `chat:write.public` scope)
- Check logs for any errors

**AI summaries failing:**
- Verify `OPENROUTER_API_KEY` is correct
- Check your OpenRouter account has credits
- Review logs for API errors

**Wrong timezone:**
- Update `TIMEZONE` in `.env` to your preferred timezone
- Valid values: `America/New_York`, `America/Los_Angeles`, `UTC`, etc.

**Database connection errors:**
- Verify `DATABASE_URL` is correctly formatted
- Ensure PostgreSQL server is running and accessible
- Check that database exists and credentials are correct
- Review logs for specific connection errors

## License

MIT
