---
title: "Upgrade Kubernets From Binary to Kubeadm"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "kubeadm", "etcd"]
date: 2019-08-06T13:55:04+08:00
# draft: true
---

记一次从二进制部署的 k8s 集群 到 kubeadm 部署的 k8s 迁移测试。    
原有 k8s 集群为二进制形式部署，集群管理不太方便，准备在集群升级的机会，将集群部署方式改为 kubeadm部署，本文记录测试迁移的过程。     

<!--more-->
## 部署新的 master 集群
### etcd 数据迁移
为了完全不影响原有集群的运行，将 etcd 也做迁移，新的 master 连接新的 etcd，不对老集群造成影响。    
首先新建一个 etcd，并使用 etcd 的 make-mirror 功能将原有集群的 etcd 数据同步到新的etcd中。     
```shell
# 新起一个 etcd，为了方便这里新建不带证书的 http 端口
docker run -d \
        --name etcd \
	--net host \
	-v /data/etcd:/var/lib/etcd \
	quay.io/coreos/etcd:v3.3.13 \
	etcd --listen-client-urls http://0.0.0.0:2379 --advertise-client-urls http://0.0.0.0:2379
```

```shell
#  迁移数据
export ETCDCTL_API=3
etcdctl --endpoints=https://etcd-ip:2379 --cert=/etc/kubernetes/ssl/etcd.pem --cacert=/etc/kubernetes/ssl/ca.pem --key=/etc/kubernetes/ssl/etcd-key.pem make-mirror http://destination-ip:2379
```
由于 kubeadm 会自动新建 dns，所以在新的 etcd 中，将导入过来的 kube-dns 相关数据手动删掉。    
```shell
# 执行如下命令知道删掉所有 kube-dns 相关的key
echo  $(etcdctl get / --prefix --keys-only | grep 'kube-dns') | awk -F ' ' '{ print $1}' | xargs etcdctl del
```

### 新建 master 集群
使用 kubeadm 新建集群，要注意集群配置要和之前一致，如 serviceSubnet, netSubnet 等，并指定 etcd 为刚才新建的 etcd，以下为 kubeadm 配置文件(用的老版本配置，最新版本的 kubeadm 已经不支持)。      
```
apiVersion: kubeadm.k8s.io/v1alpha1
kind: MasterConfiguration
api:
  advertiseAddress: 172.27.32.165
etcd:
  endpoints:
    - http://172.27.32.165:2379
networking:
  serviceSubnet: 10.254.0.0/16
  podSubnet: 172.41.0.0/16
kubernetesVersion: 1.10.13
imageRepository: harbor.guahao-inc.com/kubernetes
apiServerExtraArgs:
  insecure-bind-address: 172.27.32.165
kubeletConfiguration:
  baseConfig:
    clusterDNS:
    - 10.254.0.2
nodeName: 172.27.32.165
```
```shell
# kubelet.service 加上如下配置
Environment="KUBELET_EXTRA_ARGS=--pod-infra-container-image=harbor.guahao-inc.com/kubernetes/pause-amd64:3.1 --hostname-override=172.27.32.165"
```
*kubeadm 配置文件中设置了nodeName，要同时在 kubelet 的 kubelet.service文件中加上 --hostname-override 参事，否则 kubelet 注册 apiserver 时会出现node forbidden 错误*      

```shell
# 使用配置文件新建 master 节点，目前所用 k8s 集群版本较老，不支持新版本docker，忽略docker版本校验
# 创建之前可以先 dryrun 进行校验，没问题再真正执行，dryrun 会将需要做的步骤模拟执行并输出，不会真正操作
kubeadm init --dry-run  --config kubeadm.yaml --ignore-preflight-errors=SystemVerification
kubeadm init --config kubeadm.yaml --ignore-preflight-errors=SystemVerification
```
完成后会提示新建成功，并提示后续操作命令，及node节点加入集群的命令。    
```shell
# 配置 kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# 加入集群的命令可以用 kubeadm 重新生成
kubeadm token create --print-join-command
```

此时已经建好新的 master 节点，并且使用 kubectl get no 可以看到原有集群的节点信息，但这时只是导过来的 etcd，实际上此时 master 节点并未控制 node 节点，node 节点的 kubelet 依然是注册到老的 master 节点，想要将原来的 node 节点迁移到新的 master 节点下，还需要逐台修改每台 node 节点的配置。    

### 迁移 node 节点
迁移 node 节点要注意首先要备份原node节点的 `/etc/kubernetes/`、`/var/lib/kubelet/` 和 `/etc/systemd/system/kubelet.service`、`/etc/systemd/system/kubelet.service.d/`文件及目录，以便出现异常时可以快速回滚恢复。    
做好备份后，将当前节点`kubelet`、`kube-proxy`停掉，并执行如下命令，由于节点上 kebelet 已经启动且已有 pod 在运行，需要加上 `--ignore-preflight-errors=all` 强制执行，主要是为了生成 kubelet 相关证书及配置文件，并重启 kubelet 注册到新的 master 节点的 apiserver，此时 `--node-name` 要指定和之前一样的节点名称，如果 kubelet.service 配置不正确的话，需要手动修改相关配置（参考 kubeadm 新建节点的配置）。     
```shell
kubeadm join  --node-name 192.168.l96.31 172.27.32.165:6443 --token qfr5ff.sd7qn0tlx2a3kxtl --discovery-token-ca-cert-hash sha256:0f7175e3cf8e40d41983688aeb8e80153c2502cd375629379a5abb53f71bce0d --ignore-preflight-errors=all
```
成功的话，在新的 master 节点执行`kubectl get no`会能够看到迁移的节点已经变成 ready 状态。     
若出现异常，将之前备份的目录和文件还原，并重启`kubelet`和`kube-proxy`，即可恢复节点。    

------

以上是经测试验证过的一种思路，但是在实际生产中，用这种方式进行迁移，还是会对在运行容器产生影响，若要应用到生产环境，还需更严谨详细的测试，并且此种方式的迁移风险较大，测试中遇到很多坑，应尽量避免。    