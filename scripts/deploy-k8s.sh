#!/bin/bash

# Deploy Smart Attendance System to Kubernetes
set -e

echo "Deploying Smart Attendance System to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Apply Kubernetes manifests in order
echo "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "Creating persistent volumes..."
kubectl apply -f k8s/persistent-volumes.yaml

echo "Creating secrets and config maps..."
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

echo "Deploying database services..."
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

echo "Waiting for database services to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n smart-attendance --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n smart-attendance --timeout=300s

echo "Deploying backend services..."
kubectl apply -f k8s/face-recognition-service.yaml
kubectl apply -f k8s/emotion-analysis-service.yaml
kubectl apply -f k8s/attendance-service.yaml
kubectl apply -f k8s/validation-service.yaml
kubectl apply -f k8s/websocket-server.yaml
kubectl apply -f k8s/api-gateway.yaml

echo "Waiting for backend services to be ready..."
kubectl wait --for=condition=ready pod -l app=face-recognition-service -n smart-attendance --timeout=300s
kubectl wait --for=condition=ready pod -l app=emotion-analysis-service -n smart-attendance --timeout=300s
kubectl wait --for=condition=ready pod -l app=attendance-service -n smart-attendance --timeout=300s
kubectl wait --for=condition=ready pod -l app=validation-service -n smart-attendance --timeout=300s
kubectl wait --for=condition=ready pod -l app=websocket-server -n smart-attendance --timeout=300s
kubectl wait --for=condition=ready pod -l app=api-gateway -n smart-attendance --timeout=300s

echo "Deploying frontend..."
kubectl apply -f k8s/frontend.yaml

echo "Setting up ingress..."
kubectl apply -f k8s/ingress.yaml

echo "Setting up horizontal pod autoscaling..."
kubectl apply -f k8s/hpa.yaml

echo "Deployment completed successfully!"
echo ""
echo "To check the status of your deployment:"
echo "kubectl get pods -n smart-attendance"
echo ""
echo "To access the application:"
echo "kubectl port-forward -n smart-attendance svc/frontend-service 8080:80"
echo "Then visit http://localhost:8080"