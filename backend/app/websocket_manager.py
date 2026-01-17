# backend/app/websocket_manager.py
"""
WebSocket Connection Manager for Real-Time Updates
Handles client connections and broadcasts with comprehensive error handling
"""

from fastapi import WebSocket
from typing import Dict, Set, List
import json
import logging
from datetime import datetime
import asyncio

# Use dedicated WebSocket logger
logger = logging.getLogger('websocket')

class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        # Active connections: {user_id: set of WebSocket connections}
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # All connections for broadcast to everyone
        self.all_connections: Set[WebSocket] = set()
        
    async def connect(self, websocket: WebSocket, user_id: int = None):
        """Accept and register a new WebSocket connection"""
        try:
            await websocket.accept()
            
            # Add to all connections
            self.all_connections.add(websocket)
            
            # Add to user-specific connections if user_id provided
            if user_id:
                if user_id not in self.active_connections:
                    self.active_connections[user_id] = set()
                self.active_connections[user_id].add(websocket)
                
            logger.info(f"✅ WebSocket connected | User: {user_id} | Total connections: {len(self.all_connections)}")
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed | User: {user_id} | Error: {str(e)}", exc_info=True)
            raise
        
    def disconnect(self, websocket: WebSocket, user_id: int = None):
        """Remove a WebSocket connection with error handling"""
        try:
            # Remove from all connections
            if websocket in self.all_connections:
                self.all_connections.remove(websocket)
                
            # Remove from user-specific connections
            if user_id and user_id in self.active_connections:
                if websocket in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(websocket)
                # Clean up empty sets
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    
            logger.info(f"🔌 WebSocket disconnected | User: {user_id} | Remaining: {len(self.all_connections)}")
            
        except Exception as e:
            logger.error(f"❌ Error during disconnect | User: {user_id} | Error: {str(e)}", exc_info=True)
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to specific user's connections with error handling"""
        if user_id not in self.active_connections:
            logger.warning(f"⚠️ User {user_id} has no active connections")
            return
            
        message_str = json.dumps(message)
        disconnected = set()
        sent_count = 0
        
        for connection in self.active_connections[user_id]:
            try:
                await asyncio.wait_for(
                    connection.send_text(message_str),
                    timeout=5.0  # 5 second timeout
                )
                sent_count += 1
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Timeout sending to user {user_id}")
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"❌ Error sending to user {user_id}: {str(e)}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn, user_id)
        
        if sent_count > 0:
            logger.debug(f"📤 Sent personal message to user {user_id} ({sent_count} connections)")
    
    async def broadcast(self, message: dict, exclude_user: int = None):
        """
        Broadcast message to all connected clients with comprehensive error handling
        
        Args:
            message: Dictionary to broadcast
            exclude_user: Optional user_id to exclude from broadcast
        """
        if not self.all_connections:
            logger.debug("📭 No active connections to broadcast to")
            return
        
        message_str = json.dumps(message)
        disconnected = set()
        sent_count = 0
        failed_count = 0
        
        for connection in self.all_connections:
            # Skip if this connection belongs to excluded user
            if exclude_user:
                user_connections = self.active_connections.get(exclude_user, set())
                if connection in user_connections:
                    continue
            
            try:
                await asyncio.wait_for(
                    connection.send_text(message_str),
                    timeout=5.0  # 5 second timeout per connection
                )
                sent_count += 1
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Broadcast timeout for connection")
                disconnected.add(connection)
                failed_count += 1
            except Exception as e:
                logger.error(f"❌ Broadcast error: {str(e)}")
                disconnected.add(connection)
                failed_count += 1
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
        
        logger.info(f"📡 Broadcast complete | Sent: {sent_count} | Failed: {failed_count} | Type: {message.get('type')}")
    
    async def broadcast_equipment_update(self, equipment_id: int, action: str, data: dict = None):
        """Broadcast equipment status change with error handling"""
        try:
            message = {
                'type': 'equipment_update',
                'action': action,  # 'update', 'create', 'delete', 'status_change'
                'equipment_id': equipment_id,
                'data': data,
                'timestamp': datetime.utcnow().isoformat()
            }
            await self.broadcast(message)
            logger.info(f"🔧 Equipment {action} | ID: {equipment_id} | Broadcasted to {len(self.all_connections)} clients")
        except Exception as e:
            logger.error(f"❌ Failed to broadcast equipment update | ID: {equipment_id} | Error: {str(e)}", exc_info=True)
    
    async def broadcast_session_update(self, session_id: int, action: str, data: dict = None):
        """Broadcast session change (start/end)"""
        message = {
            'type': 'session_update',
            'action': action,  # 'started', 'ended', 'updated'
            'session_id': session_id,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.broadcast(message)
        logger.info(f"Broadcasted session update: {action} for session {session_id}")
    
    async def broadcast_sample_update(self, submission_id: int, action: str, data: dict = None, recipient_user_id: int = None):
        """Broadcast sample submission update"""
        message = {
            'type': 'sample_update',
            'action': action,  # 'new', 'status_changed', 'new_message'
            'submission_id': submission_id,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # If recipient specified, send to them specifically
        if recipient_user_id:
            await self.send_personal_message(message, recipient_user_id)
        else:
            await self.broadcast(message)
            
        logger.info(f"Broadcasted sample update: {action} for submission {submission_id}")
    
    async def broadcast_notification(self, user_id: int, notification_data: dict):
        """Send notification to specific user"""
        message = {
            'type': 'notification',
            'data': notification_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.send_personal_message(message, user_id)
        logger.info(f"Sent notification to user {user_id}")
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.all_connections)
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of connections for specific user"""
        return len(self.active_connections.get(user_id, set()))

# Global connection manager instance
manager = ConnectionManager()
