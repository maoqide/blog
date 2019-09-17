---
title: "Glusterfs Kubernetes"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "glusterfs", "presistence volume"]
date: 2019-09-06T08:46:14+08:00
draft: true
---

在 kubernetes 中使用 glusterfs 作为 pv。    
<!--more-->

## environment
- centos7    
- 3.10.0-957.27.2.el7.x86_64    

## 机器（virtualbox 虚拟机）
- centos10 - 172.27.32.165 - kubernetes master节点    
- centos12l - 172.27.32.182 - glusterfs节点/kubernetes node节点     
- centos11 - 172.27.32.164 - glusterfs节点/kubernetes node节点     

## virtualbox 添加硬盘
- 关闭虚拟机    
- 设置-存储-控制器SATA-新建磁盘-固定大小    
- 启动虚拟机    

开机后执行`fdisk -l`，其中 /dev/sdb 为新创建出的磁盘。    
```shell
[root@centos12l ~]$ fdisk -l
Disk /dev/sda: 54.5 GB, 54495248384 bytes, 106436032 sectors
Units = sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disk label type: dos
Disk identifier: 0x0001552e

   Device Boot      Start         End      Blocks   Id  System
/dev/sda1   *        2048     2099199     1048576   83  Linux
/dev/sda2         2099200   106434559    52167680   8e  Linux LVM

Disk /dev/sdb: 10.7 GB, 10737418240 bytes, 20971520 sectors
Units = sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes


Disk /dev/mapper/centos-root: 51.3 GB, 51266977792 bytes, 100130816 sectors
Units = sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes


Disk /dev/mapper/centos-swap: 2147 MB, 2147483648 bytes, 4194304 sectors
Units = sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
```

