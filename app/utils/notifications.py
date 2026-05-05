import os
import aiohttp
from datetime import datetime
from typing import Optional

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

async def send_discord_notification(endpoint: str, method: str, team_id: Optional[str] = None, ip: Optional[str] = None):
    """Envia notificação para o Discord sem travar a requisição"""
    
    if not DISCORD_WEBHOOK_URL:
        return  
    
    try:
        embed = {
            "title": "🔔 HLTV API Request",
            "color": 5814783,  # azul
            "fields": [
                {"name": "Endpoint", "value": endpoint, "inline": True},
                {"name": "Method", "value": method, "inline": True},
                {"name": "Team ID", "value": team_id or "N/A", "inline": True},
                {"name": "IP", "value": ip or "Unknown", "inline": True},
                {"name": "Timestamp", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": False}
            ],
            "footer": {"text": "HLTV API Monitor"}
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
    except Exception as e:
        # não deixa a notificação quebrar a API
        print(f"Failed to send notification: {e}")