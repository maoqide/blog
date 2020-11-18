---
title: "Kubernetes Pattern"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "crd", "design"]
date: 2020-08-10T09:18:18+08:00
draft: true
---

应用容器化和 K8S 部署最佳实践    
<!--more-->

## 镜像构建
### 基本操作
```shell
docker build -f Dockerfile -t image_name:v1 .
```
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

### 最佳实践
- 尽可能小的基础镜像    
- 清理临时文件    
- 最小层数    
- 利用缓存        
    
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
小的基础镜像上传和下载速度更快，由于包含的软件更少，也能够降低一定的安全漏洞风险。    

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
另一种方式是使用多阶段构建（在 Docker 17.05 中引入）。多阶段构建可以在第一个“构建”容器中构建应用，并将结果用于其他容器，同时使用同一 Dockerfile。    
```Dockerfile
FROM golang:1.10 as builder

WORKDIR /tmp/go
COPY hello.go ./
RUN CGO_ENABLED=0 go build -a -ldflags '-s' -o hello

FROM scratch
CMD [ "/hello" ]
COPY --from=builder /tmp/go/hello /hello
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
Docker 镜像缓存可以大幅度加速容器镜像的构建。镜像是逐层构建的，在 Dockerfile 中，每条指令都会在生成的镜像中创建一层。    
使用镜像缓存时，Dockerfile 的 ADD 和 COPY 指令，会同时对比指令字符串和对应的文件内容和缓存是否一致，其他指令只会比较指令字符串是否一致，并且仅当所有先前的构建步骤都使用 Docker 的构建缓存时，Docker 才会使用缓存。要充分利用 Docker 构建缓存，必须将经常更改的构建步骤置于 Dockerfile 底部。因此，添加代码的操作应该尽可能放在 Dockerfile 下层。    

## 容器/应用
- 单进程    
- 可观测    
- 无状态    
- 不可变    
- 横向扩展    

### 单进程
由于容器与其托管的应用具有相同的生命周期，因此每个容器应仅包含一个应用。当容器启动时，应用也应该启动，当应用停止时，容器也应该停止。    
*此处“应用”被视为具有唯一父进程且可能具有多个子进程的单个软件。*    
如果一个容器中具有多个应用，则这些应用可能具有不同的生命周期或处于不同状态。例如，到最后可能出现容器在运行但其某个核心组件崩溃或无响应的情况。如果不进行额外的运行状况检查，则整个容器管理系统（Docker 或 Kubernetes）将无法判断该容器是否运行正常。    

### 可观测
#### 活跃性探测(Liveness)
Liveness 探测的推荐方法是让应用公开 /health HTTP 端点。在此端点上收到请求后，如果认为运行状况良好，应用应发送“200 OK”响应。在 Kubernetes 中，运行状况良好意味着容器不需要终止或重启。运行状况良好的条件因应用而异，但通常意味着以下情况：    
- 该应用正在运行    
- 其主要依赖性得到满足（例如，它可以访问其数据库）    

#### 就绪性探测(Readiness)
Readiness 探测的推荐方法是让应用公开 /ready HTTP 端点。当应用在此端点上收到请求时，如果其已准备好接收流量，则应发送“200 OK”响应。准备好接收流量意味着以下情况：    
- 该应用运行状况良好    
- 任何潜在的初始化步骤均已完成    
- 发送到应用的任何有效请求都不会导致错误    
Kubernetes 使用就绪性探测来编排应用的部署。如果更新应用，Kubernetes 将对属于该应用 Deployment 的 pod 进行滚动更新。 默认更新政策是一次更新一个 pod，即 Kubernetes 会在更新下一个 pod 之前等待新 pod 准备就绪（由就绪性探测指明）。    
*在许多应用中，/health 和 /ready 端点合并为一个 /health 端点，因为实际上它们的运行状况和就绪状态之间并没有差别。*    

#### 监控指标
指标 HTTP 端点的实现方式和上面两种类似，它通常在 /metrics URI 上公开应用的内部指标。 响应如下：    
```
http_requests_total{method="post",code="200"} 1027
http_requests_total{method="post",code="400"}    3
http_requests_total{method="get",code="200"} 10892
http_requests_total{method="get",code="400"}    97
```
通过 Prometheus 客户端 SDK 可以轻松生成如上格式的 HTTP 端点。    


### 无状态
无状态意味着任何状态数据（任何类型的持久性数据）均存储在容器之外。这种外部存储可以采取多种形式：    
- 如需存储文件，建议使用对象存储。    
- 如需存储用户会话等信息，建议使用外部低延时键值存储，例如 Redis 或 Memcached。    
- 如果需要块级存储（例如对于数据库），则可以使用挂载到容器的外部磁盘。    
通过以上方式，你可以从容器本身移除数据，这意味着可以随时彻底停止和销毁容器，而不必担心数据丢失。如果创建了一个新容器来替换旧容器，只需将新容器连接到同一数据存储区或绑定到同一磁盘即可。    

### 不变性
不可变意味着容器在其生命周期内不会被修改，即没有更新、没有补丁程序，也没有配置更改。如果必须更新应用代码或应用补丁程序，则必须构建新镜像并重新部署。    
不变性使容器部署更安全、更可重复，可在不同环境中使用同一镜像。如果需要回滚，只需重新部署旧镜像即可。    
如需在不同环境中使用同一镜像，我们建议您外部化容器配置（监听端口、运行时参数等）在 Kubernetes 中，可以使用 Secrets 或 ConfigMaps 将容器中的配置作为环境变量或文件注入。    
如果需要更新配置，请使用更新后的配置部署一个新容器（基于同一镜像）。    

