from slack_bolt import App
from utils.storage import storage
from utils.logger import logger
import json

def load_config():
    """Load configuration from JSON file."""
    import os
    config_file = os.getenv('CONFIG_FILE', 'config.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def handle_start_report_function(ack, complete, fail, client):
    """Handle the 'Start Daily Report' function for Slack Workflows."""
    ack()
    
    try:
        config = load_config()
        logger.info("Starting daily report collection via workflow function")
        
        for channel in config['channels']:
            channel_id = channel['id']
            channel_name = channel['name']
            subteam = channel['subteam']
            
            # Post initial message to channel
            result = client.chat_postMessage(
                channel=channel_id,
                text=f"📝 *Daily Report for {subteam}*",
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📝 Daily Report - {subteam}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Please reply to this thread with what you accomplished today!"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "_Your report will be collected and summarized at midnight._"
                        }
                    }
                ]
            )
            
            # Store the thread timestamp
            thread_ts = result['ts']
            storage.set_thread_timestamp(channel_id, thread_ts)
            
            logger.info(f"Posted report collection message to {channel_name} (thread_ts: {thread_ts})")
        
        # Complete the function successfully
        complete(outputs={
            "channels_count": len(config['channels']),
            "status": "success"
        })
        
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error starting daily report: {e}")
        fail(error=f"Failed to start daily report: {str(e)}")

def register_report_action(app: App):
    """Register the report action handler."""
    app.function("start_daily_report")(handle_start_report_function)
    logger.info("Registered 'start_daily_report' function handler for Slack Workflows")
