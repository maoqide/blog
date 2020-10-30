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

## 镜像构建
### build context/dockerignore
执行`docker build`命令时，docker client 会将当前目录下的文件打包并发送给 docker daemon，这就是 build context。    
这个过程会有一定耗时，尤其是 build context 很大的时候，这时候可以用`.dockerignore`文件建不需要的大文件忽略，用法和 git 的`.gitignore`基本一致。    

下面执行`docker build`命令的目录, 使用`.dockerignore`文件忽略了文件 test1    
```
[root@centos11 images]# ls -la
total 102408
drwxr-xr-x. 2 root root        70 Aug 18 22:25 .
drwxr-xr-x. 3 root root        20 Aug 18 22:04 ..
-rw-r--r--. 1 root root         6 Aug 18 22:11 .dockerignore
-rw-r--r--. 1 root root        52 Aug 18 22:19 Dockerfile
-rw-r--r--. 1 root root         0 Aug 18 22:08 test
-rw-r--r--. 1 root root 104857600 Aug 18 22:11 test1
```

下面是 docker daemon 进行镜像构建的临时目录    
```
[root@centos11 docker-builder226382581]# pwd
/var/lib/docker/tmp/docker-builder226382581
[root@centos11 docker-builder226382581]# ll
total 4
-rw-r--r--. 1 root root 52 Aug 18 22:19 Dockerfile
-rw-r--r--. 1 root root  0 Aug 18 22:08 test
```

下面是使用`.dockerignore`和不使用时的区别    
```
[root@centos11 images]# time docker build --no-cache -t test .
Sending build context to Docker daemon  3.584kB
Step 1/2 : FROM alpine
 ---> a24bb4013296
Step 2/2 : ADD ./test /root
 ---> e31b37d08034
Successfully built e31b37d08034
Successfully tagged test:latest

real	0m0.296s
user	0m0.038s
sys	0m0.027s
```
```
[root@centos11 images]# time docker build --no-cache -t test .
Sending build context to Docker daemon  104.9MB
Step 1/2 : FROM alpine
 ---> a24bb4013296
Step 2/2 : ADD ./test /root
 ---> 1be2b417545d
Successfully built 1be2b417545d
Successfully tagged test:latest

real	0m2.535s
user	0m0.069s
sys	0m0.086s
```

### 最小镜像
- 多阶段构建    
- 清理临时文件    
    
https://docs.docker.com/develop/develop-images/dockerfile_best-practices/    

#### 选择体积较小的基础镜像
基础镜像大小差异:    
```
[root@centos11 ~]# docker images alpine
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
alpine              latest              a24bb4013296        2 months ago        5.57MB
[root@centos11 ~]# docker images centos
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
centos              7                   7e6257c9f8d8        13 days ago         203MB
```
#### 清理临时文件
`RUN`指令产生的临时文件需要在当前层清理    
```Dockerfile
FROM alpine
RUN dd if=/dev/zero of=temp_file bs=1M count=100
RUN rm -f temp_file
```
```
[root@centos11 images]# docker images test1
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
test1               latest              e0d48f43985e        13 seconds ago      110MB
```
```Dockerfile
FROM alpine
RUN dd if=/dev/zero of=temp_file bs=1M count=100 &&\
	rm -f temp_file
```
```
[root@centos11 images]# docker images test2
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
test2               latest              c31fabd926aa        7 seconds ago       5.57MB
```

#### 最小层数
`RUN`, `COPY`, `ADD`指令会增加镜像的层数    

```Dockerfile
RUN apt-get update && apt-get install -y \
    aufs-tools \
    automake \
    build-essential \
    curl \
    dpkg-sig \
    libcap-dev \
    libsqlite3-dev \
    mercurial \
    reprepro \
    ruby1.9.1 \
    ruby1.9.1-dev \
    s3cmd=1.1.* \
 && rm -rf /var/lib/apt/lists/*
```

#### 利用缓存
使用镜像缓存时，Dockerfile 的 ADD 和 COPY 指令，会同时对比指令字符串和对应的文件内容和缓存是否一致，其他指令只会比较指令字符串是否一致。    

## 容器/应用
- 单进程    
- 可观测    
- 无状态    
- 横向扩展    
- 不可变    

## Pod
### Init Container
Init 容器的概览，它是一种特殊容器，在 Pod 内的应用容器启动之前运行，可以包括一些应用镜像中不存在的实用工具和安装脚本。    
### Sidecar
Sidecar 容器在不改变原有容器的情况下，扩展和增强了它的功能。这种模式是基本的容器模式之一，它允许单一用途的容器紧密合作。    

## CRD/Operator
Operator 是一个特定的应用程序的控制器，通过扩展 Kubernetes API 以代表 Kubernetes 用户创建，配置和管理复杂有状态应用程序的实例。    
Operator 是一种软件，它结合了特定的领域知识并通过 CRD(Custom Resource Definition) 机制扩展了Kubernetes API，使用户像管理 Kubernetes 的内置资源一样创建，配置和管理应用程序。Operator 管理整个集群中的多个实例，而不仅仅管理应用程序的单个实例。    

### Declarative APIs
kubernetes 基于声明式 API，
代表目标状态    
基于事件触发    

### 自定义资源

A resource is an endpoint in the Kubernetes API that stores a collection of API objects of a certain kind; for example, the built-in pods resource contains a collection of Pod objects.

A custom resource is an extension of the Kubernetes API that is not necessarily available in a default Kubernetes installation. It represents a customization of a particular Kubernetes installation. However, many core Kubernetes functions are now built using custom resources, making Kubernetes more modular.

### 自定义控制器

![](/media/posts/cloud/sample-controller/client-go-controller-interaction.jpeg)    