如果使用[gluster-kubernetes](https://github.com/gluster/gluster-kubernetes)提供的`gk-deploy`脚本配置glusterfs，无需进行一下的磁盘挂载操作。   

## 磁盘挂载
***以下为手动部署 glusterfs 的步骤，使用`gk-deploy`在kubernetes上使用glusterfs跳过此步，否则会创建失败。***    

**执行`fdisk /dev/sdb`并根据提示进行磁盘写入**    
```shell
[root@centos12l ~]$ fdisk /dev/sdb 
Welcome to fdisk (util-linux 2.23.2).

Changes will remain in memory only, until you decide to write them.
Be careful before using the write command.

Device does not contain a recognized partition table
Building a new DOS disklabel with disk identifier 0xf6e6b69c.

Command (m for help): n
Partition type:
   p   primary (0 primary, 0 extended, 4 free)
   e   extended
Select (default p): p
Partition number (1-4, default 1): 
First sector (2048-20971519, default 2048): 
Using default value 2048
Last sector, +sectors or +size{K,M,G} (2048-20971519, default 20971519): 
Using default value 20971519
Partition 1 of type Linux and of size 10 GiB is set

Command (m for help): w
The partition table has been altered!

Calling ioctl() to re-read partition table.
Syncing disks.

```

需要 ext4 模块，`lsmod | grep ext4` 查看是否已加载，没有的话执行`modprobe ext4`加载。    
```shell
[root@centos12l ~]$ lsmod | grep ext4  
ext4                  579979  0 
mbcache                14958  1 ext4
jbd2                  107478  1 ext4
```
**执行`mkfs.ext4 /dev/sdb1`格式化磁盘。**     
```shell
[root@centos12l ~]$ mkfs.ext4 /dev/sdb1
mke2fs 1.42.9 (28-Dec-2013)
Filesystem label=
OS type: Linux
Block size=4096 (log=2)
Fragment size=4096 (log=2)
Stride=0 blocks, Stripe width=0 blocks
655360 inodes, 2621184 blocks
131059 blocks (5.00%) reserved for the super user
First data block=0
Maximum filesystem blocks=2151677952
80 block groups
32768 blocks per group, 32768 fragments per group
8192 inodes per group
Superblock backups stored on blocks: 
	32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632

Allocating group tables: done                            
Writing inode tables: done                            
Creating journal (32768 blocks): done
Writing superblocks and filesystem accounting information: done 
```

**将磁盘挂载到`data`目录**     
`mkdir /data`
`mount -t ext4 /dev/sdb1 /data`

```shell
[root@centos12l ~]$ df -h
Filesystem               Size  Used Avail Use% Mounted on
/dev/mapper/centos-root   48G  2.7G   46G   6% /
devtmpfs                 908M     0  908M   0% /dev
tmpfs                    920M     0  920M   0% /dev/shm
tmpfs                    920M  9.2M  910M   1% /run
tmpfs                    920M     0  920M   0% /sys/fs/cgroup
/dev/sda1               1014M  189M  826M  19% /boot
tmpfs                    184M     0  184M   0% /run/user/0
/dev/sdb1                9.8G   37M  9.2G   1% /data
```

**写入fstab开机自动挂载**     
`vim /etc/fstab`
```shell
/dev/sdb1                   /data                ext4    defaults        0 0
```

## 安装 glusterfs server
`yum install -y centos-release-gluster`
`yum install -y glusterfs-server`
`systemctl start glusterd`
`systemctl enable glusterd`

以下命名从glusterfs节点中选取一台执行即可。    
`gluster peer probe 172.27.32.182`，添加远程节点。    
```shell
[root@centos11 ~]$ gluster peer probe 172.27.32.182
peer probe: success. 
```
`gluster peer status`，查看远程节点状态。    
```shell
root@centos11 ~]$ gluster peer status
Number of Peers: 1

Hostname: 172.27.32.182
Uuid: 3ad2f5fc-2cd6-4d0a-a42d-d3325eb0c687
State: Peer in Cluster (Connected)
```

`gluster pool list`，查看节点列表。    
```shell
[root@centos11 ~]$ gluster pool list
UUID					Hostname     	State
3ad2f5fc-2cd6-4d0a-a42d-d3325eb0c687	172.27.32.182	Connected 
1717b41d-c7cd-457e-bfe3-1c825d837488	localhost    	Connected 
```

## 安装 glusterfs
glusterfs 需要以下内核模块：    
- dm_snapshot    
- dm_mirror     
- dm_thin_pool    
执行`lsmod | grep <name>`查看模块是否存在，如果不存在的话执行`modprobe <name>`加载模块。    

安装 glusterfs：    
```shell
# install
yum install glusterfs-fuse -y
# version
glusterfs --version
```

## 创建 glusterfs volume
***以下为手动部署 glusterfs 的步骤，使用`gk-deploy`在kubernetes上使用glusterfs跳过此步，否则会创建失败。***     

`mkdir /data/gvol`，在节点上创建 volume 的目录。    

以下命名从glusterfs节点中选取一台执行即可。    
`gluster volume create gvol1 replica 2 172.27.32.182:/data/gvol 172.27.32.164:/data/gvol`，创建volume。     
 ```shell
 # 提示两个节点容易发生脑裂，测试目的可以直接选择继续，生产建议3个节点。    
[root@centos11 ~]$ gluster volume create gvol1 replica 2 172.27.32.182:/data/gvol 172.27.32.164:/data/gvol
Replica 2 volumes are prone to split-brain. Use Arbiter or Replica 3 to avoid this. See: http://docs.gluster.org/en/latest/Administrator%20Guide/Split%20brain%20and%20ways%20to%20deal%20with%20it/.
Do you still want to continue?
 (y/n) y
volume create: gvol1: success: please start the volume to access data
```
此 volume 为 Repicate 类型，其他类型可查看官方文档[volume-types](https://docs.gluster.org/en/latest/Administrator%20Guide/Setting%20Up%20Volumes/#volume-types)。    

`gluster volume start gvol1`，启动 volume。    
```shell
[root@centos11 ~]$ gluster volume start gvol1
volume start: gvol1: success
```

`gluster volume info gvol1`，查看 volume 信息。     
```shell
[root@centos11 ~]$ gluster volume info gvol1
Volume Name: gvol1
Type: Replicate
Volume ID: ed8662a9-a698-4730-8ac7-de579890b720
Status: Started
Snapshot Count: 0
Number of Bricks: 1 x 2 = 2
Transport-type: tcp
Bricks:
Brick1: 172.27.32.182:/data/vol1
Brick2: 172.27.32.164:/data/vol1
Options Reconfigured:
transport.address-family: inet
nfs.disable: on
performance.client-io-threads: off
```

挂载 glusterfs volume，将 glusterfs 的 vloume gvol1 挂载到`/data/gfs`目录下。      
`mkdir -p /data/gfs`    
`mount -t glusterfs 172.27.32.164:/gvol1 /data/gfs`    
```shell
# df -h 可以看到已经挂载上
[root@centos11 gfs]$ df -h
Filesystem               Size  Used Avail Use% Mounted on
/dev/mapper/centos-root   46G  3.3G   42G   8% /
devtmpfs                 1.9G     0  1.9G   0% /dev
tmpfs                    1.9G     0  1.9G   0% /dev/shm
tmpfs                    1.9G  9.5M  1.9G   1% /run
tmpfs                    1.9G     0  1.9G   0% /sys/fs/cgroup
/dev/sda1               1014M  189M  826M  19% /boot
tmpfs                    379M     0  379M   0% /run/user/0
/dev/sdb1                9.8G   37M  9.2G   1% /data
172.27.32.182:/gvol1     9.8G  136M  9.2G   2% /data/gfs
```
在 `data/gfs` 下写入或更改文件，会自动同步到所有glusterfs节点 `gvol1` 下的目录中。     
将如下配置添加到`/etc/fstab`，当系统重启后自动 mount 目录。     
```
172.27.32.182:/gvol1 /data/gfs glusterfs  defaults,_netdev 0 0
```

## gluster-kubernetes
[gluster-kubernetes](https://github.com/gluster/gluster-kubernetes) 项目由官方提供的脚本，在kubernetes 上集成 glusterfs。    
以下命令未特殊说明的都是在kubernetes master节点上执行。    
```shell
# 下载项目代码到 /root 文件夹下
git clone https://github.com/gluster/gluster-kubernetes.git
# 进入到 deploy 目录，这也是脚本所在的工作目录
# deploy/kube-templates/ 文件夹下为需要在kubernetes上创建的资源的 yaml 文件。
cd /gluster-kubernetes/deploy

# 修改 topology.json, 描述你的 glusterfs 集群的信息
mv topology.json.sample topology.json
vim topology.json
```
```shell
{
  "clusters": [
    {
      "nodes": [
        {
          "node": {
            "hostnames": {
              "manage": [
                "172.27.32.164"
              ],
              "storage": [
                "172.27.32.164"
              ]
            },
            "zone": 1
          },
          "devices": [
            "/dev/sdc"
          ]
        },
        {
          "node": {
            "hostnames": {
              "manage": [
                "172.27.32.182"
              ],
              "storage": [
                "172.27.32.182"
              ]
            },
            "zone": 1
          },
          "devices": [
            "/dev/sdc"
          ]
        }
      ]
    }
  ]
}
```
`gk-deploy`需要为初始化过的磁盘，所以这里在两个节点上分别挂载了新的磁盘设备`/dev/sdc`，并执行以下命令。    
```shell
# 每台 glusterfs 节点上执行如下命令
# /dev/sdc 需要是新的为初始化的设备
dd if=/dev/urandom of=/dev/sdc bs=512 count=64
```

使用 base64 生成 heketi 所需要的key，此节点需要指定能够登陆 glusterfs 节点的私钥。     
如果不指定 --ssh-keyfile, `gk-deploy`会默认在kubernetes内创建新的 glusterfs pod，而不是使用本地已有的。    
```shell
# generate key
echo -n hello | base64
# gk-deploy
./gk-deploy -h
./gk-deploy --admin-key aGVsbG8= --user-key aGVsbG8=  --ssh-keyfile /root/.ssh/id_rsa
```
```shell
[root@centos10 deploy]$ ./gk-deploy --admin-key aGVsbG8= --user-key aGVsbG8=  --ssh-keyfile /root/.ssh/id_rsa
Welcome to the deployment tool for GlusterFS on Kubernetes and OpenShift.

Before getting started, this script has some requirements of the execution
environment and of the container platform that you should verify.

The client machine that will run this script must have:
 * Administrative access to an existing Kubernetes or OpenShift cluster
 * Access to a python interpreter 'python'

Each of the nodes that will host GlusterFS must also have appropriate firewall
rules for the required GlusterFS ports:
 * 2222  - sshd (if running GlusterFS in a pod)
 * 24007 - GlusterFS Management
 * 24008 - GlusterFS RDMA
 * 49152 to 49251 - Each brick for every volume on the host requires its own
   port. For every new brick, one new port will be used starting at 49152. We
   recommend a default range of 49152-49251 on each host, though you can adjust
   this to fit your needs.

The following kernel modules must be loaded:
 * dm_snapshot
 * dm_mirror
 * dm_thin_pool

For systems with SELinux, the following settings need to be considered:
 * virt_sandbox_use_fusefs should be enabled on each node to allow writing to
   remote GlusterFS volumes

In addition, for an OpenShift deployment you must:
 * Have 'cluster_admin' role on the administrative account doing the deployment
 * Add the 'default' and 'router' Service Accounts to the 'privileged' SCC
 * Have a router deployed that is configured to allow apps to access services
   running in the cluster

Do you wish to proceed with deployment?

[Y]es, [N]o? [Default: Y]: y
Using Kubernetes CLI.
Using namespace "default".
Checking for pre-existing resources...
  GlusterFS pods ... not found.
  deploy-heketi pod ... not found.
  heketi pod ... not found.
  gluster-s3 pod ... not found.
Creating initial resources ... serviceaccount "heketi-service-account" created
clusterrolebinding.rbac.authorization.k8s.io "heketi-sa-view" created
clusterrolebinding.rbac.authorization.k8s.io "heketi-sa-view" labeled
OK
secret "heketi-config-secret" created
secret "heketi-config-secret" labeled
service "deploy-heketi" created
deployment.extensions "deploy-heketi" created
Waiting for deploy-heketi pod to start ... OK
Creating cluster ... ID: e5558e7dacc4f24c75f62a68168105fc
Allowing file volumes on cluster.
Allowing block volumes on cluster.
Creating node 172.27.32.164 ... ID: 23abb66f328935c437b6d0274388027f
Adding device /dev/sdc ... OK
Creating node 172.27.32.182 ... ID: 7f99fb669bad6434cdf16258e507dbb7
Adding device /dev/sdc ... OK
heketi topology loaded.
Error: Failed to allocate new volume: No space
command terminated with exit code 255
Failed on setup openshift heketi storage
This may indicate that the storage must be wiped and the GlusterFS nodes must be reset.
```
直接执行会发生如上报错 No space，这是由于我们的 glusterfs 集群只有两个节点，和 heketi 默认至少需要三个节点，可以在执行`gk-deploy`时加上`--single-ndoe`参数跳过此报错。    

再次执行之前，需要对环境做下清理，在glusterfs节点上执行以下命令。（这里的pv跟k8s的pv概念没有关系）        
```shell
# 查看 pv，第二行 /dev/sdc 即为 heketi 创建的 pv，需要删除
[root@centos11 ~]$ pvs
  PV         VG                                  Fmt  Attr PSize   PFree
  /dev/sda2  centos                              lvm2 a--  <49.00g 4.00m
  /dev/sdc   vg_bf7e75e181a24a59edc0d38e33d5ee9c lvm2 a--    7.87g 7.87g
```
```shell
## 删除pv
[root@centos11 ~]$ pvremove /dev/sdc  -ff
  WARNING: PV /dev/sdc is used by VG vg_bf7e75e181a24a59edc0d38e33d5ee9c.
Really WIPE LABELS from physical volume "/dev/sdc" of volume group "vg_bf7e75e181a24a59edc0d38e33d5ee9c" [y/n]? y
  WARNING: Wiping physical volume label from /dev/sdc of volume group "vg_bf7e75e181a24a59edc0d38e33d5ee9c".
  Labels on physical volume "/dev/sdc" successfully wiped.
```

清理`gk-deploy`脚本创建的 kubernetes 资源。    
```shell
kubectl delete sa heketi-service-account
kubectl delete clusterrolebinding heketi-sa-view
kubectl delete secret heketi-config-secret
kubectl delete svc deploy-heketi
kubectl delete deploy deploy-heketi
```

再次创建：     
```shell
# heketi 默认要求至少3个glusterfs 节点，否则会报错 no space，我们只有两个节点，需要添加 --single-node 参数
[root@centos10 deploy]$ ./gk-deploy --admin-key aGVsbG8= --user-key aGVsbG8=  --ssh-keyfile /root/.ssh/id_rsa --single-node
Welcome to the deployment tool for GlusterFS on Kubernetes and OpenShift.

Before getting started, this script has some requirements of the execution
environment and of the container platform that you should verify.

The client machine that will run this script must have:
 * Administrative access to an existing Kubernetes or OpenShift cluster
 * Access to a python interpreter 'python'

Each of the nodes that will host GlusterFS must also have appropriate firewall
rules for the required GlusterFS ports:
 * 2222  - sshd (if running GlusterFS in a pod)
 * 24007 - GlusterFS Management
 * 24008 - GlusterFS RDMA
 * 49152 to 49251 - Each brick for every volume on the host requires its own
   port. For every new brick, one new port will be used starting at 49152. We
   recommend a default range of 49152-49251 on each host, though you can adjust
   this to fit your needs.

The following kernel modules must be loaded:
 * dm_snapshot
 * dm_mirror
 * dm_thin_pool

For systems with SELinux, the following settings need to be considered:
 * virt_sandbox_use_fusefs should be enabled on each node to allow writing to
   remote GlusterFS volumes

In addition, for an OpenShift deployment you must:
 * Have 'cluster_admin' role on the administrative account doing the deployment
 * Add the 'default' and 'router' Service Accounts to the 'privileged' SCC
 * Have a router deployed that is configured to allow apps to access services
   running in the cluster

Do you wish to proceed with deployment?

[Y]es, [N]o? [Default: Y]: y
Using Kubernetes CLI.
Using namespace "default".
Checking for pre-existing resources...
  GlusterFS pods ... not found.
  deploy-heketi pod ... 

not found.
  heketi pod ... not found.
  gluster-s3 pod ... not found.
Creating initial resources ... serviceaccount "heketi-service-account" created
clusterrolebinding.rbac.authorization.k8s.io "heketi-sa-view" created
clusterrolebinding.rbac.authorization.k8s.io "heketi-sa-view" labeled
OK
secret "heketi-config-secret" created
secret "heketi-config-secret" labeled
service "deploy-heketi" created
deployment.extensions "deploy-heketi" created
Waiting for deploy-heketi pod to start ... 
OK

Creating cluster ... ID: 09f68c8a429b152a196d0edc936c170f
Allowing file volumes on cluster.
Allowing block volumes on cluster.
Creating node 172.27.32.164 ... ID: 534b4285f90fadabc67341e8547a21fa
Adding device /dev/sdc ... OK
Creating node 172.27.32.182 ... ID: c53b72f42949056bcf21aa360f3ec442
Adding device /dev/sdc ... OK
heketi topology loaded.
Saving /tmp/heketi-storage.json
secret "heketi-storage-secret" created
endpoints "heketi-storage-endpoints" created
service "heketi-storage-endpoints" created
job.batch "heketi-storage-copy-job" created
service "heketi-storage-endpoints" labeled
pod "deploy-heketi-bf46f97fb-p9t4m" deleted
service "deploy-heketi" deleted
deployment.apps "deploy-heketi" deleted
job.batch "heketi-storage-copy-job" deleted
secret "heketi-storage-secret" deleted
service "heketi" created
deployment.extensions "heketi" created
Waiting for heketi pod to start ... OK
Flag --show-all has been deprecated, will be removed in an upcoming release

heketi is now running and accessible via http://10.244.145.28:8080 . To run
administrative commands you can install 'heketi-cli' and use it as follows:

  # heketi-cli -s http://10.244.145.28:8080 --user admin --secret '<ADMIN_KEY>' cluster list

You can find it at https://github.com/heketi/heketi/releases . Alternatively,
use it from within the heketi pod:

  # /usr/bin/kubectl -n default exec -i heketi-77f4797494-45cfl -- heketi-cli -s http://localhost:8080 --user admin --secret '<ADMIN_KEY>' cluster list

For dynamic provisioning, create a StorageClass similar to this:

---
apiVersion: storage.k8s.io/v1beta1
kind: StorageClass
metadata:
  name: glusterfs-storage
provisioner: kubernetes.io/glusterfs
parameters:
  resturl: "http://10.244.145.28:8080"
  restuser: "user"
  restuserkey: "aGVsbG8="


Deployment complete!
```
创建成功！    

## 创建 storageclass 测试

## 创建 pv pvc 测试

## 在 kubernetes 集群内起 glusterfs pod