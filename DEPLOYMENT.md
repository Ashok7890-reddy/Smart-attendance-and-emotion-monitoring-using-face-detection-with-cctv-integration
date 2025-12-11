# Smart Attendance System Deployment Guide

This guide covers the deployment of the Smart Attendance System using Docker containers and Kubernetes orchestration.

## Prerequisites

### Development Environment
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+
- Python 3.11+

### Production Environment
- Kubernetes cluster 1.24+
- kubectl configured
- Docker registry access
- Persistent storage (NFS or similar)
- SSL certificates (optional, for HTTPS)

## Architecture Overview

The system consists of the following microservices:

- **Face Recognition Service**: Handles face detection, embedding extraction, and liveness detection
- **Emotion Analysis Service**: Analyzes facial expressions and calculates engagement scores
- **Attendance Management Service**: Manages attendance workflows and cross-verification
- **Validation Service**: Validates attendance accuracy and generates alerts
- **API Gateway**: Routes requests and handles authentication
- **WebSocket Server**: Provides real-time updates to the frontend
- **Frontend**: React-based faculty dashboard
- **PostgreSQL**: Primary database for structured data
- **Redis**: Caching and session management

## Development Deployment

### Quick Start

1. **Clone the repository and navigate to the project directory**

2. **Start the development environment**:
   ```bash
   chmod +x scripts/start-dev.sh
   ./scripts/start-dev.sh
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - API Documentation: http://localhost:8000/api/v1/docs

### Manual Development Setup

1. **Create environment file**:
   ```bash
   cp .env.example .env.development
   ```

2. **Start services**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f [service_name]
   ```

4. **Stop services**:
   ```bash
   docker-compose down
   ```

## Production Deployment

### Building Images

1. **Build all service images**:
   ```bash
   chmod +x scripts/build-images.sh
   ./scripts/build-images.sh [version]
   ```

2. **Push images to registry** (replace with your registry):
   ```bash
   docker tag smart-attendance/face-recognition:latest your-registry/smart-attendance/face-recognition:latest
   docker push your-registry/smart-attendance/face-recognition:latest
   # Repeat for all services
   ```

### Kubernetes Deployment

1. **Update image references** in Kubernetes manifests to point to your registry

2. **Update secrets** in `k8s/secrets.yaml` with base64-encoded production values:
   ```bash
   echo -n "your-production-password" | base64
   ```

3. **Deploy to Kubernetes**:
   ```bash
   chmod +x scripts/deploy-k8s.sh
   ./scripts/deploy-k8s.sh
   ```

4. **Verify deployment**:
   ```bash
   kubectl get pods -n smart-attendance
   kubectl get services -n smart-attendance
   ```

### Manual Kubernetes Deployment

1. **Apply manifests in order**:
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/persistent-volumes.yaml
   kubectl apply -f k8s/secrets.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/postgres.yaml
   kubectl apply -f k8s/redis.yaml
   kubectl apply -f k8s/face-recognition-service.yaml
   kubectl apply -f k8s/emotion-analysis-service.yaml
   kubectl apply -f k8s/attendance-service.yaml
   kubectl apply -f k8s/validation-service.yaml
   kubectl apply -f k8s/websocket-server.yaml
   kubectl apply -f k8s/api-gateway.yaml
   kubectl apply -f k8s/frontend.yaml
   kubectl apply -f k8s/ingress.yaml
   kubectl apply -f k8s/hpa.yaml
   ```

## Configuration

### Environment Variables

#### Backend Services
- `ENVIRONMENT`: deployment environment (development/production)
- `DB_HOST`: PostgreSQL host
- `DB_PASSWORD`: PostgreSQL password
- `REDIS_HOST`: Redis host
- `SERVICE_NAME`: service identifier
- `LOG_LEVEL`: logging level (DEBUG/INFO/WARNING/ERROR)

#### AI Model Paths
- `FACE_RECOGNITION_MODEL_PATH`: path to face recognition model
- `LIVENESS_MODEL_PATH`: path to liveness detection model
- `EMOTION_MODEL_PATH`: path to emotion classification model

#### Service URLs (for inter-service communication)
- `FACE_RECOGNITION_SERVICE_URL`: face recognition service endpoint
- `EMOTION_ANALYSIS_SERVICE_URL`: emotion analysis service endpoint
- `ATTENDANCE_SERVICE_URL`: attendance service endpoint
- `VALIDATION_SERVICE_URL`: validation service endpoint

#### Frontend
- `REACT_APP_API_URL`: API gateway URL
- `REACT_APP_WS_URL`: WebSocket server URL

### Resource Requirements

#### Minimum Requirements (Development)
- CPU: 4 cores
- Memory: 8GB RAM
- Storage: 50GB

#### Recommended Requirements (Production)
- CPU: 16 cores
- Memory: 32GB RAM
- Storage: 200GB SSD
- GPU: NVIDIA GPU for AI processing (optional but recommended)

### Scaling Configuration

The system includes Horizontal Pod Autoscalers (HPA) for automatic scaling:

- **Face Recognition Service**: 2-10 replicas based on CPU/memory usage
- **Emotion Analysis Service**: 2-8 replicas based on CPU/memory usage
- **Attendance Service**: 2-6 replicas based on CPU usage
- **API Gateway**: 2-5 replicas based on CPU usage

## Monitoring and Maintenance

### Health Checks

All services include health check endpoints:
- HTTP services: `GET /health`
- WebSocket server: `GET /health`

### Logging

Logs are stored in persistent volumes and can be accessed via:
```bash
kubectl logs -f deployment/[service-name] -n smart-attendance
```

### Database Maintenance

1. **Backup PostgreSQL**:
   ```bash
   kubectl exec -it postgres-0 -n smart-attendance -- pg_dump -U postgres smart_attendance > backup.sql
   ```

2. **Restore PostgreSQL**:
   ```bash
   kubectl exec -i postgres-0 -n smart-attendance -- psql -U postgres smart_attendance < backup.sql
   ```

### Updating the System

1. **Build new images** with updated version tags
2. **Update Kubernetes manifests** with new image versions
3. **Apply updates**:
   ```bash
   kubectl apply -f k8s/
   ```
4. **Monitor rollout**:
   ```bash
   kubectl rollout status deployment/[service-name] -n smart-attendance
   ```

## Troubleshooting

### Common Issues

1. **Services not starting**: Check resource limits and availability
2. **Database connection issues**: Verify PostgreSQL is running and accessible
3. **Model loading failures**: Ensure AI models are present in the models volume
4. **High memory usage**: Consider increasing memory limits or optimizing models

### Debug Commands

```bash
# Check pod status
kubectl get pods -n smart-attendance

# View pod logs
kubectl logs -f [pod-name] -n smart-attendance

# Describe pod for events
kubectl describe pod [pod-name] -n smart-attendance

# Execute into pod for debugging
kubectl exec -it [pod-name] -n smart-attendance -- /bin/bash

# Check service endpoints
kubectl get endpoints -n smart-attendance
```

## Security Considerations

1. **Update secrets** with strong, unique passwords
2. **Enable SSL/TLS** for all external communications
3. **Implement network policies** to restrict inter-pod communication
4. **Regular security updates** for base images and dependencies
5. **Audit logging** for all biometric data access
6. **Backup encryption** for sensitive data

## Performance Optimization

1. **GPU acceleration** for AI workloads
2. **Redis clustering** for high availability
3. **Database indexing** for query optimization
4. **CDN integration** for frontend assets
5. **Load balancing** across multiple regions