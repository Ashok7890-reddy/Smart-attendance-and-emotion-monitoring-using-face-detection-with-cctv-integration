@echo off
setlocal enabledelayedexpansion

echo Setting up monitoring and logging infrastructure for Smart Attendance System...

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not installed. Please install Docker Compose and try again.
    exit /b 1
)

echo [INFO] Creating monitoring and logging directories...
if not exist "monitoring\prometheus" mkdir monitoring\prometheus
if not exist "monitoring\grafana\provisioning\datasources" mkdir monitoring\grafana\provisioning\datasources
if not exist "monitoring\grafana\provisioning\dashboards" mkdir monitoring\grafana\provisioning\dashboards
if not exist "monitoring\alertmanager" mkdir monitoring\alertmanager
if not exist "logging\fluentd" mkdir logging\fluentd
if not exist "logs" mkdir logs

echo [INFO] Directories created successfully.

echo [INFO] Setting up Fluentd with required plugins...
(
echo FROM fluent/fluentd:v1.16-debian-1
echo.
echo USER root
echo.
echo RUN buildDeps="sudo make gcc g++ libc-dev" ^&^&\
echo     apt-get update ^&^&\
echo     apt-get install -y $buildDeps ^&^&\
echo     sudo gem install fluent-plugin-elasticsearch ^&^&\
echo     sudo gem install fluent-plugin-prometheus ^&^&\
echo     sudo gem install fluent-plugin-record-modifier ^&^&\
echo     SUDO_FORCE_REMOVE=yes \
echo     apt-get purge -y --auto-remove $buildDeps ^&^&\
echo     rm -rf /var/lib/apt/lists/* ^&^&\
echo     rm -rf /tmp/* /var/tmp/* /usr/lib/ruby/gems/*/cache/*.gem
echo.
echo COPY fluent.conf /fluentd/etc/
echo COPY entrypoint.sh /bin/
echo.
echo USER fluent
) > logging\fluentd\Dockerfile

REM Create Fluentd entrypoint script
(
echo #!/bin/sh
echo.
echo # Create log directories
echo mkdir -p /fluentd/log/buffer/elasticsearch
echo mkdir -p /fluentd/log/buffer/docker
echo mkdir -p /fluentd/log/backup
echo.
echo # Set permissions
echo chown -R fluent:fluent /fluentd/log
echo.
echo # Start Fluentd
echo exec fluentd -c /fluentd/etc/fluent.conf -v
) > logging\fluentd\entrypoint.sh

echo [INFO] Fluentd configuration created.

echo [INFO] Creating monitoring environment configuration...
(
echo # Grafana Configuration
echo GRAFANA_USER=admin
echo GRAFANA_PASSWORD=admin123
echo.
echo # Database Configuration
echo DB_PASSWORD=postgres
echo.
echo # Elasticsearch Configuration
echo ES_JAVA_OPTS=-Xms512m -Xmx512m
echo.
echo # Alert Configuration
echo ALERT_EMAIL=admin@smartattendance.local
echo SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
echo.
echo # Environment
echo ENVIRONMENT=development
) > .env.monitoring

echo [INFO] Environment configuration created.

echo [INFO] Creating monitoring Docker Compose configuration...
(
echo version: '3.8'
echo.
echo services:
echo   # Override existing services to add logging
echo   face_recognition_service:
echo     logging:
echo       driver: fluentd
echo       options:
echo         fluentd-address: localhost:24224
echo         tag: smart_attendance.face_recognition
echo.
echo   emotion_analysis_service:
echo     logging:
echo       driver: fluentd
echo       options:
echo         fluentd-address: localhost:24224
echo         tag: smart_attendance.emotion_analysis
echo.
echo   attendance_service:
echo     logging:
echo       driver: fluentd
echo       options:
echo         fluentd-address: localhost:24224
echo         tag: smart_attendance.attendance
echo.
echo   validation_service:
echo     logging:
echo       driver: fluentd
echo       options:
echo         fluentd-address: localhost:24224
echo         tag: smart_attendance.validation
echo.
echo   api_gateway:
echo     logging:
echo       driver: fluentd
echo       options:
echo         fluentd-address: localhost:24224
echo         tag: smart_attendance.api_gateway
) > docker-compose.monitoring.yml

echo [INFO] Monitoring Docker Compose configuration created.

echo [INFO] Creating Kubernetes monitoring deployment script...
(
echo @echo off
echo setlocal
echo.
echo echo Deploying monitoring infrastructure to Kubernetes...
echo.
echo REM Create monitoring namespace
echo kubectl apply -f k8s/monitoring-namespace.yaml
echo.
echo REM Deploy Prometheus
echo kubectl apply -f k8s/prometheus.yaml
echo.
echo REM Deploy Grafana
echo kubectl apply -f k8s/grafana.yaml
echo.
echo echo Waiting for Prometheus to be ready...
echo kubectl wait --for=condition=available --timeout=300s deployment/prometheus -n monitoring
echo.
echo echo Waiting for Grafana to be ready...
echo kubectl wait --for=condition=available --timeout=300s deployment/grafana -n monitoring
echo.
echo echo Monitoring services deployed successfully!
echo echo.
echo echo Access URLs:
echo echo Prometheus: Check kubectl get services -n monitoring
echo echo Grafana: Check kubectl get services -n monitoring
echo echo.
echo echo Grafana credentials:
echo echo Username: admin
echo echo Password: admin123
) > scripts\deploy-monitoring-k8s.bat

echo [INFO] Kubernetes deployment script created.

echo [INFO] Creating monitoring health check script...
(
echo @echo off
echo setlocal
echo.
echo echo Checking monitoring infrastructure health...
echo.
echo REM Check Prometheus
echo curl -s http://localhost:9090/-/healthy >nul 2>&1
echo if errorlevel 1 (
echo     echo X Prometheus is not responding
echo ^) else (
echo     echo √ Prometheus is healthy
echo ^)
echo.
echo REM Check Grafana
echo curl -s http://localhost:3000/api/health >nul 2>&1
echo if errorlevel 1 (
echo     echo X Grafana is not responding
echo ^) else (
echo     echo √ Grafana is healthy
echo ^)
echo.
echo REM Check Elasticsearch
echo curl -s http://localhost:9200/_cluster/health >nul 2>&1
echo if errorlevel 1 (
echo     echo X Elasticsearch is not responding
echo ^) else (
echo     echo √ Elasticsearch is healthy
echo ^)
echo.
echo REM Check AlertManager
echo curl -s http://localhost:9093/-/healthy >nul 2>&1
echo if errorlevel 1 (
echo     echo X AlertManager is not responding
echo ^) else (
echo     echo √ AlertManager is healthy
echo ^)
echo.
echo echo.
echo echo Monitoring URLs:
echo echo Prometheus: http://localhost:9090
echo echo Grafana: http://localhost:3000 ^(admin/admin123^)
echo echo Kibana: http://localhost:5601
echo echo AlertManager: http://localhost:9093
) > scripts\check-monitoring-health.bat

echo [INFO] Health check script created.

echo [INFO] Setting up log rotation...
(
echo /app/logs/*.log {
echo     daily
echo     missingok
echo     rotate 30
echo     compress
echo     delaycompress
echo     notifempty
echo     create 644 root root
echo     postrotate
echo         /usr/bin/docker kill -s USR1 $(docker ps -q --filter name=smart_attendance) 2>/dev/null ^|^| true
echo     endscript
echo }
) > logging\logrotate.conf

echo [INFO] Log rotation configuration created.

echo [INFO] Monitoring and logging infrastructure setup completed!
echo [WARNING] Please review the configuration files and update credentials before deploying to production.

echo.
echo Next steps:
echo 1. Review and update .env.monitoring with your actual credentials
echo 2. Update monitoring\alertmanager\config.yml with your email/Slack settings
echo 3. Run 'docker-compose up -d' to start the monitoring stack
echo 4. Run 'scripts\check-monitoring-health.bat' to verify all services are running
echo 5. Access Grafana at http://localhost:3000 (admin/admin123) to view dashboards

pause