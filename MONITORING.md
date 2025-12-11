# Smart Attendance System - Monitoring and Logging

This document describes the monitoring and logging infrastructure for the Smart Attendance System, including setup, configuration, and usage instructions.

## Overview

The monitoring and logging infrastructure consists of:

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notification
- **Elasticsearch**: Log storage and indexing
- **Fluentd**: Log aggregation and processing
- **Kibana**: Log visualization and analysis

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │───▶│     Fluentd     │───▶│ Elasticsearch   │
│    Services     │    │ (Log Aggregator)│    │  (Log Storage)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         │ metrics                                      │
         ▼                                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │───▶│   AlertManager  │    │     Kibana      │
│ (Metrics Store) │    │   (Alerting)    │    │ (Log Analysis)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│     Grafana     │
│ (Visualization) │
└─────────────────┘
```

## Quick Start

### 1. Setup Monitoring Infrastructure

Run the setup script to create all necessary configuration files:

**Linux/macOS:**
```bash
chmod +x scripts/setup-monitoring.sh
./scripts/setup-monitoring.sh
```

**Windows:**
```cmd
scripts\setup-monitoring.bat
```

### 2. Start Monitoring Stack

```bash
# Start all services including monitoring
docker-compose up -d

# Or start only monitoring services
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### 3. Verify Services

```bash
# Linux/macOS
./scripts/check-monitoring-health.sh

# Windows
scripts\check-monitoring-health.bat
```

### 4. Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Kibana**: http://localhost:5601
- **AlertManager**: http://localhost:9093

## Configuration

### Environment Variables

Create or update `.env.monitoring`:

```env
# Grafana Configuration
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_password

# Database Configuration
DB_PASSWORD=your_db_password

# Alert Configuration
ALERT_EMAIL=admin@yourdomain.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Environment
ENVIRONMENT=production
```

### Prometheus Configuration

The Prometheus configuration (`monitoring/prometheus/prometheus.yml`) includes:

- Service discovery for all Smart Attendance services
- Scraping intervals and targets
- Alert rule definitions
- Integration with AlertManager

### Grafana Dashboards

Pre-configured dashboards include:

1. **System Overview**: Service status, resource usage, performance metrics
2. **Face Recognition**: Processing times, accuracy, liveness detection
3. **Emotion Analysis**: Emotion distribution, engagement scores
4. **Attendance Management**: Session statistics, validation metrics
5. **Infrastructure**: Database, Redis, camera connectivity

### Alert Rules

Configured alerts include:

- **Service Down**: Any service becomes unavailable
- **High Latency**: Processing times exceed thresholds
- **Low Accuracy**: Face recognition accuracy drops below 95%
- **Resource Usage**: High CPU/memory usage
- **Camera Connectivity**: Camera disconnections
- **Database Issues**: Connection failures or performance issues

## Metrics

### Application Metrics

#### Face Recognition Service
- `face_recognition_requests_total`: Total recognition requests
- `face_recognition_processing_duration_seconds`: Processing time histogram
- `face_recognition_accuracy_percentage`: Current accuracy percentage
- `liveness_detection_requests_total`: Liveness detection attempts

#### Emotion Analysis Service
- `emotion_analysis_requests_total`: Total emotion analysis requests
- `emotion_analysis_processing_duration_seconds`: Processing time histogram
- `emotion_detected_total`: Emotion distribution counters
- `engagement_score_current`: Current engagement scores

#### Attendance Management Service
- `attendance_sessions_active_total`: Active attendance sessions
- `students_detected_total`: Student detection counters
- `attendance_validation_failures_total`: Validation failure counters
- `cross_verification_requests_total`: Cross-verification attempts

### System Metrics

- `up`: Service availability (1=up, 0=down)
- `http_requests_total`: HTTP request counters
- `http_request_duration_seconds`: HTTP request duration histogram
- `database_connections_active`: Active database connections
- `redis_cache_hits_total` / `redis_cache_misses_total`: Cache performance

## Logging

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General information about system operation
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical errors requiring immediate attention

### Log Categories

#### Security Audit Logs
- Authentication attempts
- Authorization failures
- Biometric data access
- Encryption/decryption operations

#### Performance Logs
- Processing times
- Response times
- Resource usage metrics
- Benchmark results

#### Application Logs
- Service startup/shutdown
- Request processing
- Business logic events
- Integration points

### Log Format

