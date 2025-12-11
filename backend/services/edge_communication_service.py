"""
Edge Communication Service for managing communication with edge devices.

This service handles data synchronization, command execution, and status monitoring
between the cloud system and edge devices.
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
import ssl

from backend.core.base_service import BaseService
from backend.services.camera_config_manager import EdgeDeviceConfig


class CommandType(Enum):
    """Types of commands that can be sent to edge devices."""
    START_PROCESSING = "start_processing"
    STOP_PROCESSING = "stop_processing"
    UPDATE_CONFIG = "update_config"
    RESTART_SERVICE = "restart_service"
    GET_STATUS = "get_status"
    GET_LOGS = "get_logs"
    UPDATE_MODEL = "update_model"
    SYNC_DATA = "sync_data"


class CommandStatus(Enum):
    """Status of commands sent to edge devices."""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class EdgeCommand:
    """Command to be executed on edge device."""
    
    def __init__(
        self,
        command_id: str,
        device_id: str,
        command_type: CommandType,
        payload: Dict[str, Any],
        timeout: int = 60,
        callback: Optional[Callable] = None
    ):
        self.command_id = command_id
        self.device_id = device_id
        self.command_type = command_type
        self.payload = payload
        self.timeout = timeout
        self.callback = callback
        self.status = CommandStatus.PENDING
        self.created_at = time.time()
        self.sent_at = None
        self.completed_at = None
        self.response = None
        self.error = None


class DataSyncManager:
    """Manages data synchronization between cloud and edge devices."""
    
    def __init__(self):
        self.sync_queues: Dict[str, List[Dict]] = {}
        self.last_sync_times: Dict[str, float] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_sync_data(self, device_id: str, data_type: str, data: Dict[str, Any]):
        """Add data to sync queue for a device."""
        if device_id not in self.sync_queues:
            self.sync_queues[device_id] = []
        
        sync_item = {
            "data_type": data_type,
            "data": data,
            "timestamp": time.time(),
            "sync_id": f"{device_id}_{data_type}_{int(time.time() * 1000)}"
        }
        
        self.sync_queues[device_id].append(sync_item)
        self.logger.debug(f"Added sync data for device {device_id}: {data_type}")
    
    def get_pending_sync_data(self, device_id: str) -> List[Dict]:
        """Get pending sync data for a device."""
        return self.sync_queues.get(device_id, [])
    
    def mark_synced(self, device_id: str, sync_ids: List[str]):
        """Mark data as synced and remove from queue."""
        if device_id in self.sync_queues:
            self.sync_queues[device_id] = [
                item for item in self.sync_queues[device_id]
                if item["sync_id"] not in sync_ids
            ]
            self.last_sync_times[device_id] = time.time()
            self.logger.debug(f"Marked {len(sync_ids)} items as synced for device {device_id}")
    
    def get_sync_status(self, device_id: str) -> Dict[str, Any]:
        """Get sync status for a device."""
        pending_count = len(self.sync_queues.get(device_id, []))
        last_sync = self.last_sync_times.get(device_id)
        
        return {
            "device_id": device_id,
            "pending_items": pending_count,
            "last_sync_time": last_sync,
            "time_since_last_sync": time.time() - last_sync if last_sync else None
        }


class EdgeCommunicationService(BaseService):
    """Service for managing communication with edge devices."""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Device connections
        self.device_connections: Dict[str, aiohttp.ClientSession] = {}
        self.device_configs: Dict[str, EdgeDeviceConfig] = {}
        
        # Command management
        self.pending_commands: Dict[str, EdgeCommand] = {}
        self.command_history: List[EdgeCommand] = []
        self.max_history_size = 1000
        
        # Data synchronization
        self.sync_manager = DataSyncManager()
        
        # Communication statistics
        self.comm_stats = {
            "commands_sent": 0,
            "commands_completed": 0,
            "commands_failed": 0,
            "data_synced": 0,
            "connection_errors": 0,
            "avg_response_time": 0.0
        }
        
        # Background tasks
        self.background_tasks = []
        self.stop_event = asyncio.Event()
        
        # Start background services
        asyncio.create_task(self._start_background_services())
    
    async def _start_background_services(self):
        """Start background services."""
        # Command processor
        self.background_tasks.append(
            asyncio.create_task(self._command_processor())
        )
        
        # Data sync processor
        self.background_tasks.append(
            asyncio.create_task(self._data_sync_processor())
        )
        
        # Connection monitor
        self.background_tasks.append(
            asyncio.create_task(self._connection_monitor())
        )
        
        self.logger.info("Started edge communication background services")
    
    def add_device(self, device_config: EdgeDeviceConfig) -> bool:
        """Add edge device for communication."""
        try:
            self.device_configs[device_config.device_id] = device_config
            self.logger.info(f"Added edge device for communication: {device_config.device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add edge device: {e}")
            return False
    
    def remove_device(self, device_id: str) -> bool:
        """Remove edge device from communication."""
        try:
            # Close connection if exists
            if device_id in self.device_connections:
                asyncio.create_task(self.device_connections[device_id].close())
                del self.device_connections[device_id]
            
            # Remove configuration
            if device_id in self.device_configs:
                del self.device_configs[device_id]
            
            self.logger.info(f"Removed edge device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove edge device: {e}")
            return False
    
    async def send_command(
        self,
        device_id: str,
        command_type: CommandType,
        payload: Dict[str, Any],
        timeout: int = 60,
        callback: Optional[Callable] = None
    ) -> str:
        """Send command to edge device."""
        try:
            # Generate command ID
            command_id = f"{device_id}_{command_type.value}_{int(time.time() * 1000)}"
            
            # Create command
            command = EdgeCommand(
                command_id=command_id,
                device_id=device_id,
                command_type=command_type,
                payload=payload,
                timeout=timeout,
                callback=callback
            )
            
            # Add to pending commands
            self.pending_commands[command_id] = command
            
            self.logger.info(f"Queued command {command_type.value} for device {device_id}")
            return command_id
            
        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")
            return ""
    
    async def _command_processor(self):
        """Process pending commands."""
        while not self.stop_event.is_set():
            try:
                # Process pending commands
                commands_to_process = list(self.pending_commands.values())
                
                for command in commands_to_process:
                    if command.status == CommandStatus.PENDING:
                        await self._execute_command(command)
                    elif command.status in [CommandStatus.SENT, CommandStatus.ACKNOWLEDGED]:
                        # Check for timeout
                        if time.time() - command.sent_at > command.timeout:
                            command.status = CommandStatus.TIMEOUT
                            command.error = "Command timeout"
                            self._complete_command(command)
                
                await asyncio.sleep(1)  # Process commands every second
                
            except Exception as e:
                self.logger.error(f"Error in command processor: {e}")
                await asyncio.sleep(5)
    
    async def _execute_command(self, command: EdgeCommand):
        """Execute individual command."""
        try:
            device_config = self.device_configs.get(command.device_id)
            if not device_config:
                command.status = CommandStatus.FAILED
                command.error = "Device configuration not found"
                self._complete_command(command)
                return
            
            # Get or create connection
            session = await self._get_device_connection(command.device_id)
            if not session:
                command.status = CommandStatus.FAILED
                command.error = "Failed to establish connection"
                self._complete_command(command)
                return
            
            # Prepare request
            url = f"http://{device_config.ip_address}:{device_config.port}/command"
            headers = {}
            if device_config.api_key:
                headers["Authorization"] = f"Bearer {device_config.api_key}"
            
            request_data = {
                "command_id": command.command_id,
                "command_type": command.command_type.value,
                "payload": command.payload,
                "timestamp": time.time()
            }
            
            # Send command
            command.sent_at = time.time()
            command.status = CommandStatus.SENT
            
            async with session.post(
                url,
                json=request_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=command.timeout)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    command.response = result
                    command.status = CommandStatus.COMPLETED
                    command.completed_at = time.time()
                    
                    # Update statistics
                    response_time = command.completed_at - command.sent_at
                    self._update_response_time_stats(response_time)
                    self.comm_stats["commands_completed"] += 1
                    
                else:
                    command.status = CommandStatus.FAILED
                    command.error = f"HTTP {response.status}: {await response.text()}"
                    self.comm_stats["commands_failed"] += 1
            
            self.comm_stats["commands_sent"] += 1
            self._complete_command(command)
            
        except Exception as e:
            command.status = CommandStatus.FAILED
            command.error = str(e)
            self.comm_stats["commands_failed"] += 1
            self.comm_stats["connection_errors"] += 1
            self._complete_command(command)
    
    def _complete_command(self, command: EdgeCommand):
        """Complete command processing."""
        # Execute callback if provided
        if command.callback:
            try:
                command.callback(command)
            except Exception as e:
                self.logger.error(f"Error in command callback: {e}")
        
        # Move to history
        self.command_history.append(command)
        if len(self.command_history) > self.max_history_size:
            self.command_history.pop(0)
        
        # Remove from pending
        if command.command_id in self.pending_commands:
            del self.pending_commands[command.command_id]
        
        self.logger.debug(f"Completed command {command.command_id} with status {command.status.value}")
    
    async def _get_device_connection(self, device_id: str) -> Optional[aiohttp.ClientSession]:
        """Get or create connection to device."""
        try:
            if device_id not in self.device_connections:
                # Create new connection
                connector = aiohttp.TCPConnector(
                    limit=10,
                    limit_per_host=5,
                    ttl_dns_cache=300,
                    use_dns_cache=True
                )
                
                session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                
                self.device_connections[device_id] = session
            
            return self.device_connections[device_id]
            
        except Exception as e:
            self.logger.error(f"Failed to create device connection: {e}")
            return None
    
    async def _data_sync_processor(self):
        """Process data synchronization."""
        while not self.stop_event.is_set():
            try:
                for device_id in self.device_configs.keys():
                    pending_data = self.sync_manager.get_pending_sync_data(device_id)
                    
                    if pending_data:
                        await self._sync_device_data(device_id, pending_data)
                
                await asyncio.sleep(10)  # Sync every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in data sync processor: {e}")
                await asyncio.sleep(30)
    
    async def _sync_device_data(self, device_id: str, data_items: List[Dict]):
        """Sync data with specific device."""
        try:
            device_config = self.device_configs.get(device_id)
            if not device_config:
                return
            
            session = await self._get_device_connection(device_id)
            if not session:
                return
            
            # Prepare sync request
            url = f"http://{device_config.ip_address}:{device_config.port}/sync"
            headers = {}
            if device_config.api_key:
                headers["Authorization"] = f"Bearer {device_config.api_key}"
            
            sync_data = {
                "device_id": device_id,
                "timestamp": time.time(),
                "data_items": data_items
            }
            
            # Send sync request
            async with session.post(
                url,
                json=sync_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    synced_ids = result.get("synced_ids", [])
                    
                    # Mark items as synced
                    self.sync_manager.mark_synced(device_id, synced_ids)
                    self.comm_stats["data_synced"] += len(synced_ids)
                    
                    self.logger.debug(f"Synced {len(synced_ids)} items with device {device_id}")
                
        except Exception as e:
            self.logger.error(f"Error syncing data with device {device_id}: {e}")
    
    async def _connection_monitor(self):
        """Monitor device connections."""
        while not self.stop_event.is_set():
            try:
                for device_id, device_config in self.device_configs.items():
                    # Check device health
                    is_healthy = await self._check_device_health(device_id)
                    
                    if not is_healthy:
                        self.logger.warning(f"Device {device_id} appears unhealthy")
                        
                        # Close and recreate connection
                        if device_id in self.device_connections:
                            await self.device_connections[device_id].close()
                            del self.device_connections[device_id]
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in connection monitor: {e}")
                await asyncio.sleep(30)
    
    async def _check_device_health(self, device_id: str) -> bool:
        """Check if device is healthy."""
        try:
            device_config = self.device_configs.get(device_id)
            if not device_config:
                return False
            
            session = await self._get_device_connection(device_id)
            if not session:
                return False
            
            url = f"http://{device_config.ip_address}:{device_config.port}/health"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
            
        except Exception:
            return False
    
    def _update_response_time_stats(self, response_time: float):
        """Update response time statistics."""
        completed = self.comm_stats["commands_completed"]
        current_avg = self.comm_stats["avg_response_time"]
        new_avg = (current_avg * (completed - 1) + response_time) / completed
        self.comm_stats["avg_response_time"] = new_avg
    
    def add_sync_data(self, device_id: str, data_type: str, data: Dict[str, Any]):
        """Add data to sync with device."""
        self.sync_manager.add_sync_data(device_id, data_type, data)
    
    def get_command_status(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a command."""
        if command_id in self.pending_commands:
            command = self.pending_commands[command_id]
            return {
                "command_id": command_id,
                "status": command.status.value,
                "device_id": command.device_id,
                "command_type": command.command_type.value,
                "created_at": command.created_at,
                "sent_at": command.sent_at,
                "completed_at": command.completed_at,
                "response": command.response,
                "error": command.error
            }
        
        # Check history
        for command in reversed(self.command_history):
            if command.command_id == command_id:
                return {
                    "command_id": command_id,
                    "status": command.status.value,
                    "device_id": command.device_id,
                    "command_type": command.command_type.value,
                    "created_at": command.created_at,
                    "sent_at": command.sent_at,
                    "completed_at": command.completed_at,
                    "response": command.response,
                    "error": command.error
                }
        
        return None
    
    def get_device_sync_status(self, device_id: str) -> Dict[str, Any]:
        """Get sync status for a device."""
        return self.sync_manager.get_sync_status(device_id)
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics."""
        return {
            "communication_stats": self.comm_stats.copy(),
            "active_connections": len(self.device_connections),
            "pending_commands": len(self.pending_commands),
            "command_history_size": len(self.command_history),
            "devices_configured": len(self.device_configs),
            "sync_status": {
                device_id: self.sync_manager.get_sync_status(device_id)
                for device_id in self.device_configs.keys()
            }
        }
    
    async def shutdown(self):
        """Shutdown communication service."""
        self.logger.info("Shutting down edge communication service")
        
        # Stop background tasks
        self.stop_event.set()
        
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close all connections
        for session in self.device_connections.values():
            await session.close()
        
        self.device_connections.clear()
        
        self.logger.info("Edge communication service shutdown complete")