#!/bin/bash

# Smart Attendance System - Monitoring and Logging Setup Script

set -e

echo "Setting up monitoring and logging infrastructure for Smart Attendance System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Create necessary directories
print_status "Creating monitoring and logging directories..."
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/alertmanager
mkdir -p logging/fluentd
mkdir -p logs

# Set permissions for log directories
chmod 755 logs
chmod -R 755 monitoring
chmod -R 755 logging

print_status "Directories created successfully."

# Install Fluentd plugins
print_status "Setting up Fluentd with required plugins..."
cat > logging/fluentd/Dockerfile << EOF
FROM fluent/fluentd:v1.16-debian-1

USER root

RUN buildDeps="sudo make gcc g++ libc-dev" \\
    && apt-get update \\
    && apt-get install -y \$buildDeps \\
    && sudo gem install fluent-plugin-elasticsearch \\
    && sudo gem install fluent-plugin-prometheus \\
    && sudo gem install fluent-plugin-record-modifier \\
    && SUDO_FORCE_REMOVE=yes \\
    apt-get purge -y --auto-remove \$buildDeps \\
    && rm -rf /var/lib/apt/lists/* \\
    && rm -rf /tmp/* /var/tmp/* /usr/lib/ruby/gems/*/cache/*.gem

COPY fluent.conf /fluentd/etc/
COPY entrypoint.sh /bin/

USER fluent
EOF

# Create Fluentd entrypoint script
cat > logging/fluentd/entrypoint.sh << 'EOF'
#!/bin/sh

# Create log directories
mkdir -p /fluentd/log/buffer/elasticsearch
mkdir -p /fluentd/log/buffer/docker
mkdir -p /fluentd/log/backup

# Set permissions
chown -R fluent:fluent /fluentd/log

# Start Fluentd
exec fluentd -c /fluentd/etc/fluent.conf -v
EOF

chmod +x logging/fluentd/entrypoint.sh

print_status "Fluentd configuration created."

# Create environment file for monitoring
print_status "Creating monitoring environment configuration..."
cat > .env.monitoring << EOF
# Grafana Configuration
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin123

# Database Configuration
DB_PASSWORD=postgres

# Elasticsearch Configuration
ES_JAVA_OPTS=-Xms512m -Xmx512m

# Alert Configuration
ALERT_EMAIL=admin@smartattendance.local
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Environment
ENVIRONMENT=development
EOF

print_status "Environment configuration created."

# Create monitoring docker-compose override
print_status "Creating monitoring Docker Compose configuration..."
cat > docker-compose.monitoring.yml << EOF
version: '3.8'

services:
  # Override existing services to add logging
  face_recognition_service:
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: smart_attendance.face_recognition

  emotion_analysis_service:
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: smart_attendance.emotion_analysis

  attendance_service:
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: smart_attendance.attendance

  validation_service:
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: smart_attendance.validation

  api_gateway:
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: smart_attendance.api_gateway
EOF

print_status "Monitoring Docker Compose configuration created."

# Create Kubernetes monitoring deployment script
print_status "Creating Kubernetes monitoring deployment script..."
cat > scripts/deploy-monitoring-k8s.sh << 'EOF'
#!/bin/bash

set -e

echo "Deploying monitoring infrastructure to Kubernetes..."

# Create monitoring namespace
kubectl apply -f k8s/monitoring-namespace.yaml

# Deploy Prometheus
kubectl apply -f k8s/prometheus.yaml

# Deploy Grafana
kubectl apply -f k8s/grafana.yaml

# Wait for deployments to be ready
echo "Waiting for Prometheus to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n monitoring

echo "Waiting for Grafana to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/grafana -n monitoring

# Get service URLs
echo "Monitoring services deployed successfully!"
echo ""
echo "Access URLs:"
echo "Prometheus: http://$(kubectl get service prometheus -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):9090"
echo "Grafana: http://$(kubectl get service grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):3000"
echo ""
echo "Grafana credentials:"
echo "Username: admin"
echo "Password: admin123"
EOF

chmod +x scripts/deploy-monitoring-k8s.sh

print_status "Kubernetes deployment script created."

# Create monitoring health check script
print_status "Creating monitoring health check script..."
cat > scripts/check-monitoring-health.sh << 'EOF'
#!/bin/bash

# Health check script for monitoring infrastructure

echo "Checking monitoring infrastructure health..."

# Check Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "✓ Prometheus is healthy"
else
    echo "✗ Prometheus is not responding"
fi

# Check Grafana
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✓ Grafana is healthy"
else
    echo "✗ Grafana is not responding"
fi

# Check Elasticsearch
if curl -s http://localhost:9200/_cluster/health > /dev/null; then
    echo "✓ Elasticsearch is healthy"
else
    echo "✗ Elasticsearch is not responding"
fi

# Check Fluentd
if curl -s http://localhost:24224/api/plugins.json > /dev/null; then
    echo "✓ Fluentd is healthy"
else
    echo "✗ Fluentd is not responding"
fi

# Check AlertManager
if curl -s http://localhost:9093/-/healthy > /dev/null; then
    echo "✓ AlertManager is healthy"
else
    echo "✗ AlertManager is not responding"
fi

echo ""
echo "Monitoring URLs:"
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3000 (admin/admin123)"
echo "Kibana: http://localhost:5601"
echo "AlertManager: http://localhost:9093"
EOF

chmod +x scripts/check-monitoring-health.sh

print_status "Health check script created."

# Create log rotation configuration
print_status "Setting up log rotation..."
cat > logging/logrotate.conf << EOF
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        /usr/bin/docker kill -s USR1 \$(docker ps -q --filter name=smart_attendance) 2>/dev/null || true
    endscript
}
EOF

print_status "Log rotation configuration created."

print_status "Monitoring and logging infrastructure setup completed!"
print_warning "Please review the configuration files and update credentials before deploying to production."

echo ""
echo "Next steps:"
echo "1. Review and update .env.monitoring with your actual credentials"
echo "2. Update monitoring/alertmanager/config.yml with your email/Slack settings"
echo "3. Run 'docker-compose up -d' to start the monitoring stack"
echo "4. Run 'scripts/check-monitoring-health.sh' to verify all services are running"
echo "5. Access Grafana at http://localhost:3000 (admin/admin123) to view dashboards"
EOF

chmod +x scripts/setup-monitoring.sh

print_status "Setup script created successfully."