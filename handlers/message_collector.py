from slack_bolt import App
from utils.storage import storage
from utils.logger import logger

def handle_message(event, client):
    """Handle messages in report threads."""
    try:
        # Debug: Log all message events
        logger.info(f"Received message event: channel={event.get('channel')}, "
                   f"thread_ts={event.get('thread_ts')}, ts={event.get('ts')}")
        
        # Check if this is a thread reply
        if 'thread_ts' not in event:
            return
        
        channel_id = event['channel']
        thread_ts = event['thread_ts']
        
        # Check if this thread is one of our report threads
        stored_thread_ts = storage.get_thread_timestamp(channel_id)
        if stored_thread_ts != thread_ts:
            return
        
        # Don't collect bot messages
        if event.get('bot_id'):
            return
        
        user_id = event['user']
        text = event['text']
        
        # Get user info
        try:
            user_info = client.users_info(user=user_id)
            username = user_info['user']['real_name'] or user_info['user']['name']
        except Exception as e:
            logger.warning(f"Could not fetch user info for {user_id}: {e}")
            username = user_id
        
        # Store the report
        storage.add_report(channel_id, user_id, username, text)
        logger.info(f"Collected report from {username} in channel {channel_id}")
        
        # React to the message to confirm receipt
        client.reactions_add(
            channel=channel_id,
            timestamp=event['ts'],
            name='white_check_mark'
        )
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")

def register_message_collector(app: App):
    """Register the message collector handler."""
    app.event("message")(handle_message)
    logger.info("Registered message collector handler")
