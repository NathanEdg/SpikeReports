# App Home Dashboard Setup Guide

## Overview
The reportbot now includes a Slack App Home dashboard that displays all generated daily report summaries, sorted by date.

## Features
- View all historical daily report summaries
- Summaries are automatically sorted by date (newest first)
- Click "View Details" to see the full master report and team summaries
- Persistent storage using SQLite database

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

### 3. Run the Bot

Start the bot as usual:
```bash
python app.py
```

The SQLite database (`summaries.db`) will be created automatically in the project root directory.

### 4. Access the Dashboard

1. Open Slack
2. Find your reportbot in the Apps section
3. Click on the bot name to open the conversation
4. Click the **Home** tab (not Messages)
5. You'll see the dashboard with all summaries

## How It Works

### Database Storage
- All generated summaries are automatically saved to `summaries.db`
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
- `utils/database.py` - SQLite database management
- `handlers/app_home.py` - App Home dashboard handlers

Modified files:
- `app.py` - Registered App Home handler
- `jobs/midnight_report.py` - Added database storage after report generation

## Database Schema

```sql
CREATE TABLE summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    master_report TEXT NOT NULL,
    channel_summaries TEXT NOT NULL,
    total_reports INTEGER NOT NULL,
    created_at TEXT NOT NULL
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
- Ensure the bot has write permissions in the project directory
- The `summaries.db` file will be created automatically
- Check logs for specific database errors

## Future Enhancements

Potential improvements:
- Add pagination for large numbers of summaries
- Add date filtering/search functionality
- Export summaries to CSV or PDF
- Add delete/archive functionality for old summaries
- Add statistics and charts
