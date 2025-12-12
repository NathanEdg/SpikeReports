from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from slack_bolt import App
from utils.storage import storage
from utils.logger import logger
from services.openrouter import openrouter_client
import json
import os
import pytz
import time

def load_config():
    """Load configuration from JSON file."""
    config_file = os.getenv('CONFIG_FILE', 'config.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_and_send_reports(app: App):
    """Generate AI summaries and send master report."""
    try:
        logger.info("Starting midnight report generation")
        config = load_config()
        
        all_reports = storage.get_all_reports()
        
        if not all_reports:
            logger.info("No reports to process")
            return
        
        # Generate summaries for each channel
        channel_summaries = []
        
        for idx, channel_config in enumerate(config['channels']):
            channel_id = channel_config['id']
            channel_name = channel_config['name']
            subteam = channel_config['subteam']
            
            reports = storage.get_reports(channel_id)
            
            if reports:
                logger.info(f"Processing {len(reports)} reports for {channel_name}")
                
                summary = openrouter_client.summarize_channel_reports(
                    channel_name, subteam, reports
                )
                
                channel_summaries.append({
                    'channel_id': channel_id,
                    'channel_name': channel_name,
                    'subteam': subteam,
                    'summary': summary,
                    'report_count': len(reports)
                })
            else:
                logger.info(f"No reports for {channel_name}")
        
        # Generate master report
        if channel_summaries:            
            master_report = openrouter_client.generate_master_report(channel_summaries)
            
            # Format the master report message - use separate blocks for better formatting
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Daily Master Report"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": master_report
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Team Summaries:*"
                    }
                }
            ]
            
            # Add individual team summaries
            for summary in channel_summaries:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{summary['subteam']}* ({summary['report_count']} {'report' if summary['report_count'] == 1 else 'reports'})\n{summary['summary']}"
                    }
                })
            
            # Post to master report channel
            master_channel = config['masterReportChannel']
            response = app.client.chat_postMessage(
                channel=master_channel,
                text="📊 Daily Master Report",
                blocks=blocks
            )
            
            logger.info(f"Posted master report to {master_channel}")
            
            # Generate meeting summary and post as a thread reply
            meeting_summary = openrouter_client.summarize_meeting(channel_summaries)
            
            # Post meeting summary as a threaded message
            app.client.chat_postMessage(
                channel=master_channel,
                thread_ts=response["ts"],
                text="📝 Meeting Summary",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": meeting_summary
                        }
                    }
                ]
            )
            
            logger.info("Posted meeting summary thread reply")
        
        # Clear all reports for the next day
        storage.clear_all()
        logger.info("Cleared all reports and thread timestamps")
        
    except Exception as e:
        logger.error(f"Error generating reports: {e}", exc_info=True)

def setup_scheduler(app: App):
    """Set up the midnight report scheduler."""
    timezone_str = os.getenv('TIMEZONE', 'America/New_York')
    timezone = pytz.timezone(timezone_str)
    
    scheduler = BackgroundScheduler(timezone=timezone)
    
    # Schedule for midnight
    trigger = CronTrigger(hour=0, minute=0, timezone=timezone)
    scheduler.add_job(
        lambda: generate_and_send_reports(app),
        trigger=trigger,
        id='midnight_report',
        name='Generate and send daily reports',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started - will run at midnight {timezone_str}")
    
    return scheduler

def trigger_report_now(app: App):
    """Manually trigger report generation for testing."""
    logger.info("Manually triggering report generation")
    generate_and_send_reports(app)
