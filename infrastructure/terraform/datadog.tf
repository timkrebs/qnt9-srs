# ===================================================
# Datadog Monitoring Configuration
# ===================================================
# NOTE: Datadog deployment is skipped during Terraform apply due to
# HCP Terraform Cloud limitations with the Kubernetes provider.
# Use the generated script to deploy Datadog after cluster creation.

# Generate Datadog installation script
resource "local_file" "datadog_install_script" {
  filename = "${path.module}/datadog-install.sh"
  
  content = <<-SCRIPT
#!/bin/bash
set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Installing Datadog on EKS Cluster"
echo "════════════════════════════════════════════════════════════════"

# Configuration
REGION="${var.region}"
CLUSTER_NAME="${module.eks.cluster_name}"
DATADOG_SITE="${data.vault_kv_secret_v2.datadog.data["datadog_site"]}"
DATADOG_API_KEY="${data.vault_kv_secret_v2.datadog.data["datadog_api_key"]}"

echo "Cluster: $CLUSTER_NAME"
echo "Region: $REGION"
echo "Datadog Site: $DATADOG_SITE"
echo ""

# Update kubeconfig
echo "→ Updating kubeconfig..."
aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER_NAME"

# Add Datadog Helm repo
echo "→ Adding Datadog Helm repository..."
helm repo add datadog https://helm.datadoghq.com
helm repo update

# Create namespace
echo "→ Creating datadog namespace..."
kubectl create namespace datadog --dry-run=client -o yaml | kubectl apply -f -

# Create secret
echo "→ Creating Datadog API key secret..."
kubectl create secret generic datadog-secret \
  -n datadog \
  --from-literal=api-key="$DATADOG_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

# Install Datadog
echo "→ Installing Datadog agent..."
helm upgrade --install datadog datadog/datadog \
  --namespace datadog \
  --version 3.57.0 \
  --set datadog.apiKeyExistingSecret=datadog-secret \
  --set datadog.site="$DATADOG_SITE" \
  --set datadog.clusterName="$(echo $CLUSTER_NAME | tr '[:upper:]' '[:lower:]')" \
  --set datadog.logs.enabled=true \
  --set datadog.logs.containerCollectAll=true \
  --set datadog.apm.portEnabled=true \
  --set datadog.apm.port=8126 \
  --set datadog.processAgent.enabled=true \
  --set datadog.networkMonitoring.enabled=true \
  --set datadog.serviceMonitoring.enabled=true \
  --set datadog.otlp.receiver.protocols.grpc.enabled=true \
  --set datadog.otlp.receiver.protocols.grpc.endpoint="0.0.0.0:4317" \
  --set datadog.otlp.receiver.protocols.http.enabled=true \
  --set datadog.otlp.receiver.protocols.http.endpoint="0.0.0.0:4318" \
  --set datadog.containerLifecycle.enabled=true \
  --set datadog.kubeStateMetricsCore.enabled=true \
  --set datadog.clusterChecks.enabled=true \
  --set datadog.admissionController.enabled=true \
  --set clusterAgent.enabled=true \
  --set clusterAgent.replicas=2 \
  --set clusterAgent.resources.requests.cpu="200m" \
  --set clusterAgent.resources.requests.memory="256Mi" \
  --set clusterAgent.resources.limits.cpu="500m" \
  --set clusterAgent.resources.limits.memory="512Mi" \
  --set agents.enabled=true \
  --set agents.resources.requests.cpu="200m" \
  --set agents.resources.requests.memory="256Mi" \
  --set agents.resources.limits.cpu="500m" \
  --set agents.resources.limits.memory="512Mi"

echo ""
echo "✓ Datadog installation complete!"
echo ""
echo "Check status with:"
echo "  kubectl get pods -n datadog"
echo ""
echo "View in Datadog at:"
echo "  https://$DATADOG_SITE/infrastructure"
echo "════════════════════════════════════════════════════════════════"
  SCRIPT

  file_permission = "0755"

  depends_on = [module.eks]
}

# Output instructions
output "datadog_deployment_instructions" {
  description = "Instructions for deploying Datadog monitoring"
  value = <<-INSTRUCTIONS
    ════════════════════════════════════════════════════════════════
    DATADOG MONITORING - POST-DEPLOYMENT STEP
    ════════════════════════════════════════════════════════════════
    
    Your EKS cluster is ready! To install Datadog monitoring, run:
    
      cd infrastructure/terraform
      ./datadog-install.sh
    
    This will install Datadog with all monitoring features enabled.
    
    ════════════════════════════════════════════════════════════════
  INSTRUCTIONS
}
