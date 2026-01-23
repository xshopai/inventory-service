# Azure Kubernetes Service (AKS) Deployment Guide

This guide provides step-by-step instructions for deploying the Inventory Service to **Azure Kubernetes Service (AKS)** with Dapr integration.

---

## Prerequisites

- **Azure CLI** installed - [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- **kubectl** installed - [Install kubectl](https://kubernetes.io/docs/tasks/tools/)
- **Helm 3+** installed - [Install Helm](https://helm.sh/docs/intro/install/)
- **Azure Subscription** with appropriate permissions
- **Docker** installed for building images

---

## Step-by-Step Deployment

### Step 1: Login to Azure and Set Subscription

```bash
# Login to Azure
az login

# Set subscription
az account set --subscription "<subscription-id>"

# Verify
az account show
```

### Step 2: Create Resource Group

```bash
# Set variables
RESOURCE_GROUP="rg-inventory-aks"
LOCATION="eastus"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 3: Create Azure Container Registry

```bash
# Set ACR name (globally unique)
ACR_NAME="acrinventoryaks"

# Create ACR
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Standard

# Login to ACR
az acr login --name $ACR_NAME

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
```

### Step 4: Create AKS Cluster

```bash
# Set cluster name
CLUSTER_NAME="aks-inventory-cluster"

# Create AKS cluster with Azure CNI
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --node-count 2 \
  --node-vm-size Standard_D2s_v3 \
  --enable-managed-identity \
  --attach-acr $ACR_NAME \
  --network-plugin azure \
  --enable-addons monitoring \
  --generate-ssh-keys

# Get cluster credentials
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME

# Verify connection
kubectl get nodes
```

### Step 5: Install Dapr on AKS

```bash
# Add Dapr Helm repository
helm repo add dapr https://dapr.github.io/helm-charts/
helm repo update

# Create namespace for Dapr
kubectl create namespace dapr-system

# Install Dapr
helm install dapr dapr/dapr \
  --namespace dapr-system \
  --set global.ha.enabled=true \
  --wait

# Verify Dapr installation
kubectl get pods -n dapr-system

# You should see:
# - dapr-operator
# - dapr-placement-server
# - dapr-sentry
# - dapr-sidecar-injector
```

### Step 6: Build and Push Docker Image

```bash
# Build image
docker build -t inventory-service:latest .

# Tag for ACR
docker tag inventory-service:latest $ACR_LOGIN_SERVER/inventory-service:latest

# Push to ACR
docker push $ACR_LOGIN_SERVER/inventory-service:latest
```

### Step 7: Create Kubernetes Namespace

```bash
# Create namespace for the application
kubectl create namespace inventory

# Set as default namespace
kubectl config set-context --current --namespace=inventory
```

### Step 8: Create Kubernetes Secrets

```bash
# Database credentials
kubectl create secret generic inventory-db-secret \
  --from-literal=username=admin \
  --from-literal=password=<db-password> \
  --from-literal=database=inventory_service_db \
  --from-literal=host=<mysql-server>.mysql.database.azure.com \
  -n inventory

# JWT secret
kubectl create secret generic inventory-jwt-secret \
  --from-literal=jwt-secret=<your-jwt-secret> \
  -n inventory

# Service tokens
kubectl create secret generic inventory-service-tokens \
  --from-literal=product-service-token=<token> \
  --from-literal=order-service-token=<token> \
  --from-literal=cart-service-token=<token> \
  --from-literal=web-bff-token=<token> \
  -n inventory
```

### Step 9: Create Dapr Components

Create `k8s/dapr-components.yaml`:

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: inventory-pubsub
  namespace: inventory
spec:
  type: pubsub.azure.servicebus
  version: v1
  metadata:
    - name: connectionString
      value: "<service-bus-connection-string>"
    - name: consumerID
      value: inventory-service
---
apiVersion: dapr.io/v1alpha1
kind: Subscription
metadata:
  name: product-events
  namespace: inventory
spec:
  topic: product.created
  route: /events/product-created
  pubsubname: inventory-pubsub
---
apiVersion: dapr.io/v1alpha1
kind: Subscription
metadata:
  name: order-events
  namespace: inventory
spec:
  topic: order.cancelled
  route: /events/order-cancelled
  pubsubname: inventory-pubsub
```

Apply components:

```bash
kubectl apply -f k8s/dapr-components.yaml
```

### Step 10: Create Kubernetes Deployment

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inventory-service
  namespace: inventory
spec:
  replicas: 2
  selector:
    matchLabels:
      app: inventory-service
  template:
    metadata:
      labels:
        app: inventory-service
      annotations:
        dapr.io/enabled: "true"
        dapr.io/app-id: "inventory-service"
        dapr.io/app-port: "8004"
        dapr.io/log-level: "info"
    spec:
      containers:
      - name: inventory-service
        image: <acr-name>.azurecr.io/inventory-service:latest
        ports:
        - containerPort: 8004
        env:
        - name: FLASK_ENV
          value: "production"
        - name: MESSAGING_PROVIDER
          value: "dapr"
        - name: DAPR_PUBSUB_NAME
          value: "inventory-pubsub"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: inventory-db-secret
              key: connection-string
        - name: PRODUCT_SERVICE_TOKEN
          valueFrom:
            secretKeyRef:
              name: inventory-service-tokens
              key: product-service-token
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8004
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: inventory-service
  namespace: inventory
spec:
  selector:
    app: inventory-service
  ports:
  - port: 80
    targetPort: 8004
  type: LoadBalancer
```

Apply deployment:

```bash
kubectl apply -f k8s/deployment.yaml
```

### Step 11: Verify Deployment

```bash
# Check pods
kubectl get pods -n inventory

# Check pod logs
kubectl logs -f deployment/inventory-service -n inventory

# Check Dapr sidecar logs
kubectl logs -f deployment/inventory-service -c daprd -n inventory

# Get service external IP
kubectl get service inventory-service -n inventory
```

### Step 12: Test the Deployed Service

```bash
# Get service IP
SERVICE_IP=$(kubectl get service inventory-service -n inventory -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health endpoint
curl http://$SERVICE_IP/health

# Test API endpoint
curl http://$SERVICE_IP/api/inventory/
```

---

## Configure Ingress (Optional)

### Using NGINX Ingress Controller

```bash
# Install NGINX ingress
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Create ingress resource
kubectl apply -f - <<INGRESS
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: inventory-ingress
  namespace: inventory
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: inventory.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: inventory-service
            port:
              number: 80
INGRESS
```

---

## Monitoring and Observability

### View Logs

```bash
# Application logs
kubectl logs -f deployment/inventory-service -n inventory

# Dapr sidecar logs
kubectl logs -f deployment/inventory-service -c daprd -n inventory

# All pods in namespace
kubectl logs -f -l app=inventory-service -n inventory --all-containers
```

### Check Resource Usage

```bash
# Pod resource usage
kubectl top pods -n inventory

# Node resource usage
kubectl top nodes
```

### Describe Pod for Debugging

```bash
# Get detailed pod information
kubectl describe pod <pod-name> -n inventory

# Check events
kubectl get events -n inventory --sort-by='.lastTimestamp'
```

---

## Scaling

### Manual Scaling

```bash
# Scale deployment
kubectl scale deployment inventory-service --replicas=5 -n inventory

# Verify scaling
kubectl get pods -n inventory
```

### Horizontal Pod Autoscaler

```bash
# Create HPA based on CPU
kubectl autoscale deployment inventory-service \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n inventory

# Check HPA status
kubectl get hpa -n inventory
```

---

## Update Deployment

```bash
# Update image to new version
kubectl set image deployment/inventory-service \
  inventory-service=<acr-name>.azurecr.io/inventory-service:v1.1.0 \
  -n inventory

# Check rollout status
kubectl rollout status deployment/inventory-service -n inventory

# Rollback if needed
kubectl rollout undo deployment/inventory-service -n inventory
```

---

## Cleanup

```bash
# Delete deployment
kubectl delete -f k8s/deployment.yaml

# Delete Dapr components
kubectl delete -f k8s/dapr-components.yaml

# Delete namespace
kubectl delete namespace inventory

# Delete AKS cluster
az aks delete \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --yes
```

---

## Quick Reference

```bash
# Get pod status
kubectl get pods -n inventory

# View logs
kubectl logs -f deployment/inventory-service -n inventory

# Execute command in pod
kubectl exec -it <pod-name> -n inventory -- /bin/bash

# Port forward for local testing
kubectl port-forward deployment/inventory-service 8004:8004 -n inventory

# Get service endpoint
kubectl get service inventory-service -n inventory

# Check Dapr components
kubectl get components -n inventory

# Check Dapr subscriptions
kubectl get subscriptions -n inventory
```

---

## Best Practices

✅ **Use namespaces** to isolate environments (dev, staging, prod)  
✅ **Configure resource limits** to prevent resource exhaustion  
✅ **Set up health probes** for automatic recovery  
✅ **Use secrets** for sensitive configuration  
✅ **Enable pod security policies** for security hardening  
✅ **Configure network policies** to restrict pod-to-pod traffic  
✅ **Use Helm charts** for managing complex deployments  
✅ **Implement CI/CD** with Azure DevOps or GitHub Actions  

---

## Next Steps

- **Container Apps Deployment**: See [ACA_DEPLOYMENT.md](ACA_DEPLOYMENT.md)
- **Local Development**: See [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)
- **API Documentation**: See [PRD.md](PRD.md)
