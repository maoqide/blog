---
title: "Kubernetes Crd"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "crd"]
date: 2020-10-29T09:00:05+08:00
draft: true
---

<!--more-->
### 需求来源
随着 Kubernetes 使用的越来越多，用户自定义资源的需求也会越来越多。而 Kubernetes 提供的聚合各个子资源的功能，已经不能满足日益增长的广泛需求了。用户希望提供一种用户自定义的资源，把各个子资源全部聚合起来。但 Kubernetes 原生资源的扩展和使用比较复杂，因此诞生了用户自定义资源这么一个功能。    

- 复杂有状态服务管理(Operator)    
- 标准应用模型定义    
- 基于 Kubernetes 的框架或组件(calico/istio)    
- ...    

### 概念
#### Custom resources
**Resource**: 资源是 Kubernetes API 中的一个端点，用于存储某种类型的 API 对象的集合。例如，内置的 pods 资源包含 Pod 对象的集合。    
**Custom resource**: 自定义资源是对 Kubernetes API 的扩展，不一定在默认的 Kubernetes 中就可用。自定义资源所代表的是对特定 Kubernetes 的一种定制。    

#### Custom controllers
<!-- 举例 工业，温度控制器 -->
**controller**: 在 Kubernetes 中，controller 是一个通过 apiserver 监听集群状态，并在需要时进行或请求更改的控制循环。controller 致力于将当前状态(current state)转变为期望的状态(desired state)。    
*对比：恒温器*    
**custom controller** 能够实现用户自行编写，并且监听并解析 CRD 把集群变成用户期望的状态。    

自定义资源只是可以存储和检索结构化数据。当自定义资源与自定义控制器结合使用时，自定义资源会提供真正的**声明性 API**。    
***什么是声明式API:***    

- 首先，所谓“声明式”，指的就是我只需要提交一个定义好的 API 对象来“声明”，我所期望的状态是什么样子。    
- 其次，“声明式 API”允许有多个 API 写端，以 PATCH 的方式对 API 对象进行修改，而无需关心本地原始 YAML 文件的内容。    
- 最后，也是最重要的，有了上述两个能力，Kubernetes 项目才可以基于对 API 对象的增、删、改、查，在完全无需外界干预的情况下，完成对“实际状态”和“期望状态”的调谐（Reconcile）过程。    

*对比：声明式(What)/命令式(How)*    

### CRD 设计模式
controller 工作原理：    
![](/media/posts/cloud/kubernetes-crd/client-go-controller-interaction.jpeg)    

Reflector 使用一种叫作 ListAndWatch 的方法，来“获取”并“监听” Kubernetes 资源对象实例的变化。    
在 ListAndWatch 机制下，一旦 APIServer 端有新的实例被创建、删除或者更新，Reflector 都会收到“事件通知”。这时，该事件及它对应的 API 对象这个组合，就被称为增量（Delta），它会被放进一个 Delta FIFO Queue（即：增量先进先出队列）中。    
而另一方面，Informer 会不断地从这个 Delta FIFO Queue 里读取（Pop）增量。每拿到一个增量，Informer 就会判断这个增量里的事件类型，然后创建或者更新本地对象的缓存。这个缓存，在 Kubernetes 里一般被叫作 Store。    
比如，如果事件类型是 Added（添加对象），那么 Informer 就会通过一个叫作 Indexer 的库把这个增量里的 API 对象保存在本地缓存中，并为它创建索引。相反，如果增量的事件类型是 Deleted（删除对象），那么 Informer 就会从本地缓存中删除这个对象。    
这个同步本地缓存的工作，是 Informer 的第一个职责，也是它最重要的职责。    
而 Informer 的第二个职责，则是根据这些事件的类型，触发事先注册好的 ResourceEventHandler。这些 Handler，需要在创建控制器的时候注册给它对应的 Informer。    

workqueue 工作流程:    
![](/media/posts/cloud/kubernetes-crd/key-lifecicle-workqueue.png)    

Reconcile:    
```golang
for {
  实际状态 := 获取集群中对象X的实际状态(Current State)
  期望状态 := 获取集群中对象X的期望状态(Desired State)
  if 实际状态 == 期望状态{
    什么都不做
  } else {
    执行编排动作, 将实际状态调整为期望状态
  }
}
```

