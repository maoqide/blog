---
title: "Kubernetes Debugs"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "debug"]
date: 2020-02-24T14:14:38+08:00
draft: true
---

Cut out summary from your post content here.

<!--more-->
```shell
E0224 06:08:40.281148       1 reflector.go:201] k8s.io/dns/pkg/dns/dns.go:192: Failed to list *v1.Service: Get https://10.254.0.1:443/api/v1/services?resourceVersion=0: dial tcp 10.254.0.1:443: connect: no route to host
I0224 06:08:40.644995       1 dns.go:219] Waiting for [endpoints services] to be initialized from apiserver...
I0224 06:08:41.145028       1 dns.go:219] Waiting for [endpoints services] to be initialized from apiserver...
I0224 06:08:41.645029       1 dns.go:219] Waiting for [endpoints services] to be initialized from apiserver...
I0224 06:08:42.145034       1 dns.go:219] Waiting for [endpoints services] to be initialized from apiserver...
```
**no route to host**    
原因：node 节点 firewalld 为关闭。    