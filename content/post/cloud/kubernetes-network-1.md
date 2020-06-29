---
title: "Kubernetes Network 1"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["think"]
date: 2020-06-23T09:00:24+08:00
draft: true
---

Cut out summary from your post content here.

<!--more-->

## veth pair
veth pair 设备总是成对出现，一端发送的数据会在另外一端接收。    
```bash
# 创建 veth pair
ip link add veth0 type veth peer name veth1

# 查看
ip link list
```
```
# ip link list
22: veth1@veth0: <BROADCAST,MULTICAST,M-DOWN> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
    link/ether d6:2f:13:50:28:ea brd ff:ff:ff:ff:ff:ff
23: veth0@veth1: <BROADCAST,MULTICAST,M-DOWN> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
    link/ether 82:3c:74:b9:60:23 brd ff:ff:ff:ff:ff:ff
```
```bash
# 启动设备
ip link set dev veth0 up
ip link set dev veth1 up

# 配置 IP 地址
ifconfig veth0 10.20.30.40/24
ifconfig veth1 10.20.30.41/24
```

```bash
# 创建新的 netns
ip netns add netns1
# 查看
ip netns list
# 删除
ip netns delete netns1

# 进入 netns
ip netns exec netns1 bash

# 将上面的 veth1 设备放到 netns1 namespace
ip link set veth1 netns netns1
```
进入 netns1 重新启动设备并设置设备 IP 地址    
```bash
ifconfig veth1 10.20.30.41/24
ip link set dev veth1 up
```
```bash
ping 10.20.30.41 -I veth0
```

*NOTE:*    
*虚拟网络设备可以随意放到自定义 network namespace 中， 真实物理设备只能放在系统根 network namespace 中。*    
*namespace 的 root 用户可以把自己 namespace 的虚拟网络设备移动到其他 namespace，甚至根namespace中。*    

## bridge
bridge 有多个端口，数据可以从任意端口进来，出去的口取决于目的 MAC 地址。    
```bash
# 创建 bridge
# brctl addbr br0
ip link add name br0 type bridge
ip link set br0 up
```

```bash
# 创建 veth pair 并设置 IP 地址
ip link add veth0 type veth peer name veth1
ip addr add 1.2.3.101/24 dev veth0
ip addr add 1.2.3.102/24 dev veth1
ip link set dev veth0 up
ip link set dev veth1 up
```

```bash
# 将 veth0 连接到 br0
# brctl addif br0 veth0
ip link set dev veth0 master br0
```

查看当前网桥上的网络设备    
```
[root@centos11 ~]# bridge link
28: veth0 state UP @veth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 master br0 state forwarding priority 32 cost 2

[root@centos11 ~]# yum install -y bridge-utils 
[root@centos11 ~]# brctl show
bridge name	bridge id		STP enabled	interfaces
br0		8000.22338454dd43	no		veth0
```

```bash
# 将 veth0 设备 IP 分配给 bridge
ip addr del 1.2.3.101/24 dev veth0
ip addr add 1.2.3.101/24 dev br0
```

```bash
# 创建新的 netns netns1 并将 veth1 移动到 netns1
ip netns add netns1
ip link set veth1 netns netns1

# 进入到 netns1 重新配置 IP
ip netns exec netns1 bash
ip addr add 1.2.3.102/24 dev veth1
ip link set dev veth1 up
exit

# 验证
ping  -I br0 1.2.3.102

# 抓包
# yum install tcpdump -y
tcpdump -n -i br0
```
```
[root@centos11 ~]# tcpdump -n -i br0
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on br0, link-type EN10MB (Ethernet), capture size 262144 bytes
08:21:31.312646 IP 1.2.3.101 > 1.2.3.102: ICMP echo request, id 26100, seq 1, length 64
08:21:31.312670 IP 1.2.3.102 > 1.2.3.101: ICMP echo reply, id 26100, seq 1, length 64
08:21:32.312822 IP 1.2.3.101 > 1.2.3.102: ICMP echo request, id 26100, seq 2, length 64
08:21:32.312848 IP 1.2.3.102 > 1.2.3.101: ICMP echo reply, id 26100, seq 2, length 64
08:21:33.312941 IP 1.2.3.101 > 1.2.3.102: ICMP echo request, id 26100, seq 3, length 64
08:21:33.312966 IP 1.2.3.102 > 1.2.3.101: ICMP echo reply, id 26100, seq 3, length 64
08:21:34.312995 IP 1.2.3.101 > 1.2.3.102: ICMP echo request, id 26100, seq 4, length 64
08:21:34.313019 IP 1.2.3.102 > 1.2.3.101: ICMP echo reply, id 26100, seq 4, length 64
08:21:35.313479 IP 1.2.3.101 > 1.2.3.102: ICMP echo request, id 26100, seq 5, length 64
08:21:35.313502 IP 1.2.3.102 > 1.2.3.101: ICMP echo reply, id 26100, seq 5, length 64
08:21:36.313274 IP 1.2.3.101 > 1.2.3.102: ICMP echo request, id 26100, seq 6, length 64
08:21:36.313297 IP 1.2.3.102 > 1.2.3.101: ICMP echo reply, id 26100, seq 6, length 64
```

## tun/tap
tun/tap 设备的特点：一端连着协议栈，另一端连着用户态程序。    


## iptables