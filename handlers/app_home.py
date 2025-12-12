import re
from datetime import datetime
from slack_bolt import App
from utils.database import summary_db
from utils.logger import logger


def build_app_home_view(summaries: list, page: int = 0) -> dict:
    """
    Build the App Home view with summaries dashboard.
    
    Args:
        summaries: List of summary dictionaries
        page: Current page number (for pagination)
    
    Returns:
        View dictionary for App Home
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Daily Report Summaries Dashboard"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"View all generated daily report summaries. Total summaries: *{summary_db.get_summary_count()}*"
            }
        },
        {
            "type": "divider"
        }
    ]
    
    if not summaries:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_No summaries available yet. Summaries will appear here after the first daily report is generated._"
            }
        })
    else:
        # Add each summary as a collapsible section
        for summary in summaries:
            date_obj = datetime.fromisoformat(summary['date'])
            formatted_date = date_obj.strftime('%B %d, %Y')
            
            # Create the summary header with date and stats
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📅 {formatted_date}*\n_{summary['total_reports']} total reports_"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Details"
                    },
                    "value": f"view_summary_{summary['id']}",
                    "action_id": f"view_summary_{summary['id']}"
                }
            })
            
            # Add master report preview (truncated)
            master_preview = summary['master_report']
            if len(master_preview) > 300:
                master_preview = master_preview[:300] + "..."
            
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": master_preview
                    }
                ]
            })
            
            blocks.append({
                "type": "divider"
            })
    
    return {
        "type": "home",
        "blocks": blocks
    }


def build_summary_detail_view(summary: dict) -> dict:
    """
    Build a detailed view modal for a specific summary.
    
    Args:
        summary: Summary dictionary
    
    Returns:
        Modal view dictionary
    """
    date_obj = datetime.fromisoformat(summary['date'])
    formatted_date = date_obj.strftime('%B %d, %Y')
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 Report for {formatted_date}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Total Reports:* {summary['total_reports']}"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Master Summary*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": summary['master_report']
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Team Summaries*"
            }
        }
    ]
    
    # Add each team summary
    for channel_summary in summary['channel_summaries']:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{channel_summary['subteam']}* ({channel_summary['report_count']} {'report' if channel_summary['report_count'] == 1 else 'reports'})\n{channel_summary['summary']}"
            }
        })
    
    return {
        "type": "modal",
        "title": {
            "type": "plain_text",
            "text": "Daily Report Details"
        },
        "close": {
            "type": "plain_text",
            "text": "Close"
        },
        "blocks": blocks
    }


def handle_app_home_opened(client, event, logger):
    """Handle the app_home_opened event."""
    try:
        user_id = event["user"]
        
        # Get summaries from database (most recent first)
        summaries = summary_db.get_all_summaries(limit=50)
        
        # Build and publish the view
        view = build_app_home_view(summaries)
        
        client.views_publish(
            user_id=user_id,
            view=view
        )
        
        logger.info(f"App Home opened by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling app_home_opened: {e}", exc_info=True)


def handle_view_summary_action(ack, body, client, logger):
    """Handle the view summary button click."""
    ack()
    
    try:
        # Extract summary ID from action
        action = body['actions'][0]
        summary_id = int(action['value'].replace('view_summary_', ''))
        
        # Get the summary from database
        summaries = summary_db.get_all_summaries(limit=1000)  # Get all to find by ID
        summary = next((s for s in summaries if s['id'] == summary_id), None)
        
        if summary:
            # Build and open modal
            view = build_summary_detail_view(summary)
            
            client.views_open(
                trigger_id=body['trigger_id'],
                view=view
            )
            
            logger.info(f"Opened detail view for summary {summary_id}")
        else:
            logger.error(f"Summary {summary_id} not found")
    
    except Exception as e:
        logger.error(f"Error handling view_summary action: {e}", exc_info=True)


def register_app_home_handler(app: App):
    """Register the App Home event handlers."""
    
    # Handle app home opened event
    @app.event("app_home_opened")
    def app_home_opened(client, event, logger):
        handle_app_home_opened(client, event, logger)
    
    # Handle view summary button actions
    @app.action(re.compile(r"^view_summary_"))
    def view_summary_button(ack, body, client, logger):
        handle_view_summary_action(ack, body, client, logger)
    
    logger.info("Registered App Home handlers")
