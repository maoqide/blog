---
title: "Build Fileserver Using Nginx on K8s"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["practice", "fileserver"]
date: 2021-05-27T13:52:43+08:00
draft: false
---

使用 nginx 镜像在 k8s 中搭建一个简单的文件服务器。    
<!--more-->

## 镜像
在 dockerhub 的 nginx 镜像基础上，安装 openssh-client 客户端，并生成公私钥，主要是为了方便直接 scp 想要放到文件服务器上的文件吗，若想免密，可将镜像中生成的公钥拷贝到对应主机的 `~/.ssh/authorized_keys` 目录。个人认为 scp 更加方便，当然，也可以使用 nginx 的 upload 模块 [nginx-upload-module](https://www.nginx.com/resources/wiki/modules/upload/)，这样可以直接页面上传。    
```Dockerfile
FROM nginx:1.15
RUN apt-get update -y &&\
    apt-get install openssh-client -y &&\
    apt-get clean all &&\
    ssh-keygen -t rsa  -N '' -f ~/.ssh/id_rsa -q
```
`docker build -t maoqide/fileserver:nginx-1.15`    

## k8s 部署
创建 PVC，前提是先创建好名为 ceph-rbd 的 StorageClass。    
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fileserver-data
  namespace: kube-public
spec:
  storageClassName: ceph-rbd
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
```

创建 ConfigMap，`kubectl -nkube-public create configmap file-server-conf --from-file nginx.conf -oyaml --dry-run | kubectl apply -f -`，通过如下配置文件创建 ConfigMap。若有修改都可通过此命令进行 apply。下面的配置可将 nginx 作为文件下载服务器使用。    
```
user root;
worker_processes 1;
events {
  worker_connections 1024;
}
http {
  server {
    listen 80;
    server_name your.domain.com;
    root /usr/share/nginx/files;
    location / {
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }
  }
}
```

创建 Deployment，volume 挂载上面创建好的 ConfigMap 和 PVC。PVC 指定了 StorageClass，会自动创建和绑定 PV，PV 挂载到上面 nginx.conf 中指定的文件存储目录。ConfigMap 挂载使用 subPath，仅覆盖 nginx.conf 一个文件，否则挂载会覆盖 /etc/nginx/ 整个目录。     
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fileserver
  namespace: kube-public
  labels:
    app: fileserver
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fileserver
  template:
    metadata:
      labels:
        app: fileserver
    spec:
      containers:
      - name: nginx
        image: fileserver:nginx-1.15
        volumeMounts:
          - name: conf
            mountPath: /etc/nginx/nginx.conf
            subPath: nginx.conf
          - name: data
            mountPath: /usr/share/nginx/files
        ports:
        - containerPort: 80
        readinessProbe:
          tcpSocket:
            port: 80
      volumes:
        - name: conf
          configMap:
            name: file-server-conf
            items:
            - key: nginx.conf
              path: nginx.conf
        - name: data
          persistentVolumeClaim:
            claimName: fileserver-data
```

创建 Service，可创建 NodePort 类型用以外部访问。    
```yaml
apiVersion: v1
kind: Service
metadata:
  name: fileserver
  namespace: kube-public
spec:
  ports:
  - name: app
    port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: fileserver
  type: ClusterIP
```

此时访问 Service 地址，即可看到文件索引的页面，通过 scp 或上传文件到 `/usr/share/nginx/files` 目录，即可看到文件并下载。    