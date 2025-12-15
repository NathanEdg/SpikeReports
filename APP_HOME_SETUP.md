# App Home Dashboard Setup Guide

## Overview
The reportbot now includes a Slack App Home dashboard that displays all generated daily report summaries, sorted by date.

## Features
- View all historical daily report summaries
- Summaries are automatically sorted by date (newest first)
- Click "View Details" to see the full master report and team summaries
- Persistent storage using PostgreSQL database

## Setup Instructions

### 1. Enable App Home in Slack App Configuration

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Select your reportbot app
3. Navigate to **App Home** in the left sidebar
4. Under "Show Tabs", enable **Home Tab**
5. Make sure "Home Tab" is checked
6. Save your changes

### 2. Add Required Scopes (if not already added)

The app needs these OAuth scopes:
- `chat:write` - to post messages
- `commands` - for slash commands
- `channels:history` - to read messages
- `groups:history` - to read private channel messages
- `im:history` - to read direct messages
- `app_mentions:read` - to receive mentions

### 3. Configure Database

Make sure you have set up your PostgreSQL database and added the `DATABASE_URL` environment variable to your `.env` file:

```
DATABASE_URL=postgresql://username:password@host:port/database
```

The database tables will be created automatically when the bot starts.

### 4. Run the Bot

Start the bot as usual:
```bash
python app.py
```

### 5. Access the Dashboard

1. Open Slack
2. Find your reportbot in the Apps section
3. Click on the bot name to open the conversation
4. Click the **Home** tab (not Messages)
5. You'll see the dashboard with all summaries

## How It Works

### Database Storage
- All generated summaries are automatically saved to PostgreSQL
- Each summary includes:
  - Date of the report
  - Master summary text
  - Individual team summaries
  - Total report count
  - Creation timestamp

### Dashboard View
- The home tab shows a list of all summaries
- Each summary displays:
  - Report date
  - Number of reports collected
  - Preview of the master summary
  - "View Details" button for full content

### Detail Modal
When you click "View Details":
- Opens a modal with the complete report
- Shows the full master summary
- Displays all team summaries with report counts

## File Structure

New files added:
- `utils/database.py` - PostgreSQL database management
- `handlers/app_home.py` - App Home dashboard handlers

Modified files:
- `app.py` - Registered App Home handler
- `jobs/midnight_report.py` - Added database storage after report generation

## Database Schema

```sql
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    date TEXT NOT NULL,
    master_report TEXT NOT NULL,
    channel_summaries JSONB NOT NULL,
    total_reports INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE active_collections (
    channel_id TEXT PRIMARY KEY,
    thread_ts TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE collected_reports (
    id SERIAL PRIMARY KEY,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    text TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
```

## Troubleshooting

### Dashboard not showing
- Verify Home Tab is enabled in Slack App configuration
- Reinstall the app to your workspace if needed
- Check bot logs for errors

### No summaries appearing
- Summaries are only stored when the midnight report job runs
- You can manually trigger a report with `/trigger_report` command
- Check that the bot has successfully generated at least one report

### Database errors
- Verify `DATABASE_URL` is correctly formatted in your `.env` file
- Ensure PostgreSQL server is running and accessible
- Check that the database exists and credentials are correct
- Database tables will be created automatically on first run
- Check logs for specific database connection errors

## Future Enhancements

Potential improvements:
- Add pagination for large numbers of summaries
- Add date filtering/search functionality
- Export summaries to CSV or PDF
- Add delete/archive functionality for old summaries
- Add statistics and charts
