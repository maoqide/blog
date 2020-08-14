---
title: "Kubernetes Pattern"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "crd", "design"]
date: 2020-08-10T09:18:18+08:00
draft: true
---

kubernetes 实践中的一些通用设计模式和最佳实践。    
<!--more-->

## 镜像/容器
- 单进程    
- 无状态    
- 可观测    
- 横向扩展    
- 镜像不可变    
  
## Pod
- Init Container    
- Sidecar    

## CRD/Operator
An Operator is software that encodes this domain knowledge and extends the Kubernetes API through the third party resources mechanism, enabling users to create, configure, and manage applications. Like Kubernetes's built-in resources, an Operator doesn't manage just a single instance of the application, but multiple instances across the cluster.

### Declarative APIs
声明式 API    
代表目标状态    
基于事件触发    

### 自定义资源

A resource is an endpoint in the Kubernetes API that stores a collection of API objects of a certain kind; for example, the built-in pods resource contains a collection of Pod objects.

A custom resource is an extension of the Kubernetes API that is not necessarily available in a default Kubernetes installation. It represents a customization of a particular Kubernetes installation. However, many core Kubernetes functions are now built using custom resources, making Kubernetes more modular.

### 自定义控制器

![](/media/posts/cloud/sample-controller/client-go-controller-interaction.jpeg)    
