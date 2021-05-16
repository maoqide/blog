---
title: "catch signal when kuberntes pod deleted"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "grace terminating"]
date: 2021-05-08T15:26:44+08:00
draft: true
---

为了减少 pod 更新时对服务产生影响，很多应用会做优雅下线。

<!--more-->

- [kubernetes-best-practices-terminating-with-grace](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-terminating-with-grace)    
- [pod-lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination)    
