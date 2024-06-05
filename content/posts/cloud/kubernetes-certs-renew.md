+++ 
draft = false
date = 2024-05-31T16:08:07+08:00
title = "手动二进制部署的 kubernetes 集群证书过期处理"
slug = ""
authors = ["Maoqide"]
tags = ["kubernetes", "certs"]
categories = []
externalLink = ""
series = []
+++

---
通过 kubeadm 更新手动部署的 kubernetes 集群证书。

<!--more-->

## 现象
一个二进制部署的 kubernetes 集群，突然发现无法连接到 apiserver，执行 `kubectl` 时报错：     

    Unable to connect to the server: x509: certificate has expired or is not yet valid: current time 2024-05-31T15:25:02+08:00 is after 2024-05-29T08:07:53Z

## 解决
排查下来原因是 apiserver 的证书过期，导致 kubectl 及其他的控制面组件均无法连接到 apiserver。所以我们需要更新 apiserver 的证书。由于这是一个比较古老的集群，之前还是完全使用手动二进制部署方式，证书也是手动生成的，维护并不方便。因此我想要通过 kubeadm 来更新集群证书。

通过查阅官方文档 [使用 kubeadm 进行证书管理](https://kubernetes.io/zh-cn/docs/tasks/administer-cluster/kubeadm/kubeadm-certs/#custom-certificates)，发现是可行的，只要在生成证书时，将手动生成证书时使用的根证书 ca.crt 和 ca.key 传递给 kubeadm 即可。具体方式如下：

1. 备份原有证书。备份是一个好习惯，需要养成。在更新证书之前，先将原有证书备份一份，出现问题时可以快速恢复。
```shell
cp -r /etc/kubernetes/pki /etc/kubernetes/pki.bak
```

2. 下载 kubeadm，下载和当前集群版本对应的 kubeadm 工具。

3. 准备证书生成目录。kubeadm 默认生成证书是在 /etc/kubernetes/pki 下，为了避免出现问题覆盖原有证书，我新建了一个目录`/tmp/kubernetes/pki`用于证书生成，同时将原 ca 证书文件拷贝到该目录下。
```shell
mkdir -p /tmp/kubernetes/pki
cp /etc/kubernetes/pki/ca.crt /tmp/kubernetes/pki
cp /etc/kubernetes/pki/ca.key /tmp/kubernetes/pki
```

4. 准备 kubeadm config 文件。执行 kubeadm 时，需要指定一个配置文件，用来告诉 kubeadm apiserver 的地址、pods/svc 的网段、DNS 后缀等信息，以便在生成证书时，写入 csr 文件中。否则证书更新后可能出现 x509 错误。以下是我在生成时指定的配置文件。
```yaml
apiVersion: kubeadm.k8s.io/v1beta2
kind: ClusterConfiguration
controlPlaneEndpoint: "172.16.249.85:6443"
networking:
  podSubnet: "xx.xxx.0.0/17"
  serviceSubnet: "xx.xxx.128.0/17"
  dnsDomain: "cluster.local"
certificatesDir: "/tmp/kubernetes/certs"
```

5. 生成新的证书。
```shell
# 生成所有证书
./kubeadm init phase certs all --config kubeadm-config.yaml

# 实际上这里只需要更新 apiserver 的证书即可，可以指定只生成 apiserver 证书
./kubeadm init phase certs apiserver --config kubeadm-config.yaml
```

6. 更新证书。将生成的 apiserver 的证书拷贝到原有证书目录下。
```shell
cp -f /tmp/kubernetes/pki/apiserver.crt /etc/kubernetes/pki
cp -f /tmp/kubernetes/pki/apiserver.key /etc/kubernetes/pki
```

到此，证书更新已经完成，可以检查下集群是否恢复正常。