### kubebuilder
[Kubebuilder](https://github.com/kubernetes-sigs/kubebuilder) 是 CRD 构建 Kubernetes API 的框架。    
Kubebuilder 的工作流程如下：    

- 创建一个新的工程目录    
- 创建一个或多个资源 API CRD 然后将字段添加到资源    
- 在控制器中实现**协调循环**（reconcile loop），watch 额外的资源    
- 在集群中运行测试（自动安装 CRD 并自动启动控制器）    
- 更新引导集成测试测试新字段和业务逻辑    
- 使用用户提供的 Dockerfile 构建和发布容器    


#### CustomResourceDefinitions
<!-- API 定义 OpenAPI -->
CustomResourceDefinition 允许您定义自定义资源。定义CRD对象会使用您指定的名称和结构创建一个新的自定义资源。 Kubernetes API服务并处理您的自定义资源的存储。    

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  # name must match the spec fields below, and be in the form: <plural>.<group>
  name: crontabs.stable.example.com
spec:
  # group name to use for REST API: /apis/<group>/<version>
  group: stable.example.com
  # list of versions supported by this CustomResourceDefinition
  versions:
    - name: v1
      # Each version can be enabled/disabled by Served flag.
      served: true
      # One and only one version must be marked as the storage version.
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                cronSpec:
                  type: string
                image:
                  type: string
                replicas:
                  type: integer
  # either Namespaced or Cluster
  scope: Namespaced
  names:
    # plural name to be used in the URL: /apis/<group>/<version>/<plural>
    plural: crontabs
    # singular name to be used as an alias on the CLI and for display
    singular: crontab
    # kind is normally the CamelCased singular type. Your resource manifests use this.
    kind: CronTab
    # shortNames allow shorter string to match your resource on the CLI
    shortNames:
    - ct
```

### 高级功能
### Finalizers
```yaml
apiVersion: "stable.example.com/v1"
kind: CronTab
metadata:
  finalizers:
  - finalizer.stable.example.com
...
```

Finalizers 字段属于 Kubernetes GC 垃圾收集器，是一种删除拦截机制，能够让控制器实现异步的删除前（Pre-delete）回调。    
对带有 `Finalizer` 的对象的第一个删除请求会为其 `metadata.deletionTimestamp` 设置一个值，但不会真的删除对象。一旦此值被设置，finalizers 列表中的值就只能被移除。    
当 `metadata.deletionTimestamp`字段被设置时，负责监测该对象的各个控制器会通过轮询对该对象的更新请求来执行它们所要处理的所有 Finalizer。当所有 Finalizer 都被执行过，资源被删除。    
`metadata.deletionGracePeriodSeconds` 的取值控制对更新的轮询周期。    
每个控制器要负责将其 `Finalizer` 从列表中去除。    
每执行完一个就从 finalizers 中移除一个，直到 finalizers 为空，之后其宿主资源才会被真正的删除。    

### Validation
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: crontabs.stable.example.com
spec:
  group: stable.example.com
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        # openAPIV3Schema is the schema for validating custom objects.
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                cronSpec:
                  type: string
                  pattern: '^(\d+|\*)(/\d+)?(\s+(\d+|\*)(/\d+)?){4}$'
                image:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 10
  scope: Namespaced
  names:
    plural: crontabs
    singular: crontab
    kind: CronTab
    shortNames:
    - ct
```

```shell
[root@centos10 crd-demo]# kubectl apply -f cr.yaml
The CronTab "my-new-cron-object" is invalid: spec.replicas: Invalid value: 10: spec.replicas in body should be less than or equal to 10
```

### 示例演示: wedoctor-app
![](/media/posts/cloud/kubernetes-crd/wedoctorapp-controller.jpg)    



*书籍推荐*    
[Kubernetes Pattern](https://www.redhat.com/cms/managed-files/cm-oreilly-kubernetes-patterns-ebook-f19824-201910-en.pdf)
/[中文翻译版](https://www.yuque.com/serviceup/cn-kubernetes-patterns/tquvrt)    
