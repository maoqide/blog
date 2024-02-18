---
title: "Deploy Mysql on Kubernetes"
date: 2019-05-16T14:06:37+08:00
draft: false
author: "Maoqide"
tags: ["cloud", "kubernetes", "kubernetes-operator", "mysql-operator"]
---

本文通过 [mysql-operator](https://github.com/oracle/mysql-operator) 在kubernetes集群部署高可用的mysql statefulset。    
<!--more--> 

## 环境准备
本文使用的开源 operator 项目 [mysql-operator](https://github.com/oracle/mysql-operator) 配死只支持 mysql 8.0.11 以上的版本，改了下代码，支持 5.7.0 以上版本，[项目地址](https://github.com/maoqide/mysql-operator)，本文部署的是 mysql-5.7.26，使用的 dockerhub 上的镜像 mysql/mysql-server:5.7.26。

## 代码编译
git clone 下载该项目，进入到代码目录，执行`sh hack/build.sh`，编译代码得到二进制文件 mysql-agent 和 mysql-operator，将二进制文件放入 `bin/linux_amd64`，执行`docker build -f docker/mysql-agent/Dockerfile -t $IMAGE_NAME_AGENT .`，`docker build -f docker/mysql-operator/Dockerfile -t $IMAGE_NAME_OPERATOR .`构建镜像，mysql-operator 生成的镜像为 operator 的镜像，mysql-agent 生成的是镜像，在创建mysql服务时，作为sidecar和mysql-server容器起在同一个pod中。

## 部署 operator
先根据 [文档](https://github.com/maoqide/mysql-operator/blob/master/docs/tutorial.md) 部署 mysql-operator 的 Deployment，文档中是使用 helm 安装，不希望安装 helm 和 tiller 的话，可以只安装一个 helm 客户端，进入到代码目录，再执行`helm template --name mysql-operator mysql-operator`生成部署所需要的yaml文件，然后直接执行`kubectl apply -f mysql-operator.yaml`创建 operator。这个yaml创建了operator所需的CRD类型，operator 的 Deployment 和 operator 所需的 RBAC 权限等。    
```shell
# change directory into mysql-operator
cd mysql-operator
# generate mysql-operator.yaml
helm template --name mysql-operator mysql-operator > mysql-operator.yaml
# deploy on kubernetes
kubectl apply -f mysql-operator.yaml
# deployed.
[root@localhost]$ kubectl get deploy -n mysql-operator
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
mysql-operator   1/1     1            1           2d5h
```

## 创建 mysql 集群
本文创建的集群为3节点的 mysql，一个节点为 master，二个为 slave，master节点可读写，slave节点为只读，使用 kubernetes Local PV 作持久化存储。    
首先，为每个节点创建一个PV，Local PV 需要定义`nodeAffinity`，约束创建的节点。    
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mypv0
spec:
  capacity:
    storage: 1Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: mysql-storage
  local:
    path: /data/mysql-data
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - 192.168.0.1

---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mypv1
spec:
  capacity:
    storage: 1Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: mysql-storage
  local:
    path: /data/mysql-data
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - 192.168.0.2

---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mypv2
spec:
  capacity:
    storage: 1Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Delete
  storageClassName: mysql-storage
  local:
    path: /data/mysql-data
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - 192.168.0.3
```

```shell
# create pv
kubectl create -f pv.yaml
# get presistence volume
[root@localhost]$ kubectl get pv
mypv-0               1Gi        RWO            Delete           Available                                                                     mysql-storage               4s
mypv-1               1Gi        RWO            Delete           Available                                                                     mysql-storage               4s
mypv-2               1Gi        RWO            Delete           Available                                                                     mysql-storage               4s
```

接着，需要在创建 mysql 的 namespace 下，为要创建的 mysql 创建对应的 RBAC 权限。    
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mysql-agent
  namespace: mysql2
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1beta1
metadata:
  name: mysql-agent
  namespace: mysql2
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: mysql-agent
subjects:
- kind: ServiceAccount
  name: mysql-agent
  namespace: mysql2
```
如果需要自定义 mysql 的密码，需要为其创建一个 secret，密码需要使用base64加密。linux 下执行 `echo -n 'password' | base64` 为密码加密。    
```yaml
apiVersion: v1
data:
  password: cm9vdA==
kind: Secret
metadata:
  labels:
    v1alpha1.mysql.oracle.com/cluster: mysql
  name: mysql-pv-root-password
  namespace: mysql2
```
```shell
kubectl apply -f rbac.yaml
kubectl apply -f secret.yaml
```
在创建 operator 的时候，已经创建了如下的crd类型，部署mysql集群所需创建的就是 mysqlclusters 类型的资源。        
```shell
[root@localhost]$ kubectl get crd  | grep mysql
mysqlbackups.mysql.oracle.com                2019-05-14T02:51:11Z
mysqlbackupschedules.mysql.oracle.com        2019-05-14T02:51:11Z
mysqlclusters.mysql.oracle.com               2019-05-14T02:51:11Z
mysqlrestores.mysql.oracle.com               2019-05-14T02:51:11Z
```
接下来开始创建 operator 自定义资源类型(CRD)的实例 mysqlclusters。     
```yaml
apiVersion: mysql.oracle.com/v1alpha1
kind: Cluster
metadata:
  name: mysql
  namespace: mysql2
spec:  
  # 和mysql-server镜像版本的tag一直
  version: 5.7.26
  repository: 20.26.28.56/dcos/mysql-server
  # 节点数量
  members: 3
  # 指定 mysql 密码，和之前创建的secret名称一致
  rootPasswordSecret:
    name: mysql-pv-root-password
  resources:
    agent:
      limits:
        cpu: 500m
        memory: 200Mi
      requests:
        cpu: 300m
        memory: 100Mi
    server:
      limits:
        cpu: 1000m
        memory: 1000Mi
      requests:
        cpu: 500m
        memory: 500Mi
  volumeClaimTemplate:
    metadata:
      name: mysql-pv
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "mysql-storage"
      resources:
        requests:
          storage: 1Gi
```
```shell
kubectl apply -f mysql.yaml
```
执行后，会看到 kubernetes 在该 namespace 下开始拉起 mysql 的 statefulset，并会创建一个 headless service。    
```shell
[root@localhost]$ kubectl get all -n mysql2
NAME                                                      READY   STATUS    RESTARTS   AGE
pod/mysql-0                                               2/2     Running   0          8h
pod/mysql-1                                               2/2     Running   0          8h
pod/mysql-2                                               2/2     Running   0          8h


NAME              TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
service/mysql     ClusterIP   None            <none>        3306/TCP   21h


NAME                     READY   AGE
statefulset.apps/mysql   1/1     21h
```
此时执行`hack/cluster-status.sh`脚本，会得到如下集群信息：    
```json
{
    "clusterName": "Cluster", 
    "defaultReplicaSet": {
        "name": "default", 
        "primary": "mysql-0.mysql:3306", 
        "ssl": "DISABLED", 
        "status": "OK_NO_TOLERANCE", 
        "statusText": "Cluster is NOT tolerant to any failures. 2 members are not active", 
        "topology": {
            "mysql-0.mysql:3306": {
                "address": "mysql-0.mysql:3306", 
                "mode": "R/W", 
                "readReplicas": {}, 
                "role": "HA", 
                "status": "ONLINE"
            }, 
            "mysql-1.mysql:3306": {
                "address": "mysql-1.mysql:3306", 
                "mode": "n/a", 
                "readReplicas": {}, 
                "role": "HA", 
                "status": "ONLINE"
            }, 
            "mysql-2.mysql:3306": {
                "address": "mysql-2.mysql:3306", 
                "mode": "n/a", 
                "readReplicas": {}, 
                "role": "HA", 
                "status": "ONLINE"
            }
        }, 
        "topologyMode": "Single-Primary"
    }, 
    "groupInformationSourceMember": "mysql-0.mysql:3306"
}
```
通过DNS地址 `mysql-0.mysql.mysql2.svc.cluster.local:3306` 可以连接到数据库进行读写操作。此时一个多节点的mysql集群已经部署完成，但是，集群外部的服务还无法访问数据库。     

## 通过 haproxy-ingress 允许外部访问
首先，headless service只能通过集群内 DNS 访问服务，要外部访问，还需要另外创建一个 Service。为了让外部可以访问到 mysql-0 的服务，我们为 mysql-0 创建一个ClusterIP 类型的服务。    
```yaml
kind: Service
apiVersion: v1
metadata:
  name: mysql-0
  namespace: mysql2
spec:
  selector:
    # 通过 selector 将 pod 约束到 mysql-0
   statefulset.kubernetes.io/pod-name: mysql-0
  ports:
    - protocol: TCP
      port: 3306
      targetPort: 3306
```

接着，需要创建一个ingress-controller，本文选用的是 [haproxy-ingress](https://github.com/jcmoraisjr/haproxy-ingress)。    
由于 mysql 服务通过 TCP 协议通信，kubernetes ingress 默认只支持 http 和 https，haproxy-ingress 提供了通过 configmap 的方法，配置 TCP 服务的端口，需要先创建一个 configmap，configmap的data中，key为HAProxy监听的端口，value 为需要转发的 service 的服务和端口。    
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mysql-tcp
  namespace: mysql2
data:
  "3306": "mysql2/mysql-0:3306"
```
```shell
kubectl apply -f mysql-0.yaml
kubectl apply -f tcp-svc.yaml
```
接下来创建 ingress-controller，    
```yaml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  labels:
    run: haproxy-ingress
  name: haproxy-ingress-192.168.0.1-30080
  namespace: mysql2
spec:
  replicas: 1
  selector:
    matchLabels:
      run: haproxy-ingress
  strategy:
    type: RollingUpdate
  template:
    metadata:
      labels:
        run: haproxy-ingress
    spec:
      tolerations:
      - key: app 
        operator: Equal 
        value: haproxy
        effect: NoSchedule
      serviceAccount: ingress-controller      
      nodeSelector:
        kubernetes.io/hostname: 192.168.0.1
      containers:
      - args:
        - --tcp-services-configmap=$(POD_NAMESPACE)/mysql-tcp
        - --default-backend-service=$(POD_NAMESPACE)/mysql
        - --default-ssl-certificate=$(POD_NAMESPACE)/tls-secret
        - --ingress-class=ha-mysql
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              apiVersion: v1
              fieldPath: metadata.namespace
        image: jcmoraisjr/haproxy-ingress
        name: haproxy-ingress
        ports:
          # 和 configmap 中定义的端口对应
        - containerPort: 3306
          hostPort: 3306
          name: http
          protocol: TCP
        - containerPort: 443
          name: https
          protocol: TCP
        - containerPort: 1936
          hostPort: 30081
          name: stat
          protocol: TCP
```
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ingress-controller

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ingress-controller
rules:
  - apiGroups:
      - ""
    resources:
      - configmaps
      - pods
      - secrets
      - namespaces
    verbs:
      - get
  - apiGroups:
      - ""
    resources:
      - configmaps
    verbs:
      - get
      - update
  - apiGroups:
      - ""
    resources:
      - configmaps
    verbs:
      - create
  - apiGroups:
      - ""
    resources:
      - endpoints
    verbs:
      - get
      - create
      - update

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ingress-controller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ingress-controller
subjects:
  - kind: ServiceAccount
    name: ingress-controller
  - apiGroup: rbac.authorization.k8s.io
    kind: User
    name: ingress-controller

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: ingress-controller
rules:
  - apiGroups:
      - ""
    resources:
      - configmaps
      - endpoints
      - nodes
      - pods
      - secrets
    verbs:
      - list
      - watch
  - apiGroups:
      - ""
    resources:
      - nodes
    verbs:
      - get
  - apiGroups:
      - ""
    resources:
      - services
    verbs:
      - get
      - list
      - watch
  - apiGroups:
      - "extensions"
    resources:
      - ingresses
    verbs:
      - get
      - list
      - watch
  - apiGroups:
      - ""
    resources:
      - events
    verbs:
      - create
      - patch
  - apiGroups:
      - "extensions"
    resources:
      - ingresses/status
    verbs:
      - update

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: ingress-controller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: ingress-controller
subjects:
  - kind: ServiceAccount
    name: ingress-controller
    namespace: mysql2
  - apiGroup: rbac.authorization.k8s.io
    kind: User
    name: ingress-controller
```
```shell
kubectl apply -f ingress-controller.yaml
kubectl apply -f ingress-rbac.yaml -n mysql2
```

最后创建 ingress 规则：    
```yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  annotations:
    ingress.kubernetes.io/ssl-redirect: "false"
    kubernetes.io/ingress.class: ha-mysql
  name: ha-mysql
spec:
  rules:
  - http:
      paths:
      - backend:
          serviceName: mysql-0
          servicePort: 3306
        path: /
```

此时可以通过 haproxy 的 IP + 映射端口访问到 mysql 集群。    

## 附件
以下是上面用到的 yaml 文件：    

- [rbac.yaml](/media/posts/cloud/deploy-mysql-on-kubernetes/rbac.yaml)    
- [mysql.yaml](/media/posts/cloud/deploy-mysql-on-kubernetes/mysql.yaml)    
- [secret.yaml](/media/posts/cloud/deploy-mysql-on-kubernetes/secret.yaml)    
- [pv.yaml](/media/posts/cloud/deploy-mysql-on-kubernetes/pv.yaml)    
- [mysql-0-svc.yaml](/media/posts/cloud/deploy-mysql-on-kubernetes/mysql-0-svc.yaml)    
- [tcp-svc.yaml](/media/posts/cloud/deploy-mysql-on-kubernetes/tcp-svc.yaml)    
- [ingress-controller.yaml](/media/posts/cloud/deploy-mysql-on-kubernetes/ingress-controller.yaml)    
- [ingress-rbac.yaml](/media/posts/cloud/deploy-mysql-on-kubernetes/ingress-rbac.yaml)    
- [ingress.yaml](/media/posts/cloud/deploy-mysql-on-kubernetes/ingress.yaml)    
