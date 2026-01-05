#!/bin/bash
# QNT9-SRS Kubernetes Deployment Script
# Usage: ./deploy.sh <environment> <service> <image_tag>
# Example: ./deploy.sh dev auth-service v1.0.0

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_BASE_DIR="${SCRIPT_DIR}/../kubernetes"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate inputs
validate_inputs() {
    local environment="$1"
    local service="$2"
    local image_tag="$3"

    if [[ ! "$environment" =~ ^(dev|staging|prd)$ ]]; then
        log_error "Invalid environment: $environment. Must be dev, staging, or prd."
        exit 1
    fi

    if [[ -z "$service" ]]; then
        log_error "Service name is required."
        exit 1
    fi

    if [[ -z "$image_tag" ]]; then
        log_error "Image tag is required."
        exit 1
    fi

    # Validate service directory exists
    if [[ ! -d "${K8S_BASE_DIR}/${service}" ]]; then
        log_error "Service directory not found: ${K8S_BASE_DIR}/${service}"
        exit 1
    fi
}

# Check required environment variables
check_env_vars() {
    local required_vars=("ACR_LOGIN_SERVER")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi
}

# Apply base resources (namespace, secrets, configmaps)
apply_base_resources() {
    local environment="$1"

    log_info "Applying base resources for environment: $environment"

    if [[ -d "${K8S_BASE_DIR}/base" ]]; then
        for manifest in "${K8S_BASE_DIR}"/base/*.yaml; do
            if [[ -f "$manifest" ]]; then
                log_info "Applying: $(basename "$manifest")"
                envsubst < "$manifest" | kubectl apply -f -
            fi
        done
    fi
}

# Deploy service
deploy_service() {
    local environment="$1"
    local service="$2"
    local image_tag="$3"
    local service_dir="${K8S_BASE_DIR}/${service}"

    log_info "Deploying $service to $environment with tag $image_tag"

    # Export variables for envsubst
    export ENVIRONMENT="$environment"
    export IMAGE_TAG="$image_tag"

    # Apply deployment
    if [[ -f "${service_dir}/deployment.yaml" ]]; then
        log_info "Applying deployment manifest"
        envsubst < "${service_dir}/deployment.yaml" | kubectl apply -f -
    fi

    # Apply service
    if [[ -f "${service_dir}/service.yaml" ]]; then
        log_info "Applying service manifest"
        envsubst < "${service_dir}/service.yaml" | kubectl apply -f -
    fi

    # Apply any additional manifests
    for manifest in "${service_dir}"/*.yaml; do
        local basename_manifest
        basename_manifest=$(basename "$manifest")
        if [[ "$basename_manifest" != "deployment.yaml" && "$basename_manifest" != "service.yaml" ]]; then
            log_info "Applying: $basename_manifest"
            envsubst < "$manifest" | kubectl apply -f -
        fi
    done
}

# Wait for deployment rollout
wait_for_rollout() {
    local service="$1"
    local timeout="${2:-300}"

    log_info "Waiting for $service deployment rollout (timeout: ${timeout}s)"

    if kubectl rollout status deployment/"$service" -n qnt9 --timeout="${timeout}s"; then
        log_info "Deployment $service rolled out successfully"
    else
        log_error "Deployment $service failed to roll out"
        kubectl get pods -n qnt9 -l app="$service"
        kubectl describe deployment "$service" -n qnt9
        exit 1
    fi
}

# Verify deployment health
verify_deployment() {
    local service="$1"

    log_info "Verifying $service deployment health"

    # Get pod status
    local ready_pods
    ready_pods=$(kubectl get pods -n qnt9 -l app="$service" -o jsonpath='{.items[*].status.containerStatuses[*].ready}' | tr ' ' '\n' | grep -c true || echo 0)

    local total_pods
    total_pods=$(kubectl get pods -n qnt9 -l app="$service" --no-headers | wc -l)

    if [[ "$ready_pods" -eq 0 ]]; then
        log_error "No ready pods found for $service"
        exit 1
    fi

    log_info "Ready pods: $ready_pods/$total_pods"

    # Get deployment info
    kubectl get deployment "$service" -n qnt9
}

# Print deployment summary
print_summary() {
    local environment="$1"
    local service="$2"
    local image_tag="$3"

    log_info "Deployment Summary"
    echo "-----------------------------------"
    echo "Environment: $environment"
    echo "Service: $service"
    echo "Image Tag: $image_tag"
    echo "Namespace: qnt9"
    echo "-----------------------------------"

    # Get service endpoint
    local service_ip
    service_ip=$(kubectl get svc "$service" -n qnt9 -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo "N/A")
    echo "Service IP: $service_ip"

    # Get pod count
    local pod_count
    pod_count=$(kubectl get pods -n qnt9 -l app="$service" --no-headers 2>/dev/null | wc -l || echo "0")
    echo "Pod Count: $pod_count"
}

# Main execution
main() {
    local environment="${1:-}"
    local service="${2:-}"
    local image_tag="${3:-}"

    # Show usage if no arguments
    if [[ -z "$environment" ]]; then
        echo "Usage: $0 <environment> <service> <image_tag>"
        echo "  environment: dev, staging, or prd"
        echo "  service: auth-service, search-service, webapp-service, user-service, watchlist-service"
        echo "  image_tag: Docker image tag (e.g., v1.0.0, sha-abc123)"
        exit 1
    fi

    validate_inputs "$environment" "$service" "$image_tag"
    check_env_vars

    # Apply base resources first
    apply_base_resources "$environment"

    # Deploy the service
    deploy_service "$environment" "$service" "$image_tag"

    # Wait for rollout
    wait_for_rollout "$service"

    # Verify deployment
    verify_deployment "$service"

    # Print summary
    print_summary "$environment" "$service" "$image_tag"

    log_info "Deployment completed successfully"
}

main "$@"
