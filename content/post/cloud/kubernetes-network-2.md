---
title: "Kubernetes Network 2"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["think"]
date: 2020-07-23T09:01:17+08:00
draft: true
---

Cut out summary from your post content here.

<!--more-->

## service
- ClusterIP    
- NodePort    
- LoadBalance    

- Headless     
- externalName    

externalTrafficPolicy    

## ingress
service 只负责 L4 转发，做不到高级的 L7 转发功能，如基于 HTTP header、cookie、URL 的转发。    

## DNS

## Network Policy

## 网络故障定位

### IP forward
sysctl net.ipv4.ip_forward    
### bridge netfilter
sysctl net.bridge.bridge-nf-call-iptables    

### pod-cidr

### hairpin

### SNAT 丢包
