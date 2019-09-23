---
title: "Kubernetes Watch"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["think"]
date: 2019-09-23T13:50:30+08:00
draft: true
---

现象：通过 client-go 方法调用 apiserver watch deployment 资源，三台 apiserver 通过 nginx 做负载均衡，直接通过ip访问可以实时接收到资源变化的event，通过 nginx 只会在设置的 watch timeout 事件到了之后，将这段时间内的事件，一起返回，导致出现问题。
原因和解决：nginx gzip 参数导致，注释掉后正常。
原理：？
<!--more-->

The remaining content of your post.
