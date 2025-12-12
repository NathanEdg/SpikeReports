import requests
import os
from dotenv import load_dotenv

load_dotenv()

headers = {
  'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
  'Content-Type': 'application/json',
}

response = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json={
  'model': 'openai/gpt-oss-120b:free',
  'messages': [{ 'role': 'user', 'content': 'Hello' }],
  'provider': {
    'sort': 'throughput',
  },
})

print(response.json())

