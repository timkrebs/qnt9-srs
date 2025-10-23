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

# Install Datadog Operator via Helm
resource "helm_release" "datadog_operator" {
  name       = "datadog-operator"
  repository = "https://helm.datadoghq.com"
  chart      = "datadog-operator"
  namespace  = kubernetes_namespace.datadog.metadata[0].name
  version    = "1.4.0"

  values = [
    yamlencode({
      image = {
        tag = "1.4.0"
      }
    })
  ]

  depends_on = [kubernetes_namespace.datadog]
}

# Deploy Datadog Agent via CRD
resource "kubernetes_manifest" "datadog_agent" {
  manifest = {
    apiVersion = "datadoghq.com/v2alpha1"
    kind       = "DatadogAgent"

    metadata = {
      name      = "datadog"
      namespace = kubernetes_namespace.datadog.metadata[0].name
    }

    spec = {
      global = {
        site        = data.vault_kv_secret_v2.datadog.data["datadog_site"]
        clusterName = module.eks.cluster_name

        credentials = {
          apiSecret = {
            secretName = kubernetes_secret.datadog_api_key.metadata[0].name
            keyName    = "api-key"
          }
        }

        kubelet = {
          tlsVerify = false
        }
      }

      features = {
        # Enable APM (Application Performance Monitoring)
        apm = {
          enabled = true
          hostPortConfig = {
            enabled  = true
            hostPort = 8126
          }
        }

        # Enable Log Collection
        logCollection = {
          enabled                    = true
          containerCollectAll        = true
          containerCollectUsingFiles = true
        }

        # Enable OpenTelemetry Collector
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

        # Enable Live Container Monitoring
        liveContainerCollection = {
          enabled = true
        }

        # Enable Network Performance Monitoring
        npm = {
          enabled = true
        }

        # Enable Universal Service Monitoring
        usm = {
          enabled = true
        }

        # Enable Cluster Checks
        clusterChecks = {
          enabled = true
        }

        # Enable Kubernetes State Metrics Core
        kubeStateMetricsCore = {
          enabled = true
        }

        # Enable Admission Controller
        admissionController = {
          enabled = true
        }
      }

      override = {
        clusterAgent = {
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

        nodeAgent = {
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
      }
    }
  }

  depends_on = [
    helm_release.datadog_operator,
    kubernetes_secret.datadog_api_key
  ]
}
