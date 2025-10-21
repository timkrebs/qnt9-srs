# Datadog Monitoring Setup for EKS Cluster using Datadog Operator
# Based on official Datadog documentation
# API Key is configured as a Terraform variable in HCP Terraform

# Kubernetes Secret for Datadog API Key
resource "kubernetes_secret_v1" "datadog_secret" {
  metadata {
    name      = "datadog-secret"
    namespace = "default"
  }

  data = {
    api-key = var.datadog_api_key
  }

  type = "Opaque"

  depends_on = [module.eks]
}

# Install Datadog Operator via Helm
resource "helm_release" "datadog_operator" {
  name       = "datadog-operator"
  repository = "https://helm.datadoghq.com"
  chart      = "datadog-operator"
  namespace  = "default"

  depends_on = [
    kubernetes_secret_v1.datadog_secret,
    module.eks
  ]
}

# Deploy DatadogAgent Custom Resource
resource "kubernetes_manifest" "datadog_agent" {
  manifest = {
    apiVersion = "datadoghq.com/v2alpha1"
    kind       = "DatadogAgent"
    metadata = {
      name      = "datadog"
      namespace = "default"
    }
    spec = {
      global = {
        site = "us3.datadoghq.com"
        credentials = {
          apiSecret = {
            secretName = kubernetes_secret_v1.datadog_secret.metadata[0].name
            keyName    = "api-key"
          }
        }
        clusterName = module.eks.cluster_name
        tags = [
          "env:production",
          "project:qnt9-srs",
          "cluster:${module.eks.cluster_name}"
        ]
      }
      features = {
        # APM with automatic instrumentation
        apm = {
          enabled = true
          instrumentation = {
            enabled = true
            targets = [
              {
                name = "default-target"
                ddTraceVersions = {
                  java   = "1"
                  python = "2"
                  js     = "5"
                  php    = "1"
                  dotnet = "3"
                  ruby   = "2"
                }
              }
            ]
          }
        }
        # Log Collection
        logCollection = {
          enabled            = true
          containerCollectAll = true
        }
        # OpenTelemetry Collector
        otelCollector = {
          enabled = true
          ports = [
            {
              containerPort = 4317
              hostPort      = 4317
              name          = "otel-grpc"
            },
            {
              containerPort = 4318
              hostPort      = 4318
              name          = "otel-http"
            }
          ]
        }
        # Live Container Monitoring
        liveContainerCollection = {
          enabled = true
        }
        # Orchestrator Explorer
        orchestratorExplorer = {
          enabled = true
        }
        # Process Monitoring
        processDiscovery = {
          enabled = true
        }
      }
    }
  }

  depends_on = [helm_release.datadog_operator]
}

