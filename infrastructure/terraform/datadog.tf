# ===================================================
# Datadog Monitoring Configuration
# ===================================================

# Create Datadog namespace
resource "kubernetes_namespace" "datadog" {
  metadata {
    name = "datadog"
    labels = {
      name = "datadog"
    }
  }

  depends_on = [module.eks]
}

# Create Datadog API Key secret
# API key is retrieved from HCP Vault
resource "kubernetes_secret" "datadog_api_key" {
  metadata {
    name      = "datadog-secret"
    namespace = kubernetes_namespace.datadog.metadata[0].name
  }

  data = {
    api-key = data.vault_kv_secret_v2.datadog.data["datadog_api_key"]
  }

  type = "Opaque"

  depends_on = [kubernetes_namespace.datadog]
}

# Deploy Datadog Agent via Helm Chart (Simplified Approach)
# Using the official Datadog Helm chart instead of Operator + CRDs
resource "helm_release" "datadog_agent" {
  name       = "datadog"
  repository = "https://helm.datadoghq.com"
  chart      = "datadog"
  namespace  = kubernetes_namespace.datadog.metadata[0].name
  version    = "3.57.0"

  values = [
    yamlencode({
      datadog = {
        apiKeyExistingSecret = kubernetes_secret.datadog_api_key.metadata[0].name
        site                 = data.vault_kv_secret_v2.datadog.data["datadog_site"]
        clusterName          = lower(module.eks.cluster_name)

        # Logging
        logs = {
          enabled             = true
          containerCollectAll = true
        }

        # APM
        apm = {
          portEnabled = true
          port        = 8126
        }

        # Process monitoring
        processAgent = {
          enabled = true
        }

        # Network Performance Monitoring
        networkMonitoring = {
          enabled = true
        }

        # Universal Service Monitoring
        serviceMonitoring = {
          enabled = true
        }

        # OpenTelemetry
        otlp = {
          receiver = {
            protocols = {
              grpc = {
                enabled  = true
                endpoint = "0.0.0.0:4317"
              }
              http = {
                enabled  = true
                endpoint = "0.0.0.0:4318"
              }
            }
          }
        }

        # Container lifecycle events
        containerLifecycle = {
          enabled = true
        }

        # Kubernetes State Metrics Core
        kubeStateMetricsCore = {
          enabled = true
        }

        # Cluster checks
        clusterChecks = {
          enabled = true
        }

        # Admission Controller
        admissionController = {
          enabled = true
        }
      }

      # Cluster Agent configuration
      clusterAgent = {
        enabled  = true
        replicas = 2

        resources = {
          requests = {
            cpu    = "200m"
            memory = "256Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }

      # Agent configuration (node agent)
      agents = {
        enabled = true

        resources = {
          requests = {
            cpu    = "200m"
            memory = "256Mi"
          }
          limits = {
            cpu    = "500m"
            memory = "512Mi"
          }
        }
      }
    })
  ]

  depends_on = [
    kubernetes_secret.datadog_api_key,
    kubernetes_namespace.datadog
  ]
}
