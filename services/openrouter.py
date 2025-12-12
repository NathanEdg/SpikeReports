import requests
import os
import time
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from utils.logger import logger

# Load environment variables before client instantiation
load_dotenv()

class OpenRouterClient:
    """Client for interacting with OpenRouter API."""
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.model = os.getenv('AI_MODEL', 'google/gemini-2.0-flash-exp:free')
        self.base_url = 'https://openrouter.ai/api/v1'
        self.fallback_model = 'meta-llama/llama-3.3-70b-instruct:free'
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    
    def _make_request(self, messages: List[Dict[str, str]], max_retries: int = 3) -> str:
        """Make a request to OpenRouter API with exponential backoff retry logic."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Title': 'Slack Report Bot'
        }
        
        payload = {
            'model': self.model,
            'messages': messages,
            'provider': {'sort': 'throughput'}
        }
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Making OpenRouter API request (attempt {attempt + 1}/{max_retries})")

                response = requests.post(
                    f'{self.base_url}/chat/completions',
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=60
                )

                if response.status_code == 429:
                    logger.warning("Rate limit hit. Switching to fallback model for this request.")
                    payload['model'] = self.fallback_model
                    continue

                response.raise_for_status()

                data = response.json()
                content = data['choices'][0]['message']['content']
                logger.info("Successfully received response from OpenRouter")
                return content
                
            except requests.exceptions.RequestException as e:
                logger.error(f"OpenRouter API error (attempt {attempt + 1}/{max_retries}): {e}")
                
                # If this is not the last attempt, wait before retrying
                if attempt < max_retries - 1:
                    # Exponential backoff: 2, 4, 8 seconds
                    wait_time = 2 ** (attempt + 1)
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    # Last attempt failed, raise the exception
                    raise
                
        return ""
    
    def summarize_channel_reports(self, channel_name: str, subteam: str, reports: List[Dict[str, Any]]) -> str:
        """Summarize reports from a single channel."""
        if not reports:
            return f"No reports submitted for {subteam}."
        
        # Format reports for AI
        reports_text = "\n\n".join([
            f"**{report['username']}**: {report['text']}"
            for report in reports
        ])
        
        prompt = f"""Summarize the following daily reports from the {subteam} team.

Team reports:
{reports_text}

Create a concise 2-3 sentence summary covering:
- Main accomplishments
- Any blockers or challenges  
- Key themes

Write ONLY the summary. Do not include meta-commentary, notes, or explanations about your process."""
        
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        
        logger.info(f"Generating summary for {channel_name} ({subteam})")
        return self._make_request(messages)
    
    def generate_master_report(self, channel_summaries: List[Dict[str, str]]) -> str:
        """Generate a master report from all channel summaries."""
        if not channel_summaries:
            return "No reports were submitted today."
        
        # Format summaries for AI
        summaries_text = "\n\n".join([
            f"**{summary['subteam']}**:\n{summary['summary']}"
            for summary in channel_summaries
        ])
        
        prompt = f"""Create a master daily report from these team summaries:

{summaries_text}

Produce a concise executive summary using short, information-dense bullet points. Do NOT write paragraphs.

Include exactly three sections:

*Key Accomplishments (cross-team highlights only)*:
• ...

*Themes & Patterns (trends across multiple teams)*:
• ...

*Blockers & Risks (major issues requiring attention)*:
• ...

Use simple bullets (•) only. No bold, no italics, no code blocks, no special Markdown. Include the single astrisk (*) in the section headers.
Focus on the most important, decision-relevant insights.  
Write ONLY the bullet-point executive summary with the three sections.
"""
        logger.info(f"prompt for master report: {prompt}")
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        
        logger.info("Generating master report from all channel summaries")
        return self._make_request(messages)

# Global client instance
openrouter_client = OpenRouterClient()
