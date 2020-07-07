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
iptables 底层实现是 netfilter，netfilter 在 IP 层放置 5 个钩子， PREROUTING, POSTROUTING, INPUT, OUTPUT, FORWARD。    
iptables 是用户空间的一个程序，通过 netlink 和内核的 netfilter 框架打交道，负责往钩子上配置回调函数。    

iptables 使用 Xtables 框架。存在表(tables）、链(chain）和规则(rules）三个层面。    
每个**表**指的是不同类型的数据包处理流程，如 filter 表表示进行数据包过滤，而 nat 表针对连接进行地址转换操作。每个表中又可以存在多个**链**，系统按照预订的规则将数据包通过某个内建链，例如将从本机发出的数据通过OUTPUT链。在**链**中可以存在若干**规则**，这些规则会被逐一进行匹配，如果匹配，可以执行相应的**动作**，如修改数据包，或者跳转。跳转可以直接接受该数据包或拒绝该数据包，也可以跳转到其他链继续进行匹配，或者从当前链返回调用者链。当链中所有规则都执行完仍然没有跳转时，将根据该链的默认策略(policy)执行对应动作；如果也没有默认动作，则是返回调用者链。        

5 条链:    
- PREROUTING: 数据包进入路由表之前，可以在此处进行 DNAT    
- INPUT: 通过路由表后目的地为本机，一般用于处理输入本地进程的数据包    
- FORWARDING: 通过路由表后，目的地不为本机，一般用于处理转发到其他机器/network namespace 的数据包    
- OUTPUT: 由本机产生，向外转发，一般用于处理本地进程的输出数据包    
- POSTROUTIONG: 发送到网卡接口之前，可以在此处进行 SNAT    

5 张表:     
- filter: 一般的过滤功能，用于控制到达某条链的数据包是 放行、丢弃(drop) 或拒绝 (reject)    
- nat: 用于 nat 功能（端口映射，地址映射等），修改数据包的源和目的地址    
- mangle: 用于对特定数据包的修改，修改数据包的 IP 头信息    
- raw: 有限级最高，设置 raw 时一般是为了不再让 iptables 做数据包的链接跟踪处理，提高性能    
- *security: 不常用，用于在数据包上应用 SELinux*     
优先级: raw > mangle > nat > filter > security   

![](/media/posts/cloud/network/tables_traverse.jpg)    

每张表上可以挂的链的种类不同，具体如下:     
- filter表: INPUT、FORWARD、OUTPUT    
- nat表: PREROUTING、POSTROUTING、OUTPUT    
- mangle表: PREROUTING、POSTROUTING、INPUT、OUTPUT、FORWARD    
- raw表: OUTPUT、PREROUTING    

常见的动作:    
- DROP: 直接将数据包丢弃，不再进行后续处理。场景：模拟宕机、服务不存在。    
- REJECT: 返回客户端`connection refused`或`destination unreachable`报文。场景：拒绝客户端访问。    
- QUEUE: 将数据包放入用户空间的队列，供用户空间的程序处理。    
- RETURN: 跳出当前链，该链中后续规则不再执行。    
- ACCEPT: 同意数据包通过，继续执行后续规则。    
- JUMP: 跳转到其他用户自定义链继续执行。    

