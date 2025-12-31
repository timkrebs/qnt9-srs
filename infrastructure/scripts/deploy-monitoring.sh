#!/bin/bash
set -euo pipefail

# QNT9 Monitoring Stack Deployment Script
# Deploys Grafana Agent, kube-state-metrics, and configures Grafana Cloud integration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITORING_DIR="${SCRIPT_DIR}/../kubernetes/monitoring"

echo "========================================"
echo "QNT9 Monitoring Stack Deployment"
echo "========================================"
echo

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we're connected to a cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Not connected to a Kubernetes cluster"
    echo "Please configure kubectl to connect to your AKS cluster"
    exit 1
fi

echo "Connected to cluster: $(kubectl config current-context)"
echo

# Function to prompt for Grafana Cloud credentials
prompt_credentials() {
    echo "========================================"
    echo "Grafana Cloud Configuration"
    echo "========================================"
    echo
    echo "You need to provide Grafana Cloud credentials."
    echo "Get these from: https://grafana.com/orgs/<your-org>/stacks"
    echo
    
    read -p "Do you want to configure Grafana Cloud credentials now? (y/n): " configure
    
    if [[ "$configure" != "y" ]]; then
        echo
        echo "Skipping credential configuration."
        echo "You must manually edit grafana-cloud-secrets.yaml before applying"
        return
    fi
    
    echo
    echo "Prometheus Configuration:"
    read -p "Remote Write Endpoint: " prom_endpoint
    read -p "Username (Instance ID): " prom_username
    read -sp "Password/API Key: " prom_password
    echo
    
    echo
    echo "Loki Configuration:"
    read -p "Endpoint URL: " loki_endpoint
    read -p "Username (Instance ID): " loki_username
    read -sp "Password/API Key: " loki_password
    echo
    
    echo
    echo "Tempo Configuration:"
    read -p "Endpoint (host:port): " tempo_endpoint
    read -p "Username (Instance ID): " tempo_username
    read -sp "Password/API Key: " tempo_password
    echo
    
    # Create temporary secret file
    cat > "${MONITORING_DIR}/grafana-cloud-secrets-configured.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: grafana-cloud-secrets
  namespace: qnt9-monitoring
type: Opaque
stringData:
  prometheus-remote-write-endpoint: "${prom_endpoint}"
  prometheus-username: "${prom_username}"
  prometheus-password: "${prom_password}"
  loki-endpoint: "${loki_endpoint}"
  loki-username: "${loki_username}"
  loki-password: "${loki_password}"
  tempo-endpoint: "${tempo_endpoint}"
  tempo-username: "${tempo_username}"
  tempo-password: "${tempo_password}"
EOF
    
    echo
    echo "Credentials configured successfully"
}

# Step 1: Create namespace
echo "Step 1: Creating monitoring namespace..."
kubectl apply -f "${MONITORING_DIR}/namespace.yaml"
echo "Namespace created/verified"
echo

# Step 2: Configure secrets
echo "Step 2: Configuring Grafana Cloud secrets..."
if [ -f "${MONITORING_DIR}/grafana-cloud-secrets-configured.yaml" ]; then
    echo "Using pre-configured secrets..."
    kubectl apply -f "${MONITORING_DIR}/grafana-cloud-secrets-configured.yaml"
elif kubectl get secret grafana-cloud-secrets -n qnt9-monitoring &> /dev/null; then
    echo "Secrets already exist, skipping..."
else
    prompt_credentials
    if [ -f "${MONITORING_DIR}/grafana-cloud-secrets-configured.yaml" ]; then
        kubectl apply -f "${MONITORING_DIR}/grafana-cloud-secrets-configured.yaml"
    else
        echo "Warning: Secrets not configured. Deployment will continue but monitoring will not work."
        echo "Please configure secrets manually later."
    fi
fi
echo

# Step 3: Deploy kube-state-metrics
echo "Step 3: Deploying kube-state-metrics..."
kubectl apply -f "${MONITORING_DIR}/kube-state-metrics.yaml"
echo "Waiting for kube-state-metrics to be ready..."
kubectl wait --for=condition=available --timeout=120s deployment/kube-state-metrics -n qnt9-monitoring || true
echo

# Step 4: Deploy Grafana Agent
echo "Step 4: Deploying Grafana Agent..."
kubectl apply -f "${MONITORING_DIR}/grafana-agent.yaml"
echo "Waiting for Grafana Agent pods to be ready..."
sleep 10
kubectl wait --for=condition=ready --timeout=120s pod -l app=grafana-agent -n qnt9-monitoring || true
echo

# Step 5: Verify deployment
echo "========================================"
echo "Deployment Status"
echo "========================================"
echo
echo "Pods in qnt9-monitoring namespace:"
kubectl get pods -n qnt9-monitoring
echo
echo "Services in qnt9-monitoring namespace:"
kubectl get svc -n qnt9-monitoring
echo

# Check if all pods are running
NOT_RUNNING=$(kubectl get pods -n qnt9-monitoring --no-headers | grep -v "Running" | wc -l || true)
if [ "$NOT_RUNNING" -gt 0 ]; then
    echo "Warning: Some pods are not running. Check logs:"
    echo "  kubectl logs -n qnt9-monitoring -l app=grafana-agent"
    echo "  kubectl logs -n qnt9-monitoring -l app=kube-state-metrics"
else
    echo "All monitoring pods are running successfully"
fi

echo
echo "========================================"
echo "Next Steps"
echo "========================================"
echo
echo "1. Verify metrics are being scraped:"
echo "   kubectl port-forward -n qnt9-monitoring svc/grafana-agent 80:80"
echo "   curl localhost:80/metrics"
echo
echo "2. Check agent logs:"
echo "   kubectl logs -n qnt9-monitoring -l app=grafana-agent --tail=50"
echo
echo "3. Verify data in Grafana Cloud:"
echo "   - Go to your Grafana Cloud dashboard"
echo "   - Check Explore > Metrics for incoming data"
echo "   - Check Explore > Logs for application logs"
echo
echo "4. Import pre-built dashboards:"
echo "   - Kubernetes Cluster Monitoring (ID: 7249)"
echo "   - Kubernetes Pods (ID: 6417)"
echo
echo "5. Create alerts in Grafana Cloud:"
echo "   - High error rate: rate(http_requests_total{status=~\"5..\"}[5m]) > 0.05"
echo "   - High latency: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2.0"
echo
echo "Deployment complete!"
