---
title: "Kubernetes Nginx Ingress 502"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["think"]
date: 2019-09-26T11:28:31+08:00
draft: true
---

nginx  ingress 后端实例过多，频繁reload。
导致长时间调用10s中断。
```
# In case of errors try the next upstream server before returning an error
   proxy_next_upstream                     error timeout;
   proxy_next_upstream_timeout             0;
   proxy_next_upstream_tries               3;
```
<!--more-->

The remaining content of your post.
