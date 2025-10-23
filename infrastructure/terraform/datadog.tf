# ===================================================
# Datadog Monitoring Configuration
# ===================================================
# NOTE: Datadog deployment is skipped during Terraform apply due to
# HCP Terraform Cloud limitations with the Kubernetes provider.
# Use the generated scripts to deploy Datadog after cluster creation.

# Generate Datadog Operator installation script
resource "local_file" "datadog_operator_install_script" {
  filename = "${path.module}/datadog-operator-install.sh"

  content = <<-SCRIPT
#!/bin/bash
set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Installing Datadog Operator on EKS Cluster"
echo "════════════════════════════════════════════════════════════════"

# Configuration
REGION="${var.region}"
CLUSTER_NAME="${module.eks.cluster_name}"
DATADOG_API_KEY="${data.vault_kv_secret_v2.datadog.data["datadog_api_key"]}"

echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"
echo ""

# Update kubeconfig
echo "→ Updating kubeconfig..."
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER_NAME"

# Add Datadog Helm repo
echo "→ Adding Datadog Helm repository..."
helm repo add datadog https://helm.datadoghq.com
helm repo update

# Install Datadog Operator
echo "→ Installing Datadog Operator..."
helm install datadog-operator datadog/datadog-operator

# Wait for operator to be ready
echo "→ Waiting for Datadog Operator to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/datadog-operator -n default

# Create Datadog secret
echo "→ Creating Datadog API key secret..."
kubectl create secret generic datadog-secret \
  --from-literal=api-key="$DATADOG_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "✓ Datadog Operator installation complete!"
echo ""
echo "Next step: Deploy the Datadog Agent using:"
echo "  kubectl apply -f datadog-agent.yaml"
echo ""
echo "════════════════════════════════════════════════════════════════"
  SCRIPT

  file_permission = "0755"

  depends_on = [module.eks]
}

# Generate Datadog Agent manifest
resource "local_file" "datadog_agent_manifest" {
  filename = "${path.module}/datadog-agent.yaml"

  content = <<-YAML
apiVersion: datadoghq.com/v2alpha1
kind: DatadogAgent
metadata:
  name: datadog
spec:
  global:
    site: "${data.vault_kv_secret_v2.datadog.data["datadog_site"]}"
    clusterName: "${lower(module.eks.cluster_name)}"
    credentials:
      apiSecret:
        secretName: datadog-secret
        keyName: api-key
  
  features:
    # APM with auto-instrumentation
    apm:
      enabled: true
      instrumentation:
        enabled: true
        targets:
          - name: default-target
            ddTraceVersions:
              java: "1"
              python: "3"
              js: "5"
              php: "1"
              dotnet: "3"
              ruby: "2"
    
    # Log collection
    logCollection:
      enabled: true
      containerCollectAll: true
    
    # OpenTelemetry collector
    otelCollector:
      enabled: true
      ports:
        - containerPort: 4317
          hostPort: 4317
          name: otel-grpc
        - containerPort: 4318
          hostPort: 4318
          name: otel-http
    
    # Additional monitoring features
    processDiscovery:
      enabled: true
    
    liveProcessCollection:
      enabled: true
    
    liveContainerCollection:
      enabled: true
    
    networkMonitoring:
      enabled: true
    
    serviceMonitoring:
      enabled: true
    
    orchestratorExplorer:
      enabled: true
  YAML

  depends_on = [module.eks]
}

# Output instructions
output "datadog_deployment_instructions" {
  description = "Instructions for deploying Datadog monitoring"
  value       = <<-INSTRUCTIONS
    ════════════════════════════════════════════════════════════════
    DATADOG MONITORING - POST-DEPLOYMENT STEPS
    ════════════════════════════════════════════════════════════════
    
    Your EKS cluster is ready! Deploy Datadog in 2 steps:
    
    STEP 1: Install Datadog Operator
      cd infrastructure/terraform
      ./datadog-operator-install.sh
    
    STEP 2: Deploy Datadog Agent
      kubectl apply -f datadog-agent.yaml
    
    Check status:
      kubectl get datadogagent
      kubectl get pods -l app.kubernetes.io/name=datadog
    
    View in Datadog:
      https://${data.vault_kv_secret_v2.datadog.data["datadog_site"]}/infrastructure
    
    ════════════════════════════════════════════════════════════════
  INSTRUCTIONS
}
