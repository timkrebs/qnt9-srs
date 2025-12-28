#!/bin/bash
# Configure Icinga2 to monitor Kubernetes cluster
# This script should be run after Icinga2 is installed

set -e

echo "Configuring Kubernetes monitoring in Icinga2..."

# Install kubectl
echo "Installing kubectl..."
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm kubectl

# Install Kubernetes monitoring plugins
echo "Installing Kubernetes monitoring plugins..."
sudo apt-get install -y python3-pip git
sudo pip3 install kubernetes requests

# Clone check_kubernetes plugin
cd /tmp
git clone https://github.com/tomrijndorp/icinga2-kubernetes.git
sudo cp icinga2-kubernetes/check_kubernetes.py /usr/lib/nagios/plugins/
sudo chmod +x /usr/lib/nagios/plugins/check_kubernetes.py

# Create Kubernetes monitoring configuration
echo "Creating Kubernetes monitoring configuration..."
sudo tee /etc/icinga2/conf.d/kubernetes.conf > /dev/null <<'EOF'
# Kubernetes Host
object Host "kubernetes-cluster" {
  import "generic-host"
  address = "127.0.0.1"
  vars.notification["mail"] = {
    groups = [ "icingaadmins" ]
  }
}

# Kubernetes API Service
object Service "k8s-api" {
  import "generic-service"
  host_name = "kubernetes-cluster"
  check_command = "http"
  vars.http_uri = "/healthz"
  vars.http_vhost = "kubernetes.default"
  vars.http_ssl = true
  vars.http_sni = true
}

# Kubernetes Nodes Service
object Service "k8s-nodes" {
  import "generic-service"
  host_name = "kubernetes-cluster"
  check_command = "check_kubernetes_nodes"
}

# Kubernetes Pods Service
object Service "k8s-pods" {
  import "generic-service"
  host_name = "kubernetes-cluster"
  check_command = "check_kubernetes_pods"
}

# Kubernetes Deployments Service
object Service "k8s-deployments" {
  import "generic-service"
  host_name = "kubernetes-cluster"
  check_command = "check_kubernetes_deployments"
}
EOF

# Create check commands
sudo tee /etc/icinga2/conf.d/kubernetes-commands.conf > /dev/null <<'EOF'
object CheckCommand "check_kubernetes_nodes" {
  command = [ "/usr/lib/nagios/plugins/check_kubernetes.py" ]
  arguments = {
    "--object" = "nodes"
    "--warning" = "$k8s_warning$"
    "--critical" = "$k8s_critical$"
  }
}

object CheckCommand "check_kubernetes_pods" {
  command = [ "/usr/lib/nagios/plugins/check_kubernetes.py" ]
  arguments = {
    "--object" = "pods"
    "--namespace" = "$k8s_namespace$"
    "--warning" = "$k8s_warning$"
    "--critical" = "$k8s_critical$"
  }
}

object CheckCommand "check_kubernetes_deployments" {
  command = [ "/usr/lib/nagios/plugins/check_kubernetes.py" ]
  arguments = {
    "--object" = "deployments"
    "--namespace" = "$k8s_namespace$"
    "--warning" = "$k8s_warning$"
    "--critical" = "$k8s_critical$"
  }
}
EOF

# Restart Icinga2
echo "Restarting Icinga2..."
sudo systemctl restart icinga2

echo ""
echo "========================================="
echo "Kubernetes monitoring configured!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Configure kubectl with your AKS credentials:"
echo "   az aks get-credentials --resource-group <rg> --name <aks-name>"
echo ""
echo "2. Create a service account for Icinga:"
echo "   kubectl create serviceaccount icinga-monitoring -n kube-system"
echo "   kubectl create clusterrolebinding icinga-monitoring \\"
echo "     --clusterrole=cluster-admin \\"
echo "     --serviceaccount=kube-system:icinga-monitoring"
echo ""
echo "3. Check services in Icinga Web 2"
echo "========================================="
