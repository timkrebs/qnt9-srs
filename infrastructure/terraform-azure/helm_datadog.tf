# Datadog Operator Helm Chart Installation for AKS
# This installs the Datadog Operator which manages the DatadogAgent custom resource

# Install Datadog Operator via local-exec (after cluster is ready)
resource "null_resource" "datadog_operator_install" {
  depends_on = [azurerm_kubernetes_cluster.main]

  provisioner "local-exec" {
    command = <<-EOT
      az aks get-credentials --name ${azurerm_kubernetes_cluster.main.name} --resource-group ${azurerm_resource_group.main.name} --overwrite-existing
      helm repo add datadog https://helm.datadoghq.com || true
      helm repo update
      helm upgrade --install datadog-operator datadog/datadog-operator \
        --namespace datadog \
        --create-namespace \
        --version 1.7.0 \
        --set replicaCount=1 \
        --wait
    EOT
  }

  triggers = {
    cluster_name = azurerm_kubernetes_cluster.main.name
  }
}

# Create Kubernetes secret for Datadog API key via kubectl (from Vault)
resource "null_resource" "datadog_secret" {
  depends_on = [null_resource.datadog_operator_install]

  provisioner "local-exec" {
    command = <<-EOT
      az aks get-credentials --name ${azurerm_kubernetes_cluster.main.name} --resource-group ${azurerm_resource_group.main.name} --overwrite-existing
      kubectl create secret generic datadog-secret \
        --from-literal=api-key=${local.datadog_api_key} \
        --namespace=datadog \
        --dry-run=client -o yaml | kubectl apply -f -
    EOT
  }

  triggers = {
    api_key_hash = sha256(local.datadog_api_key)
  }
}

# Generate DatadogAgent manifest with cluster name and Vault-provided site
resource "local_file" "datadog_agent_manifest" {
  content = templatefile("${path.module}/datadog-agent.yaml.tpl", {
    cluster_name = azurerm_kubernetes_cluster.main.name
    datadog_site = local.datadog_site
  })
  filename = "${path.module}/datadog-agent-generated.yaml"
}

# Deploy DatadogAgent custom resource via kubectl
resource "null_resource" "datadog_agent" {
  depends_on = [
    null_resource.datadog_secret,
    local_file.datadog_agent_manifest
  ]

  provisioner "local-exec" {
    command = <<-EOT
      az aks get-credentials --name ${azurerm_kubernetes_cluster.main.name} --resource-group ${azurerm_resource_group.main.name} --overwrite-existing
      kubectl apply -f ${path.module}/datadog-agent-generated.yaml
    EOT
  }

  triggers = {
    manifest_content = local_file.datadog_agent_manifest.content
    cluster_name     = azurerm_kubernetes_cluster.main.name
  }
}

# Output Datadog configuration details
output "datadog_operator_status" {
  description = "Datadog Operator deployment status"
  sensitive   = true
  value = {
    namespace        = "datadog"
    chart_version    = "1.7.0"
    status           = "deployed"
    datadog_site     = local.datadog_site
    secrets_from     = "HCP Vault"
    vault_kv_path    = "kv/datadog"
  }
}
