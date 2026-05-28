import json
import requests
from datetime import datetime

class WebhookNotifier:
    """Dispatches asynchronous HTTP POST requests (Webhooks) with JSON payloads."""
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    def send_alert(self, equipment_id: str, risk_level: str, probability: float, recommendations: list) -> dict:
        """Sends a structured alert payload to the configured webhook URL."""
        if not self.webhook_url or self.webhook_url == "https://your-webhook-endpoint.com/alert":
            return {"success": False, "message": "Webhook URL not configured or default used."}
            
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "equipment_id": equipment_id,
            "alert_type": "PREDICTIVE_MAINTENANCE",
            "severity": risk_level.upper(),
            "failure_probability": round(probability, 3),
            "recommended_actions": recommendations
        }
        
        try:
            # Send HTTP POST (timeout set to prevent hanging)
            response = requests.post(
                self.webhook_url, 
                json=payload, 
                headers={"Content-Type": "application/json"},
                timeout=5.0
            )
            response.raise_for_status()
            return {"success": True, "status_code": response.status_code, "message": "Webhook dispatched successfully."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": str(e)}
