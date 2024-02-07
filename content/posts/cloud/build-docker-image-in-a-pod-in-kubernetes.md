---
title: "Build Docker Image in a Pod in Kubernetes"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["cloud", "docker image", "kaniko"]
date: 2019-10-27T11:24:01+08:00
---

利用 [kaniko](https://github.com/GoogleContainerTools/kaniko) 在 kubernetes 集群中使用 pod 来进行镜像构建，并 push 到镜像仓库中。     
<!--more-->

## pre-request
- kubernetes cluster    
- kaniko-executor image    

## 构建
具体用法可以阅读 [kaniko](https://github.com/GoogleContainerTools/kaniko) 项目的 README 文档，项目本身支持`GCS Bucket`、`S3 Bucket`、`Local Directory`、`Git Repository`四种 buildcontext 存储方案，在实际的使用中，感觉使用内部的文件服务器更加方便，添加了对直接 http/https 下载链接的支持，https://github.com/maoqide/kaniko。    

## quick start
### build yourself a image for kaniko executor
```shell
# build yourself a image for kaniko executor
cd $GOPATH/src/github.com/GoogleContainerTools
git clone https://github.com/maoqide/kaniko
make images
```
### start a file server if using http/https for buildcontext
	kaniko's build context is very similar to the build context you would send your Docker daemon for an image build; it represents a directory containing a Dockerfile which kaniko will use to build your image. For example, a COPY command in your Dockerfile should refer to a file in the build context.    

using [minio](https://github.com/minio/minio) as file server:    
```shell
docker run -p 9000:9000 minio/minio server /data
```

### create context.tar.gz
```shell
# tar your build context including Dockerfile into context.tar.gz
tar -C <path to build context> -zcvf context.tar.gz .
```
upload to minio and generate a download url.    


### create secret on kubernetes
```shell
# registry can also be a harbor or other registry.
kubectl create secret docker-registry regcred --docker-server=<your-registry-server> --docker-username=<your-name> --docker-password=<your-pword> --docker-email=<your-email>
```

### create pod
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: kaniko
spec:
  containers:
  - name: kaniko
    env:
    - name: DOCKER_CONFIG
      value: /root/.docker/
    image: harbor.guahao-inc.com/mqtest/executor
    args: [ "--context=http://download_url/context.tar.gz",
            "--destination=maoqide/test:latest",
            "--verbosity=debug",
		]
    volumeMounts:
      - name: kaniko-secret
        mountPath: /root
      - name: context
        mountPath: /kaniko/buildcontext/
  restartPolicy: Never
  volumes:
    - name: context
      emptyDir: {}
    - name: kaniko-secret
      secret:
        secretName: regcred
        items:
          - key: .dockerconfigjson
            path: .docker/config.json
```
*env DOCKER_CONFIG is required for regidtry authorization, otherwise you would get an UNAUTHORIZED error.*    

```shell
kubectl create -f pod.yaml
```

```shell
[root@centos10 ~]$ kubectl get po
NAME                      READY     STATUS      RESTARTS   AGE
kaniko                    0/1       Completed   0          5h
```

and you can find your image pushed.    