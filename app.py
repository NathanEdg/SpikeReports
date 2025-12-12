import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from handlers.report_action import register_report_action
from handlers.message_collector import register_message_collector
from jobs.midnight_report import setup_scheduler, trigger_report_now
from utils.logger import logger

# Load environment variables
load_dotenv()

# Initialize Slack app
app = App(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET")
)

# Register handlers
register_report_action(app)
register_message_collector(app)

# Set up scheduler
scheduler = setup_scheduler(app)

# Add a test command to manually trigger reports (for testing)
@app.command("/trigger_report")
def handle_trigger_report(ack, command, client):
    """Handle manual report trigger command."""
    ack()
    user_id = command['user_id']
    
    try:
        trigger_report_now(app)
        client.chat_postEphemeral(
            channel=command['channel_id'],
            user=user_id,
            text="✅ Report generation triggered manually!"
        )
    except Exception as e:
        logger.error(f"Error triggering report: {e}")
        client.chat_postEphemeral(
            channel=command['channel_id'],
            user=user_id,
            text=f"❌ Error triggering report: {str(e)}"
        )

def main():
    """Start the Slack bot."""
    logger.info("Starting Slack Report Bot")
    logger.info(f"Using AI Model: {os.getenv('AI_MODEL')}")
    logger.info(f"Timezone: {os.getenv('TIMEZONE')}")
    
    # Start Socket Mode handler
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    logger.info("Socket Mode handler initialized")
    
    try:
        handler.start()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        scheduler.shutdown()
        logger.info("Scheduler stopped")

if __name__ == "__main__":
    main()
