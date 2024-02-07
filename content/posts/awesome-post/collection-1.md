---
title: "Awesome Post Collection 1"
date: 2018-12-03T21:38:12+08:00
author: "Maoqide"
tags: ["awesome", "mesos", "kubernetes"]
draft: false
---

- Mesos 的资源分配。    
- Kubernetes调度详解。    
- Istio 调用链埋点/tracing。    
- kubernetes informer 解析。    
<!--more-->



1. Mesos 的资源分配，解释 mesos 的二级调度和资源邀约机制，并详细介绍了保证资源分配公平的DRF算法（主导资源公平算法 Dominant Resource Fairness）。    
   [https://www.infoq.cn/article/analyse-mesos-part-04](https://www.infoq.cn/article/analyse-mesos-part-04)    
   [备用链接](https://www.evernote.com/shard/s499/sh/95931a50-240d-4cc7-b36f-2772ea2768c3/be811e866f8889c89ce3a3d6068eefd1)

2. Kubernetes调度详解。    
   [http://dockone.io/article/2885](http://dockone.io/article/2885)    
   [备用链接](https://www.evernote.com/shard/s499/u/0/sh/957a3a11-392c-4926-9095-86836c1e5a7e/432392ceb4a9fd2edc29d2fb9979844f)    
   [https://cizixs.com/2017/07/19/kubernetes-scheduler-source-code-analysis/](https://cizixs.com/2017/07/19/kubernetes-scheduler-source-code-analysis/)    
   [备用链接](https://www.evernote.com/shard/s499/u/0/sh/a57220f3-0c6b-4dde-939d-19543406068d/f2e867a6cf257d1b0062b6364996c738)    

3. Istio 调用链埋点/tracing: 使用 istio 做调用链跟踪依旧需要修改一定业务代码，微服务间请求时需要配合在请求头上传递 sidecar 生成的 Trace 相关信息，才能将调用关联到同一个 trace 上，否则每次请求都会形成新的割裂的 Trace 信息。    
   [https://www.infoq.cn/article/pqy*PFPhox9OQQ9iCRTt](https://www.infoq.cn/article/pqy*PFPhox9OQQ9iCRTt)    
   [备用链接](https://www.evernote.com/shard/s499/u/0/sh/7c3489c5-b2ad-4e6d-8f6f-0013c8a5b06f/19b490c8227798d709c766c174ed686c)

4. kubernetes informer 解析。    
   [https://blog.csdn.net/weixin_42663840/article/details/81699303](https://blog.csdn.net/weixin_42663840/article/details/81699303)    