Structured JSON logging format:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "service": "face_recognition",
  "module": "recognition_service",
  "function": "process_face",
  "line": 123,
  "message": "Face recognition completed successfully",
  "thread_id": 12345,
  "process_id": 67890,
  "extra_fields": {
    "processing_time": 1.23,
    "confidence": 0.95,
    "student_id": "STU001"
  }
}
```

## Alerting

### Alert Channels

Configure alert channels in `monitoring/alertmanager/config.yml`:

#### Email Alerts
```yaml
email_configs:
  - to: 'admin@yourdomain.com'
    subject: 'Smart Attendance System Alert'
    body: |
      Alert: {{ .GroupLabels.alertname }}
      Summary: {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}
      Description: {{ range .Alerts }}{{ .Annotations.description }}{{ end }}
```

#### Slack Alerts
```yaml
slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#alerts'
    title: 'Smart Attendance System Alert'
    text: |
      *Alert:* {{ .GroupLabels.alertname }}
      *Summary:* {{ range .Alerts }}{{ .Annotations.summary }}{{ end }}
```

### Alert Severity Levels

- **Critical**: Service outages, security breaches, data loss
- **Warning**: Performance degradation, resource constraints
- **Info**: Maintenance notifications, configuration changes

## Kubernetes Deployment

### Deploy Monitoring Stack

```bash
# Create monitoring namespace
kubectl apply -f k8s/monitoring-namespace.yaml

# Deploy Prometheus
kubectl apply -f k8s/prometheus.yaml

# Deploy Grafana
kubectl apply -f k8s/grafana.yaml

# Or use the deployment script
./scripts/deploy-monitoring-k8s.sh
```

### Access Services

```bash
# Port forward to access services locally
kubectl port-forward -n monitoring service/prometheus 9090:9090
kubectl port-forward -n monitoring service/grafana 3000:3000
```

## Troubleshooting

### Common Issues

#### Prometheus Not Scraping Metrics
1. Check service discovery configuration
2. Verify network connectivity between services
3. Ensure metrics endpoints are accessible
4. Check Prometheus logs: `docker logs prometheus`

#### Grafana Dashboard Not Loading
1. Verify Prometheus datasource configuration
2. Check Grafana logs: `docker logs grafana`
3. Ensure proper permissions and authentication

#### Fluentd Not Collecting Logs
1. Check Fluentd configuration syntax
2. Verify log file permissions
3. Check Elasticsearch connectivity
4. Review Fluentd logs: `docker logs fluentd`

#### High Resource Usage
1. Adjust retention policies in Prometheus
2. Configure log rotation for Fluentd
3. Optimize Elasticsearch indices
4. Scale services horizontally if needed

### Log Analysis

#### View Application Logs
```bash
# View logs from specific service
docker logs face_recognition_service

# Follow logs in real-time
docker logs -f attendance_service

# View structured logs
docker logs emotion_analysis_service | jq '.'
```

#### Search Logs in Kibana
1. Access Kibana at http://localhost:5601
2. Create index patterns for `smart-attendance-*`
3. Use KQL queries to search logs:
   - `service: "face_recognition" AND level: "ERROR"`
   - `message: "processing_time" AND extra_fields.processing_time > 2`

## Performance Tuning

### Prometheus
- Adjust scrape intervals based on requirements
- Configure retention policies to manage storage
- Use recording rules for complex queries

### Elasticsearch
- Configure appropriate heap size
- Set up index lifecycle management
- Use index templates for consistent mapping

### Grafana
- Enable query caching
- Optimize dashboard queries
- Use template variables for dynamic dashboards

## Security Considerations

### Access Control
- Change default passwords for all services
- Implement proper authentication and authorization
- Use HTTPS for all web interfaces
- Restrict network access to monitoring services

### Data Privacy
- Ensure logs don't contain sensitive information
- Implement log retention policies
- Use encryption for data in transit and at rest
- Regular security audits of monitoring infrastructure

## Maintenance

### Regular Tasks
- Monitor disk usage for log and metric storage
- Update monitoring stack components
- Review and update alert rules
- Clean up old logs and metrics
- Test backup and recovery procedures

### Backup Strategy
- Backup Prometheus data directory
- Export Grafana dashboards and datasources
- Backup Elasticsearch indices
- Document configuration changes

## Support

For issues related to monitoring and logging:

1. Check the troubleshooting section above
2. Review service logs for error messages
3. Verify configuration files
4. Check network connectivity between services
5. Consult the official documentation for each component

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Elasticsearch Documentation](https://www.elastic.co/guide/)
- [Fluentd Documentation](https://docs.fluentd.org/)
- [AlertManager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)