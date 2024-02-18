---
title: "阿里云主机搭建 K8S 集群"
date: 2018-11-14T14:31:38+08:00
draft: false
author: "Maoqide"
tags: ["cloud", "kubernetes"]
---


通过阿里云ECS实例搭建K8S集群
<!--more--> 

## 环境
 - 阿里云ECS * 2
 - centos7.4
 - 阿里云两台机器需要内网互通（同一k可用区可以创建免费VPC高速通道实现）

## 安装 docker
[官方文档](https://docs.docker.com/install/linux/docker-ce/centos/)
```shell
sudo yum install -y yum-utils \
  device-mapper-persistent-data \
  lvm2
sudo yum-config-manager \
    --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce
```
## 配置代理
- [shadowsocks服务端](https://github.com/shadowsocks/shadowsocks/tree/master)
- provixy
- shadowsocks客户端 sslocal

### 安装 shadowsocks
```shell
yum -y install python-pip
pip install shadowsocks
```
### 配置 shadowsocks
```shell
vim /etc/shadowsocks.json
```
```json
{
    "server":"1.1.1.1", 			//shadowsocks server ip
    "server_port":8888,				//shadowsocks server port
    "local_address": "127.0.0.1",	
    "local_port":1080,				//default 1080
    "password":"ssserver_passwd",
    "timeout":300,
    "method":"aes-256-cfb",
    "fast_open": false,
    "workers": 1
}

```
### 安装 privoxy
配置全局代理或 gfwlist 代理    
```shell
yum -y install privoxy
# 全局代理
echo 'forward-socks5 / 127.0.0.1:1080 .' >>/etc/privoxy/config

# gfwlist 代理
# 获取 gfwlist2privoxy 脚本
curl -4sSkL https://raw.github.com/zfl9/gfwlist2privoxy/master/gfwlist2privoxy -O

# 生成 gfwlist.action 文件
bash gfwlist2privoxy '127.0.0.1:1080'

# 检查 gfwlist.action 文件
more gfwlist.action # 一般有 5000+ 行

# 应用 gfwlist.action 文件
mv -f gfwlist.action /etc/privoxy
echo 'actionsfile gfwlist.action' >>/etc/privoxy/config
```

#### 配置快捷命令
在 /etc/profile.d 新建 set_proxy.sh, linux开机会自动执行该目录下可执行文件    
```shell
vim /etc/profile.d/set_proxy.sh
```
```shell
[root@localhost ~]$ cat /etc/profile.d/set_proxy.sh 
# Initialization script for bash and sh
# export proxy for GFW
alias proxy_on='nohup sslocal -c /etc/shadowsocks.json & systemctl start privoxy'
alias proxy_off='systemctl stop privoxy && pkill sslocal'
alias proxy_export='export http_proxy=http://127.0.0.1:8118 && export https_proxy=http://127.0.0.1:8118 && export no_proxy=localhost'
alias proxy_unset='unset http_proxy https_proxy no_proxy'
alias proxy_test='curl google.com'
```
手动执行 /etc/profile, 会重新执行/etc/profile.d下文件    
```shell
source /etc/profile
```
执行alias查看，发现有proxy前缀的别名，则配置成功    
```shell
[root@localhost ~]$ alias 
alias egrep='egrep --color=auto'
alias fgrep='fgrep --color=auto'
alias grep='grep --color=auto'
alias l.='ls -d .* --color=auto'
alias ll='ls -l --color=auto'
alias ls='ls --color=auto'
alias proxy_export='export http_proxy=http://127.0.0.1:8118 && export https_proxy=http://127.0.0.1:8118 && export no_proxy=localhost'
alias proxy_off='systemctl stop privoxy && pkill sslocal'
alias proxy_on='nohup sslocal -c /etc/shadowsocks.json & systemctl start privoxy'
alias proxy_test='curl google.com'
alias proxy_unset='unset http_proxy https_proxy no_proxy'
alias vi='vim'
alias which='alias | /usr/bin/which --tty-only --read-alias --show-dot --show-tilde'
```
执行下面命令开启代理，并配置环境变量(只对当前shell生效，若要永久生效需要在/etc/proxy中export环境变量)    
```shell
proxy_on && proxy_export
```
执行 proxy_test 测试代理是否配置成功，出现如下输出则配置成功。     
```shell
[root@mqd1c2g ~]$ proxy_test 
<HTML><HEAD><meta http-equiv="content-type" content="text/html;charset=utf-8">
<TITLE>301 Moved</TITLE></HEAD><BODY>
<H1>301 Moved</H1>
The document has moved
<A HREF="http://www.google.com/">here</A>.
</BODY></HTML>
```
参考: [ss-local 终端代理（gfwlist）](https://www.zfl9.com/ss-local.html)

## 安装 Kubernetes
[官方文档](https://kubernetes.io/docs/setup/independent/install-kubeadm/)

### 安装kubeadm
检查机器是否符合文档中的`Before you begin`的要求, 符合的话才能进行接下来的步骤。    
```shell
cat <<EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
exclude=kube*
EOF

# Set SELinux in permissive mode (effectively disabling it)
setenforce 0
sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config

yum install -y kubelet kubeadm kubectl --disableexcludes=kubernetes

systemctl enable kubelet && systemctl start kubelet
```

### 创建 master 节点
```shell
# pod-network-cidr 10.244.0.0/16 是后面 flannel 默认配置的 pod Network，配置成这个地址不用改的flannel的 默认配置
kubeadm init --pod-network-cidr 10.244.0.0/16
```
成功执行后 master 节点就已经启动了, 可以选择安装一种网络插件，这里选择flannel
```shell
# 使用默认配置启动 flannel 的 DaemonSet
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
```

### 创建 node 节点
在 master 节点执行下面命令生成创建子节点命令
```shell
kubeadm token create --print-join-command
```
```shell
[root@localhost ~]$ kubeadm token create --print-join-command
kubeadm join masterip:6443 --token 5zk5ql.5eq0rgoui0dl0xx3 --discovery-token-ca-cert-hash sha256:5bef3894fc492bf9d93c9f248f84ec3sdsadasdss7685191a9d841fd32a88bb9ac9 
```
在 node 节点执行上述命令生成的命令
```shell
kubeadm join masterip:6443 --token 5zk5ql.5eq0rgoui0dl0xx3 --discovery-token-ca-cert-hash sha256:5bef3894fc492bf9d93c9f248f84ec3sdsadasdss7685191a9d841fd32a88bb9ac9
```
执行成功则 node 节点添加成功

