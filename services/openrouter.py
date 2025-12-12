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

Write a brief executive summary (2-3 paragraphs) covering:
1. Overall accomplishments across all teams today
2. Any cross-team themes or patterns
3. Notable blockers or challenges

Write ONLY the executive summary. Do not include notes, meta-commentary, placeholders, or instructions."""
        
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        
        logger.info("Generating master report from all channel summaries")
        return self._make_request(messages)
    
    def summarize_meeting(self, channel_summaries: List[Dict[str, str]]) -> str:
        """Generate a meeting summary answering specific questions based on team summaries."""
        if not channel_summaries:
            return "No meeting data available."
        
        # Combine all team summaries into a single text block
        summaries_text = "\n\n".join([
            f"**{summary['subteam']}** ({summary['report_count']} {'report' if summary['report_count'] == 1 else 'reports'}):\n{summary['summary']}"
            for summary in channel_summaries
        ])
        
        prompt = f"""Based on the following team summaries, answer the questions:

1. What was accomplished in the previous meeting?
2. Which goals were met or not met, and why?
3. Identify any blockers or risks.
4. What are the next‑meeting goals and projected milestones?

Team Summaries:
{summaries_text}

Provide concise bullet points for each question."""
        
        messages = [{"role": "user", "content": prompt}]
        
        logger.info("Generating meeting summary using OpenRouter")
        return self._make_request(messages)

# Global client instance
openrouter_client = OpenRouterClient()
