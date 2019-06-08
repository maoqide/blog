---
title: "将网站部署在 Kubernetes 上"
date: "2019-01-01T17:04:25+08:00"
author: "Maoqide"
tags: ["notes", "blog", "kubernetes"]
draft: false
---

将自己的博客网站发布到自己的 Kubernetes 集群上。     
<!--more--> 

## Kubernetes 环境
之前在 [阿里云主机搭建-k8s-集群](https://maoqide.live:30091/cloud/%E9%98%BF%E9%87%8C%E4%BA%91%E4%B8%BB%E6%9C%BA%E6%90%AD%E5%BB%BA-k8s-%E9%9B%86%E7%BE%A4/) 这篇文章介绍了如何在阿里云环境快速搭建一个 Kubernetes 环境，按照文章的步骤，可以快速搭建一个可用的 Kubernetes 集群。    

## 网站
同样在 [Build Blog With Hugo](https://maoqide.live:30091/notes/build-blog-with-hugo/) 这边文章中，介绍了怎么使用 hugo 快速搭建一个自己的个人博客。   

## 容器化
我的项目 [hugo-dcos](https://github.com/maoqide/hugo-docs) 包含了容器化一个 hugo 网站项目所需的一些脚本和 Dockerfile, 可以参考本项目自行容器化自己的项目。    
项目使用了[webhook](https://github.com/adnanh/webhook)接收 github 的通知，并在github上配置项目[maoqide.github.io](https://github.com/maoqide/maoqide.github.io)的 Webhooks, 当本项目有更新时，会调用 webhook 服务触发操作，拉取最新的代码。    

## 部署
本文介绍如何将自己的个人博客通过 Kubernetes 发布到公网，让大家可以访问。     
> 当然，最简单的发布方法是通过 [Github Pages](https://pages.github.com/), 直接将 hugo 生成的 publish 文件夹上传到自己 github 的命名为 your-username.github.io 的仓库下，即可以通过 https://your-username.github.io 访问到自己的网站。

### 准备
- 域名
- 云服务器

### 创建 Deployment & Service
首先创建 Deployment 和 Service。    
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mysite
spec:
  selector:
    matchLabels:
      app: site
  replicas: 1
  template:
    metadata:
      labels:
        app: site
    spec:
      containers:
      - name: mysite
        image: maoqide/site:v1.1
        env:
        - name: GITHUB_HOOK_SECRET
          value: MY_SECRET
        ports:
        - containerPort: 80
        - containerPort: 9000
        livenessProbe:
          httpGet:
          # scheme: HTTPS
            path: /
            port: 80
          initialDelaySeconds: 15
          timeoutSeconds: 1

---
kind: Service
apiVersion: v1
metadata:
  name: mysite
spec:
  selector:
    app: site
  ports:
  - name: nginx
    protocol: TCP
    port: 80
    targetPort: 80
  - name: webhook
    protocol: TCP
    port: 9000
    targetPort: 9000


```

### 创建 ingress-controller
为了能够从外部访问，还需要创建 Ingress。     
这里使用nginx ingress，首先要创建 nginx-ingress-controller。    
```yaml
kind: ConfigMap
apiVersion: v1
metadata:
  name: nginx-configuration
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx

---
kind: ConfigMap
apiVersion: v1
metadata:
  name: tcp-services
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx

---
kind: ConfigMap
apiVersion: v1
metadata:
  name: udp-services
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: nginx-ingress-serviceaccount
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx

---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRole
metadata:
  name: nginx-ingress-clusterrole
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
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
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: Role
metadata:
  name: nginx-ingress-role
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
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
    resourceNames:
      # Defaults to "<election-id>-<ingress-class>"
      # Here: "<ingress-controller-leader>-<nginx>"
      # This has to be adapted if you change either parameter
      # when launching the nginx-ingress-controller.
      - "ingress-controller-leader-nginx"
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

---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: RoleBinding
metadata:
  name: nginx-ingress-role-nisa-binding
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: nginx-ingress-role
subjects:
  - kind: ServiceAccount
    name: nginx-ingress-serviceaccount

---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: nginx-ingress-clusterrole-nisa-binding
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: nginx-ingress-clusterrole
subjects:
  - kind: ServiceAccount
    name: nginx-ingress-serviceaccount
    namespace: default

---

apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: nginx-ingress-controller
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: ingress-nginx
      app.kubernetes.io/part-of: ingress-nginx
  template:
    metadata:
      labels:
        app.kubernetes.io/name: ingress-nginx
        app.kubernetes.io/part-of: ingress-nginx
      annotations:
        prometheus.io/port: "10254"
        prometheus.io/scrape: "true"
    spec:
      serviceAccountName: nginx-ingress-serviceaccount
      containers:
        - name: nginx-ingress-controller
          image: quay.io/kubernetes-ingress-controller/nginx-ingress-controller:0.21.0
          args:
            - /nginx-ingress-controller
            - --configmap=$(POD_NAMESPACE)/nginx-configuration
            - --tcp-services-configmap=$(POD_NAMESPACE)/tcp-services
            - --udp-services-configmap=$(POD_NAMESPACE)/udp-services
            - --publish-service=$(POD_NAMESPACE)/ingress-nginx
            - --annotations-prefix=nginx.ingress.kubernetes.io
          securityContext:
            capabilities:
              drop:
                - ALL
              add:
                - NET_BIND_SERVICE
            # www-data -> 33
            runAsUser: 33
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          ports:
            - name: http
              containerPort: 80
            - name: https
              containerPort: 443
          livenessProbe:
            failureThreshold: 3
            httpGet:
              path: /healthz
              port: 10254
              scheme: HTTP
            initialDelaySeconds: 10
            periodSeconds: 10
            successThreshold: 1
            timeoutSeconds: 1
          readinessProbe:
            failureThreshold: 3
            httpGet:
              path: /healthz
              port: 10254
              scheme: HTTP
            periodSeconds: 10
            successThreshold: 1
            timeoutSeconds: 1

---
```
以上 yaml 创建了一个 nginx-ingress-controller 的 Deployment，并赋给 Deployment 下的 Pod 对 Ingress 等集群内资源的 API 访问权限。    

接着要为 nginx-ingress-controller 创建 Node port 类型的 Service，让我们可以通过云服务器的公网地址访问到 ingress:    
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
spec:
  type: NodePort
  ports:
    - name: http
      port: 80
      targetPort: 80
      protocol: TCP
    - name: https
      port: 443
      targetPort: 443
      protocol: TCP
  selector:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx

---
```

### 创建 Ingress
创建 Ingress 策略。    
```yaml
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: site-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
spec:
  rules:
  - http:
      paths:
      - path: /_hook
        backend:
          serviceName: mysite
          servicePort: 9000
      - path: /
        backend:
          serviceName: mysite
          servicePort: 80

```

### 配置域名
上述步骤完成，已经可以通过云服务器公网IP= https://IP:ingress_svc-port 访问网站了。    
为了访问方便，还可以给站点配置一个域名，直接在阿里云购买一个域名，然后通过绑定一个 A 类型的域名解析，解析到阿里云公网IP，就可以通过域名加端口访问了。    
如果不想访问的时候加上端口，还需要再配置一个 隐性URL 的域名解析（需要先将域名备案）。    

### 附件
以下是上面用到的 yaml 文件：    
- [site-deployment](/media/posts/notes/publish-your-site-on-k8s/mysite.yaml)    
- [nginx-ingress-controller](/media/posts/notes/publish-your-site-on-k8s/nginx_ingress.yaml)    
- [ingress-svc](/media/posts/notes/publish-your-site-on-k8s/ingress_svc.yaml)    
- [ingress](/media/posts/notes/publish-your-site-on-k8s/ingress.yaml)
