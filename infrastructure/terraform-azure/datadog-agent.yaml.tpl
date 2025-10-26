apiVersion: datadoghq.com/v2alpha1
kind: DatadogAgent
metadata:
  name: datadog
  namespace: datadog
spec:
  global:
    clusterName: ${cluster_name}
    site: ${datadog_site}
    credentials:
      apiSecret:
        secretName: datadog-secret
        keyName: api-key
    kubelet:
      tlsVerify: false
  features:
    apm:
      enabled: true
      hostPortConfig:
        enabled: true
        hostPort: 8126
    logCollection:
      enabled: true
      containerCollectAll: true
    liveProcessCollection:
      enabled: true
    liveContainerCollection:
      enabled: true
    npm:
      enabled: true
    orchestratorExplorer:
      enabled: true
    kubeStateMetricsCore:
      enabled: true
    prometheusScrape:
      enabled: true
  override:
    clusterAgent:
      replicas: 1
      image:
        tag: latest
