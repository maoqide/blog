+++
draft = false
date = 2024-05-10T13:51:54+08:00
title = "kubernetes 集群开启审计日志"
authors = "Maoqide"
tags = ["kubernetes", "audit"]
categories = []
+++

开启 kubernetes apiserver 的审计日志。
<!--more--> 

## Kubernetes 审计
关于 Kubernetes 审计的详细信息，可以查看官方文档：https://kubernetes.io/zh-cn/docs/tasks/debug-application-cluster/audit/

简单来说，kube-apiserver 能够记录所有请求到集群的请求和响应。根据你配置的审计策略，审计日志可以记录请求的元数据，例如请求的时间、请求的资源、请求的操作、请求的用户、请求的 IP 地址等，还可以记录了请求的响应，例如响应的状态码、响应的资源等。当然，越详细的审计策略，就会耗费更多的资源，日志量也会更大。所以你需要根据自己的需求来配置审计策略。

审计日志支持通过日志文件和 webhook 两种方式输出。我是通过日志文件的方式，然后由 vector 进行日志收集，再由 loki 进行日志存储和查询。

关于审计策略，可以根据自己的需求进行配置，最简单的配置如下：

```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: Metadata
```

这是最低级别的审计策略，只记录请求的元数据，不记录请求的响应。官方还提供了一个 GCP 的脚本 ![configure-helper.sh](https://github.com/kubernetes/kubernetes/blob/master/cluster/gce/gci/configure-helper.sh)，可以生成审计策略文件，可以参考脚本中的配置进行修改。

## 开启审计
这里记录一下我自己的配置操作，我的集群是使用 kubeadm 部署的。

### 1.更改 kubeadm 配置

#### 备份 kubeadm-config
```bash
kubectl -nkube-system get cm kubeadm-config -oyaml > kubeadm-config.yaml
```

#### 编辑 kubeadm-config
```bash
kubectl -nkube-system edit cm kubeadm-config
```

添加如下 apiserver 配置，将静态 pod 启动的 apiserver 日志目录挂载到宿主机上，方便日志收集。添加 audit 相关配置，并且将审计策略文件挂载到 apiserver 容器中。
```yaml
... ...
    apiServer:
      extraArgs:
        ... ...
        audit-policy-file: /etc/kubernetes/audit/audit-policy.yaml
        audit-log-path: /var/log/kubernetes/audit/audit.log
        audit-log-maxage: "30"
        audit-log-maxbackup: "5"
        audit-log-maxsize: "200"
        log-dir: /var/log/kubernetes
        logtostderr: "false"
        v: "2"
      extraVolumes:
       - name: "audit"
         hostPath: "/etc/kubernetes/audit"
         mountPath: "/etc/kubernetes/audit"
         pathType: DirectoryOrCreate
       - name: "log"
         hostPath: "/data/logs/kubernetes"
         mountPath: "/var/log/kubernetes"
         pathType: DirectoryOrCreate
      timeoutForControlPlane: 4m0s
... ...
```

### 2.创建审计策略文件
在 control-plane 节点上创建审计策略文件。这里是我的审计策略，根据上面提到的 GCP 脚本生成的审计策略进行了一些修改，减少了一些不必要的日志记录。
```bash
cat <<EOF > /etc/kubernetes/audit/audit-policy.yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # The following requests were manually identified as high-volume and low-risk,
  # so drop them.
  - level: None
    users: ["system:kube-proxy"]
    verbs: ["watch"]
    resources:
      - group: "" # core
        resources: ["endpoints", "services", "services/status"]
  - level: None
    # Ingress controller reads 'configmaps/ingress-uid' through the unsecured port.
    # TODO(#46983): Change this to the ingress controller service account.
    users: ["system:unsecured"]
    namespaces: ["kube-system"]
    verbs: ["get"]
    resources:
      - group: "" # core
        resources: ["configmaps"]
  - level: None
    users: ["kubelet"] # legacy kubelet identity
    verbs: ["get"]
    resources:
      - group: "" # core
        resources: ["nodes", "nodes/status"]
  - level: None
    userGroups: ["system:nodes"]
    verbs: ["get"]
    resources:
      - group: "" # core
        resources: ["nodes", "nodes/status"]
  - level: None
    users:
      - system:kube-controller-manager
      - system:cloud-controller-manager
      - system:kube-scheduler
      - system:serviceaccount:kube-system:endpoint-controller
    verbs: ["get", "update"]
    namespaces: ["kube-system"]
    resources:
      - group: "" # core
        resources: ["endpoints"]
  - level: None
    users: ["system:apiserver"]
    verbs: ["get"]
    resources:
      - group: "" # core
        resources: ["namespaces", "namespaces/status", "namespaces/finalize"]
  - level: None
    users: ["cluster-autoscaler"]
    verbs: ["get", "update"]
    namespaces: ["kube-system"]
    resources:
      - group: "" # core
        resources: ["configmaps", "endpoints"]
  # Don't log HPA fetching metrics.
  - level: None
    users:
      - system:kube-controller-manager
      - system:cloud-controller-manager
    verbs: ["get", "list"]
    resources:
      - group: "metrics.k8s.io"
  # Don't log these read-only URLs.
  - level: None
    nonResourceURLs:
      - /healthz*
      - /version
      - /swagger*
  # Don't log events requests because of performance impact.
  - level: None
    resources:
      - group: "" # core
        resources: ["events"]
  # node and pod status calls from nodes are high-volume and can be large, don't log responses for expected updates from nodes
  - level: Request
    users: ["kubelet", "system:node-problem-detector", "system:serviceaccount:kube-system:node-problem-detector"]
    verbs: ["update","patch"]
    resources:
      - group: "" # core
        resources: ["nodes/status", "pods/status"]
    omitStages:
      - "RequestReceived"
  - level: Request
    userGroups: ["system:nodes"]
    verbs: ["update","patch"]
    resources:
      - group: "" # core
        resources: ["nodes/status", "pods/status"]
    omitStages:
      - "RequestReceived"
  # deletecollection calls can be large, don't log responses for expected namespace deletions
  - level: Request
    users: ["system:serviceaccount:kube-system:namespace-controller"]
    verbs: ["deletecollection"]
    omitStages:
      - "RequestReceived"
  # Secrets, ConfigMaps, TokenRequest and TokenReviews can contain sensitive & binary data,
  # so only log at the Metadata level.
  - level: Metadata
    resources:
      - group: "" # core
        resources: ["secrets", "configmaps", "serviceaccounts/token"]
      - group: authentication.k8s.io
        resources: ["tokenreviews"]
    omitStages:
      - "RequestReceived"
  # Get responses can be large; skip them.
  - level: Request
    verbs: ["get", "list", "watch"]
    resources:
      - group: "" # core
      - group: "admissionregistration.k8s.io"
      - group: "apiextensions.k8s.io"
      - group: "apiregistration.k8s.io"
      - group: "apps"
      - group: "authentication.k8s.io"
      - group: "authorization.k8s.io"
      - group: "autoscaling"
      - group: "batch"
      - group: "certificates.k8s.io"
      - group: "extensions"
      - group: "metrics.k8s.io"
      - group: "networking.k8s.io"
      - group: "node.k8s.io"
      - group: "policy"
      - group: "rbac.authorization.k8s.io"
      - group: "scheduling.k8s.io"
      - group: "storage.k8s.io"
    omitStages:
      - "RequestReceived"
  # Default level for known APIs
  - level: RequestResponse
    resources:
      - group: "" # core
      - group: "admissionregistration.k8s.io"
      - group: "apiextensions.k8s.io"
      - group: "apiregistration.k8s.io"
      - group: "apps"
      - group: "authentication.k8s.io"
      - group: "authorization.k8s.io"
      - group: "autoscaling"
      - group: "batch"
      - group: "certificates.k8s.io"
      - group: "extensions"
      - group: "metrics.k8s.io"
      - group: "networking.k8s.io"
      - group: "node.k8s.io"
      - group: "policy"
      - group: "rbac.authorization.k8s.io"
      - group: "scheduling.k8s.io"
      - group: "storage.k8s.io"
    omitStages:
      - "RequestReceived"
  # Default level for all other requests.
  - level: Metadata
    omitStages:
      - "RequestReceived"
```

### 3.更新 apiserver
最后，需要更新每台 apiserver 静态 pod，使第一步更改的 kubeadm-config 生效。在 control-plane 节点上执行：
```bash
kubeadm upgrade node --certificate-renewal=false
```

### 4.日志采集
最后，就是通过你熟悉的日志收集工具，将审计日志收集起来就可以了。