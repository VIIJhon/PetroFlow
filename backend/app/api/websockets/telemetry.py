"""
WebSocket Telemetry Handler
Real-time telemetry data streaming
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import logging
import json
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific connection"""
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connections"""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")


manager = ConnectionManager()


async def send_telemetry_pusher(websocket: WebSocket):
    """Periodically pushes physically grounded telemetry data to the client"""
    import random
    import time
    try:
        while True:
            # Physically grounded fluctuations
            oee = 84.5 + random.uniform(-0.4, 0.4)
            flow = 240.2 + random.uniform(-2.5, 2.5)
            press = 318.4 + random.uniform(-4.0, 4.0)
            vibr = 2.3 + random.uniform(-0.1, 0.1)
            temp = 72.8 + random.uniform(-0.3, 0.3)
            
            # Simple cavitation indicator if vibration spikes
            cav_idx = 0.12 + (vibr - 2.2) * 0.05
            
            sensor_data = {
                "rpm": round(2950.0 + random.uniform(-15, 15), 1),
                "vibration": round(vibr, 2),
                "temperature": round(temp, 1),
                "pumpFlow": round(flow, 1),
                "dischargePressure": round(press, 1),
                "npshAvailable": round(max(1.0, 16.0 - (vibr * 0.8)), 2),
                "oee": round(oee, 2),
                "flow_rate_gpm": round(flow, 2),
                "discharge_pressure_psi": round(press, 2),
                "vibration_rms": round(vibr, 2),
                "temperature_c": round(temp, 2),
                "cavitation_index": round(max(0.01, cav_idx), 3),
                "status": "Normal" if vibr < 3.0 else "Alerta (Vibración Alta)"
            }
            
            payload = {
                "type": "telemetry",
                "timestamp": time.time(),
                "data": sensor_data,
                "payload": {
                    "equipmentId": "bomba",
                    "sensorData": sensor_data
                }
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(2.5)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in send_telemetry_pusher: {e}")


@router.websocket("/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time telemetry data
    Now with active periodic background pushes
    """
    await manager.connect(websocket)
    push_task = asyncio.create_task(send_telemetry_pusher(websocket))
    
    try:
        while True:
            # Receive data from client (e.g. commands, subscription updates)
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Process message
            if message.get("type") == "subscribe":
                device_id = message.get("device_id")
                logger.info(f"Client subscribed to device: {device_id}")
                
                await manager.send_personal_message(
                    json.dumps({
                        "type": "subscription_confirmed",
                        "device_id": device_id
                    }),
                    websocket
                )
            
            elif message.get("type") == "unsubscribe":
                device_id = message.get("device_id")
                logger.info(f"Client unsubscribed from device: {device_id}")
            
            # Echo back for testing
            await manager.send_personal_message(
                json.dumps({"echo": message}),
                websocket
            )
            
    except WebSocketDisconnect:
        push_task.cancel()
        manager.disconnect(websocket)
        logger.info("Client disconnected")
    
    except Exception as e:
        push_task.cancel()
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)



@router.websocket("/simulation")
async def simulation_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time simulation updates
    """
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle simulation commands
            if message.get("command") == "start":
                # TODO: Start simulation
                await manager.send_personal_message(
                    json.dumps({"status": "simulation_started"}),
                    websocket
                )
            
            elif message.get("command") == "stop":
                # TODO: Stop simulation
                await manager.send_personal_message(
                    json.dumps({"status": "simulation_stopped"}),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"Simulation WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_telemetry_update(data: dict):
    """
    Broadcast telemetry update to all connected clients
    Call this from MQTT handler or other data sources
    """
    message = json.dumps({
        "type": "telemetry_update",
        "data": data,
        "timestamp": data.get("timestamp")
    })
    await manager.broadcast(message)


async def broadcast_alarm(alarm_data: dict):
    """Broadcast alarm to all connected clients"""
    message = json.dumps({
        "type": "alarm",
        "data": alarm_data
    })
    await manager.broadcast(message)