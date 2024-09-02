+++ 
draft = false
date = 2024-09-02T16:06:49+08:00
title = "为 Kubernetes ServiceAccount 生成 kubeconfig 文件"
authors = ["Maoqide"]
tags = ["kubernetes", "rbac"]
+++

为 Service Account 生成 kubeconfig 文件

<!--more-->

## 创建 Service Account 并绑定 ClusterRole
这里创建了一个 ServiceAccount `testsa` 并绑定了 `edit` ClusterRole，这样 ServiceAccount 就有了对应 Namespace 下的资源的读写权限。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sa-test
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: testsa
  namespace: sa-test
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: testsa-role-binding
  namespace: sa-test
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: edit
subjects:
- kind: ServiceAccount
  name: testsa
  namespace: sa-test
```

## 生成 kubeconfig 文件
为 Service Account 生成 kubeconfig 文件，这样就可以在本地使用 `kubectl` 命令行工具访问 Kubernetes 集群。 

```bash
#!/bin/bash
set -euo pipefail

# Variables
NAMESPACE="sa-test"
SERVICE_ACCOUNT_NAME="testsa"
KUBECONFIG_FILE="kubeconfig_${SERVICE_ACCOUNT_NAME}"
SECRET_NAME="$SERVICE_ACCOUNT_NAME-token"

# Create Secret token
# k8s 1.22+ 需要手动创建 kubernetes.io/service-account-token 类型的 Secret，为 ServiceAccount 生成长期有效的 token
kubectl -n $NAMESPACE apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: $SECRET_NAME
  annotations:
    kubernetes.io/service-account.name: $SERVICE_ACCOUNT_NAME
type: kubernetes.io/service-account-token
EOF

# Extract the bearer token from the secret
SA_TOKEN=$(kubectl get secret $SECRET_NAME \
           --namespace $NAMESPACE \
           -o jsonpath='{.data.token}' | base64 --decode)

# Get the API server endpoint
APISERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')

# Get the certificate authority
CA_CERT=$(kubectl get secret $SECRET_NAME \
          --namespace $NAMESPACE \
          -o jsonpath='{.data.ca\.crt}')

# Create kubeconfig file
cat > $KUBECONFIG_FILE <<EOF
apiVersion: v1
kind: Config
clusters:
- name: kubernetes
  cluster:
    certificate-authority-data: $CA_CERT
    server: $APISERVER
contexts:
- name: $SERVICE_ACCOUNT_NAME-context
  context:
    cluster: kubernetes
    namespace: $NAMESPACE
    user: $SERVICE_ACCOUNT_NAME
current-context: $SERVICE_ACCOUNT_NAME-context
users:
- name: $SERVICE_ACCOUNT_NAME
  user:
    token: $SA_TOKEN
EOF
```