# WebSocket Implementation Usage Guide

## Overview

The Smart Attendance System includes a comprehensive WebSocket implementation for real-time updates. This allows the faculty dashboard to receive live attendance data, emotion statistics, and system alerts without polling.

## Architecture

### Components

1. **ConnectionManager** (`backend/api/websocket.py`)
   - Manages WebSocket connections
   - Handles subscriptions to sessions
   - Broadcasts messages to subscribers

2. **WebSocketIntegrationService** (`backend/services/websocket_integration_service.py`)
   - Integrates with attendance and emotion services
   - Formats data for WebSocket broadcasting
   - Handles different types of updates

3. **WebSocket Endpoints** (`/api/v1/ws/{connection_id}`)
   - FastAPI WebSocket endpoints
   - Authentication and connection management
   - Message routing and error handling

## Connection Flow

### 1. Establishing Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/connection-id?user_id=faculty-001&role=faculty');

ws.onopen = function(event) {
    console.log('Connected to WebSocket server');
};
```

### 2. Subscribing to Session Updates

```javascript
// Subscribe to a specific attendance session
ws.send(JSON.stringify({
    type: 'subscribe',
    session_id: 'session-123'
}));
```

### 3. Receiving Real-time Updates

```javascript
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'attendance_update':
            updateAttendanceDisplay(data.data);
            break;
        case 'emotion_update':
            updateEmotionCharts(data.data);
            break;
        case 'alert':
            showAlert(data.data);
            break;
    }
};
```

## Message Types

### Connection Messages

#### Connection Established
```json
{
    "type": "connection_established",
    "connection_id": "connection-123",
    "message": "Connected to Smart Attendance System",
    "timestamp": "2024-01-01T10:00:00Z"
}
```

#### Subscription Confirmed
```json
{
    "type": "subscription_confirmed",
    "session_id": "session-123",
    "message": "Subscribed to session session-123",
    "timestamp": "2024-01-01T10:00:00Z"
}
```

### Real-time Updates

#### Attendance Update
```json
{
    "type": "attendance_update",
    "session_id": "session-123",
    "data": {
        "total_registered": 30,
        "total_detected": 25,
        "attendance_percentage": 83.33,
        "present_students": [
            {
                "student_id": "student-001",
                "status": "present",
                "timestamp": "2024-01-01T10:00:00Z",
                "confidence": 0.95
            }
        ],
        "present_count": 25,
        "is_active": true,
        "last_updated": "2024-01-01T10:00:00Z"
    },
    "timestamp": "2024-01-01T10:00:00Z"
}
```

#### Emotion Update
```json
{
    "type": "emotion_update",
    "session_id": "session-123",
    "data": {
        "total_detections": 100,
        "emotion_breakdown": {
            "interested": 60.0,
            "bored": 25.0,
            "confused": 15.0
        },
        "engagement_score": 7.5,
        "average_engagement": 7.2,
        "last_updated": "2024-01-01T10:00:00Z"
    },
    "timestamp": "2024-01-01T10:00:00Z"
}
```

#### Alert Message
```json
{
    "type": "alert",
    "data": {
        "alert_type": "attendance_discrepancy",
        "severity": "warning",
        "title": "Attendance Count Mismatch",
        "message": "Expected 30 students, detected 25",
        "requires_action": true,
        "session_id": "session-123"
    },
    "timestamp": "2024-01-01T10:00:00Z"
}
```

### Client Commands

#### Subscribe to Session
```json
{
    "type": "subscribe",
    "session_id": "session-123"
}
```

#### Unsubscribe from Session
```json
{
    "type": "unsubscribe",
    "session_id": "session-123"
}
```

#### Ping/Pong (Heartbeat)
```json
{
    "type": "ping"
}
```

#### Get Connection Status
```json
{
    "type": "get_status"
}
```

## Integration with Services

### Attendance Service Integration

The attendance service automatically broadcasts updates when:
- New students are detected in classroom
- Attendance session is created or updated
- Cross-verification is completed

```python
# In attendance service
await self.websocket_integration.broadcast_attendance_update(session)
```

### Emotion Analysis Integration

The emotion service broadcasts updates when:
- Emotion statistics are updated
- Engagement scores are calculated
- Session emotion data changes

```python
# In emotion service
await self.websocket_integration.broadcast_emotion_update(session_id, stats)
```

### Validation Service Integration

The validation service sends alerts for:
- Attendance discrepancies
- Missing students
- System health issues

```python
# In validation service
await self.websocket_integration.broadcast_validation_alert(session_id, alert_data)
```

## Error Handling

### Connection Errors
- Automatic reconnection with exponential backoff
- Stale connection cleanup (5-minute timeout)
- Graceful disconnection handling

### Message Errors
- Invalid JSON handling
- Unknown message type responses
- Service integration error isolation

### Network Issues
- Connection state monitoring
- Heartbeat mechanism (ping/pong)
- Connection health checks

## Testing

### Test Client
Use the provided HTML test client (`backend/websocket_test_client.html`) to:
- Test WebSocket connections
- Subscribe to sessions
- Monitor real-time updates
- Debug message flow

### Validation Script
Run the validation script to test core functionality:
```bash
cd backend
python validate_websocket.py
```

## Performance Considerations

### Connection Management
- Maximum 1000 concurrent connections
- Automatic cleanup of stale connections
- Memory-efficient subscription tracking

### Message Broadcasting
- Asynchronous message delivery
- Error isolation per connection
- Batch processing for multiple subscribers

### Resource Usage
- Connection metadata caching
- Efficient JSON serialization
- Background cleanup tasks

## Security

### Authentication
- User ID and role validation
- Connection-level authentication
- Session-based access control

### Data Protection
- No sensitive data in WebSocket messages
- Encrypted connections (WSS in production)
- Rate limiting and abuse prevention

## Deployment

### Development
```bash
# Start the FastAPI server with WebSocket support
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
- Use WSS (WebSocket Secure) protocol
- Configure load balancer for WebSocket support
- Monitor connection metrics and performance
- Set up proper logging and alerting

## Monitoring

### Connection Metrics
- Active connection count
- Session subscription statistics
- Message delivery rates
- Error rates and types

### Health Checks
- WebSocket endpoint availability
- Connection manager status
- Service integration health
- Memory and CPU usage

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check server is running
   - Verify WebSocket endpoint URL
   - Check firewall settings

2. **Messages Not Received**
   - Verify session subscription
   - Check connection status
   - Review server logs

3. **High Memory Usage**
   - Monitor connection count
   - Check for connection leaks
   - Review cleanup task logs

### Debug Tools
- WebSocket test client
- Browser developer tools
- Server-side logging
- Connection status endpoints