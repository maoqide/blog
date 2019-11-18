---
title: "Upgrade Kubeadm Cluster"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "kubeadm", "upgrade"]
date: 2019-10-31T09:50:41+08:00
---

升级 kubeadm 部署的 kubernetes 集群。    
<!--more-->
## 当前环境
```shell
[root@centos10 ~]$ uname -a 
Linux centos10 3.10.0-957.27.2.el7.x86_64 #1 SMP Mon Jul 29 17:46:05 UTC 2019 x86_64 x86_64 x86_64 GNU/Linux

[root@centos10 ~]$ kubectl version
Client Version: version.Info{Major:"1", Minor:"11", GitVersion:"v1.11.10", GitCommit:"7a578febe155a7366767abce40d8a16795a96371", GitTreeState:"clean", BuildDate:"2019-05-01T04:14:38Z", GoVersion:"go1.10.8", Compiler:"gc", Platform:"linux/amd64"}
Server Version: version.Info{Major:"1", Minor:"11", GitVersion:"v1.11.10", GitCommit:"7a578febe155a7366767abce40d8a16795a96371", GitTreeState:"clean", BuildDate:"2019-05-01T04:05:01Z", GoVersion:"go1.10.8", Compiler:"gc", Platform:"linux/amd64"}
```

## 确认升级版本
由于目前集群版本和最新版本相差版本较多，采用逐个版本升级的策略，首先确认要升级到的具体版本。    
```shell
yum list --showduplicates | grep kubeadm
```
选取要升级版本的最新小版本，即`1.12.10-0`。    

## 升级 master
 ```shell
# backup config
kubeadm config view > kubeadm.yaml

# upgrade kubeadm
yum upgrade -y kubeadm-1.12.x --disableexcludes=kubernetes

# confirm version
kubeadm version
 ```

 `kubeadm upgrade plan`查看升级组件后版本    
 ```shell
 [root@centos10 v1.12.10]# kubeadm upgrade plan
[preflight] Running pre-flight checks.
[upgrade] Making sure the cluster is healthy:
[upgrade/config] Making sure the configuration is correct:
[upgrade/config] Reading configuration from the cluster...
[upgrade/config] FYI: You can look at this config file with 'kubectl -n kube-system get cm kubeadm-config -oyaml'
[upgrade] Fetching available versions to upgrade to
[upgrade/versions] Cluster version: v1.11.10
[upgrade/versions] kubeadm version: v1.12.10
I1031 13:42:09.427100    7721 version.go:93] could not fetch a Kubernetes version from the internet: unable to get URL "https://dl.k8s.io/release/stable.txt": Get https://dl.k8s.io/release/stable.txt: net/http: request canceled while waiting for connection (Client.Timeout exceeded while awaiting headers)
I1031 13:42:09.427154    7721 version.go:94] falling back to the local client version: v1.12.10
[upgrade/versions] Latest stable version: v1.12.10
I1031 13:42:19.466181    7721 version.go:93] could not fetch a Kubernetes version from the internet: unable to get URL "https://dl.k8s.io/release/stable-1.11.txt": Get https://dl.k8s.io/release/stable-1.11.txt: net/http: request canceled while waiting for connection (Client.Timeout exceeded while awaiting headers)
I1031 13:42:19.466211    7721 version.go:94] falling back to the local client version: v1.12.10
[upgrade/versions] Latest version in the v1.11 series: v1.12.10

External components that should be upgraded manually before you upgrade the control plane with 'kubeadm upgrade apply':
COMPONENT   CURRENT   AVAILABLE
Etcd        3.3.13    3.2.24

Components that must be upgraded manually after you have upgraded the control plane with 'kubeadm upgrade apply':
COMPONENT   CURRENT        AVAILABLE
Kubelet     3 x v1.11.10   v1.12.10

Upgrade to the latest version in the v1.11 series:

COMPONENT            CURRENT    AVAILABLE
API Server           v1.11.10   v1.12.10
Controller Manager   v1.11.10   v1.12.10
Scheduler            v1.11.10   v1.12.10
Kube Proxy           v1.11.10   v1.12.10
CoreDNS              1.1.3      1.2.2

You can now apply the upgrade by executing the following command:

	kubeadm upgrade apply v1.12.10

_____________________________________________________________________
 ```
可以看到升级后 k8s 各组件版本，由于无法直接访问 gcr 镜像仓库，需要手动拉取对应版本。    
k8s组件的镜像命名基本为 `k8s.gcr.io/<component-name>-<arch>:<component-version>` 或 `gcr.io/google-containers/<component-name>:<component-version>`, 二者实际上是同一仓库，国内可以使用azure 的镜像仓库下载，只要将后者`gcr.io`替换为`gcr.azk8s.cn`即可。也可以使用`https://raw.githubusercontent.com/maoqide/utils/master/pullgcr.sh`脚本一键拉取。     
```shell
pullgcr k8s.gcr.io/kube-apiserver:v1.12.10
pullgcr k8s.gcr.io/kube-controller-manager:v1.12.10
pullgcr k8s.gcr.io/kube-scheduler:v1.12.10
pullgcr k8s.gcr.io/kube-proxy:v1.12.10
pullgcr k8s.gcr.io/coredns:1.2.2
pullgcr k8s.gcr.io/etcd:3.2.24
```
如果使用的内部镜像仓库，将以上镜像tag后推送到内部的镜像仓库中。    
```shell
# using fry-run flag for validation
kubeadm upgrade apply v1.12.10 --config kubeadm.yaml --dry-run
```

使用 `kubeadm config view` 保存的配置，有可能有遗漏，在升级时遇到主节点的 nodeName 配置没有保存，所以在更新时，使用默认的 hostname 为 node name，导致在拉起apiserver的静态pod时，以 kube-apiserver-\<node-name\>的规则拼接 pod 名出错，一直找不到已有的 apiserver 的静态pod，进而导致 upgrade 超时而失败。     
遇到`kubeadm upgrade`一直卡住并最终超时的情况时，首先 `kubeadm upgrade apply  v1.12.10 --config kubeadm.yaml  -v 5`的时候添加 `-v`参数指定 log 等级，一般到5就比较详细了，然后通过日志来定位问题，以上问题就是通过如下日志看到一直在请求错误的 apiserver 的pod名称，从而定位到错误。    
```
[upgrade/apply] Upgrading your Static Pod-hosted control plane to version "v1.12.10"...
I1031 16:03:08.955081   25594 request.go:530] Throttling request took 185.13957ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods/kube-apiserver-centos10
```
解决：`kubeadm config print-default` 可以查看 kubeadm 的 config 文件的所有默认的配置，查看后发现有如下`nodeRegistration`配置, 将node name默认指定成主机的 hostname，导致了上述的错误，在之前通过`kubeadm config view`生成的配置文件中，加上     
```
nodeRegistration:
  name: <real-node-name>
```
并重新执行`kubeadm upgrade apply  v1.12.10 --config kubeadm.yaml`即可。     

在1.13及以后版本中，`kubeadm config print-default` 被修改为`kubeadm config print`的子命令，可执行`kubeadm config print init-defaults`。 
```   
...

nodeRegistration:
  criSocket: /var/run/dockershim.sock
  name: centos10
tlsBootstrapToken: abcdef.0123456789abcdef
token: abcdef.0123456789abcdef
...
```


    1.12升1.13及以后版本，不需要指定 --condig 参数，kubeadm会自动从configmap中读取，只需要执行 kubeadm upgrade apply v1.13.12 即可。     
```shell
[root@centos10 v1.12.10]$ kubeadm upgrade apply  v1.12.10 --config kubeadm.yaml  -v 5
I1031 16:18:09.848434   31033 apply.go:86] running preflight checks
[preflight] Running pre-flight checks.
I1031 16:18:09.848496   31033 apply.go:92] fetching configuration from file kubeadm.yaml
I1031 16:18:09.848507   31033 masterconfig.go:167] loading configuration from the given file
I1031 16:18:09.855269   31033 feature_gate.go:206] feature gates: &{map[]}
I1031 16:18:09.855302   31033 apply.go:150] [upgrade/apply] verifying health of cluster
I1031 16:18:09.855307   31033 apply.go:151] [upgrade/apply] retrieving configuration from cluster
[upgrade] Making sure the cluster is healthy:
[upgrade/config] Making sure the configuration is correct:
[upgrade/config] Reading configuration options from a file: kubeadm.yaml
[upgrade/apply] Respecting the --cri-socket flag that is set with higher priority than the config file.
I1031 16:18:09.877158   31033 apply.go:163] [upgrade/apply] validating requested and actual version
I1031 16:18:09.877171   31033 apply.go:181] [upgrade/version] enforcing version skew policies
[upgrade/version] You have chosen to change the cluster version to "v1.12.10"
[upgrade/versions] Cluster version: v1.11.10
[upgrade/versions] kubeadm version: v1.12.10
[upgrade/confirm] Are you sure you want to proceed with the upgrade? [y/N]: y
I1031 16:18:11.377401   31033 apply.go:195] [upgrade/apply] creating prepuller
[upgrade/prepull] Will prepull images for components [kube-apiserver kube-controller-manager kube-scheduler etcd]
[upgrade/prepull] Prepulling image for component etcd.
[upgrade/prepull] Prepulling image for component kube-apiserver.
[upgrade/prepull] Prepulling image for component kube-controller-manager.
[upgrade/prepull] Prepulling image for component kube-scheduler.
[apiclient] Found 1 Pods for label selector k8s-app=upgrade-prepull-kube-apiserver
[apiclient] Found 0 Pods for label selector k8s-app=upgrade-prepull-etcd
[apiclient] Found 0 Pods for label selector k8s-app=upgrade-prepull-kube-scheduler
[apiclient] Found 1 Pods for label selector k8s-app=upgrade-prepull-kube-controller-manager
[apiclient] Found 1 Pods for label selector k8s-app=upgrade-prepull-etcd
[apiclient] Found 1 Pods for label selector k8s-app=upgrade-prepull-kube-scheduler
I1031 16:18:14.046733   31033 request.go:530] Throttling request took 64.263528ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-controller-manager
I1031 16:18:14.246235   31033 request.go:530] Throttling request took 263.748054ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-scheduler
I1031 16:18:14.647280   31033 request.go:530] Throttling request took 173.534831ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-apiserver
I1031 16:18:14.846492   31033 request.go:530] Throttling request took 367.060734ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-controller-manager
I1031 16:18:15.045493   31033 request.go:530] Throttling request took 566.033546ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-scheduler
I1031 16:18:15.245604   31033 request.go:530] Throttling request took 271.241012ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-etcd
I1031 16:18:15.445656   31033 request.go:530] Throttling request took 471.269391ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-apiserver
I1031 16:18:15.646784   31033 request.go:530] Throttling request took 668.609111ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-controller-manager
I1031 16:18:15.845868   31033 request.go:530] Throttling request took 370.912219ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-etcd
I1031 16:18:16.045929   31033 request.go:530] Throttling request took 570.956625ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-apiserver
I1031 16:18:16.245422   31033 request.go:530] Throttling request took 767.553384ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-scheduler
I1031 16:18:16.445445   31033 request.go:530] Throttling request took 468.71903ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-etcd
[upgrade/prepull] Prepulled image for component etcd.
I1031 16:18:16.645553   31033 request.go:530] Throttling request took 666.826898ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-controller-manager
I1031 16:18:16.845616   31033 request.go:530] Throttling request took 371.917463ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-apiserver
I1031 16:18:17.047923   31033 request.go:530] Throttling request took 568.641489ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-scheduler
I1031 16:18:17.245839   31033 request.go:530] Throttling request took 273.128186ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-apiserver
[upgrade/prepull] Prepulled image for component kube-apiserver.
I1031 16:18:17.445456   31033 request.go:530] Throttling request took 466.94069ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-controller-manager
[upgrade/prepull] Prepulled image for component kube-controller-manager.
I1031 16:18:17.646001   31033 request.go:530] Throttling request took 167.6097ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=k8s-app%3Dupgrade-prepull-kube-scheduler
[upgrade/prepull] Prepulled image for component kube-scheduler.
[upgrade/prepull] Successfully prepulled the images for all the control plane components
I1031 16:18:17.653778   31033 apply.go:202] [upgrade/apply] performing upgrade
I1031 16:18:17.653785   31033 apply.go:268] checking if cluster is self-hosted
[upgrade/apply] Upgrading your Static Pod-hosted control plane to version "v1.12.10"...
I1031 16:18:17.845963   31033 request.go:530] Throttling request took 184.620923ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods/kube-apiserver-172.27.32.165
Static pod: kube-apiserver-172.27.32.165 hash: c5c5b18e12d5e605ef55d516c4559ba0
I1031 16:18:18.045736   31033 request.go:530] Throttling request took 193.159946ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods/kube-controller-manager-172.27.32.165
Static pod: kube-controller-manager-172.27.32.165 hash: 6e79e209a8bc468fa21969e807be68e3
I1031 16:18:18.245404   31033 request.go:530] Throttling request took 197.471715ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods/kube-scheduler-172.27.32.165
Static pod: kube-scheduler-172.27.32.165 hash: dcb7e042ad7733f6f04068629eb4b8b9
[upgrade/staticpods] Writing new Static Pod manifests to "/etc/kubernetes/tmp/kubeadm-upgraded-manifests040725233"
I1031 16:18:18.247454   31033 manifests.go:44] [controlplane] creating static pod files
I1031 16:18:18.247469   31033 manifests.go:117] [controlplane] getting StaticPodSpecs
[controlplane] wrote Static Pod manifest for component kube-apiserver to "/etc/kubernetes/tmp/kubeadm-upgraded-manifests040725233/kube-apiserver.yaml"
[controlplane] wrote Static Pod manifest for component kube-controller-manager to "/etc/kubernetes/tmp/kubeadm-upgraded-manifests040725233/kube-controller-manager.yaml"
[controlplane] wrote Static Pod manifest for component kube-scheduler to "/etc/kubernetes/tmp/kubeadm-upgraded-manifests040725233/kube-scheduler.yaml"
[upgrade/staticpods] Moved new manifest to "/etc/kubernetes/manifests/kube-apiserver.yaml" and backed up old manifest to "/etc/kubernetes/tmp/kubeadm-backup-manifests-2019-10-31-16-18-17/kube-apiserver.yaml"
[upgrade/staticpods] Waiting for the kubelet to restart the component
[upgrade/staticpods] This might take a minute or longer depending on the component/version gap (timeout 5m0s
I1031 16:18:18.446010   31033 request.go:530] Throttling request took 178.44808ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods/kube-apiserver-172.27.32.165
Static pod: kube-apiserver-172.27.32.165 hash: 7d9abb385d9679f7575617a4e03828be
I1031 16:18:18.648914   31033 request.go:530] Throttling request took 200.383408ms, request: GET:https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=component%3Dkube-apiserver
[apiclient] Error getting Pods with label selector "component=kube-apiserver" [Get https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=component%3Dkube-apiserver: dial tcp 172.27.32.165:6443: connect: connection refused]
[apiclient] Error getting Pods with label selector "component=kube-apiserver" [Get https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=component%3Dkube-apiserver: dial tcp 172.27.32.165:6443: connect: connection refused]
[apiclient] Error getting Pods with label selector "component=kube-apiserver" [Get https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=component%3Dkube-apiserver: dial tcp 172.27.32.165:6443: connect: connection refused]
[apiclient] Error getting Pods with label selector "component=kube-apiserver" [Get https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=component%3Dkube-apiserver: dial tcp 172.27.32.165:6443: connect: connection refused]
[apiclient] Error getting Pods with label selector "component=kube-apiserver" [Get https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=component%3Dkube-apiserver: dial tcp 172.27.32.165:6443: connect: connection refused]
[apiclient] Error getting Pods with label selector "component=kube-apiserver" [Get https://172.27.32.165:6443/api/v1/namespaces/kube-system/pods?labelSelector=component%3Dkube-apiserver: net/http: TLS handshake timeout]
[apiclient] Found 1 Pods for label selector component=kube-apiserver
[upgrade/staticpods] Component "kube-apiserver" upgraded successfully!
[upgrade/staticpods] Moved new manifest to "/etc/kubernetes/manifests/kube-controller-manager.yaml" and backed up old manifest to "/etc/kubernetes/tmp/kubeadm-backup-manifests-2019-10-31-16-18-17/kube-controller-manager.yaml"
[upgrade/staticpods] Waiting for the kubelet to restart the component
[upgrade/staticpods] This might take a minute or longer depending on the component/version gap (timeout 5m0s
Static pod: kube-controller-manager-172.27.32.165 hash: 6e79e209a8bc468fa21969e807be68e3
Static pod: kube-controller-manager-172.27.32.165 hash: a9ef5d96e631ef6bb37aa7399b39ce31
[apiclient] Found 1 Pods for label selector component=kube-controller-manager
[upgrade/staticpods] Component "kube-controller-manager" upgraded successfully!
[upgrade/staticpods] Moved new manifest to "/etc/kubernetes/manifests/kube-scheduler.yaml" and backed up old manifest to "/etc/kubernetes/tmp/kubeadm-backup-manifests-2019-10-31-16-18-17/kube-scheduler.yaml"
[upgrade/staticpods] Waiting for the kubelet to restart the component
[upgrade/staticpods] This might take a minute or longer depending on the component/version gap (timeout 5m0s
Static pod: kube-scheduler-172.27.32.165 hash: dcb7e042ad7733f6f04068629eb4b8b9
Static pod: kube-scheduler-172.27.32.165 hash: 92d30ca7866fe98c3147c1f8f4c3d413
[apiclient] Found 1 Pods for label selector component=kube-scheduler
[upgrade/staticpods] Component "kube-scheduler" upgraded successfully!
I1031 16:18:47.231899   31033 apply.go:208] [upgrade/postupgrade] upgrading RBAC rules and addons
[uploadconfig] storing the configuration used in ConfigMap "kubeadm-config" in the "kube-system" Namespace
[kubelet] Creating a ConfigMap "kubelet-config-1.12" in namespace kube-system with the configuration for the kubelets in the cluster
[kubelet] Downloading configuration for the kubelet from the "kubelet-config-1.12" ConfigMap in the kube-system namespace
[kubelet] Writing kubelet configuration to file "/var/lib/kubelet/config.yaml"
[patchnode] Uploading the CRI Socket information "/var/run/dockershim.sock" to the Node API object "172.27.32.165" as an annotation
[bootstraptoken] configured RBAC rules to allow Node Bootstrap tokens to post CSRs in order for nodes to get long term certificate credentials
[bootstraptoken] configured RBAC rules to allow the csrapprover controller automatically approve CSRs from a Node Bootstrap Token
[bootstraptoken] configured RBAC rules to allow certificate rotation for all node client certificates in the cluster
I1031 16:18:47.794738   31033 clusterinfo.go:79] creating the RBAC rules for exposing the cluster-info ConfigMap in the kube-public namespace
I1031 16:18:47.849852   31033 request.go:530] Throttling request took 50.242056ms, request: POST:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/namespaces/kube-public/rolebindings
I1031 16:18:48.049867   31033 request.go:530] Throttling request took 195.937473ms, request: PUT:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/namespaces/kube-public/rolebindings/kubeadm:bootstrap-signer-clusterinfo
I1031 16:18:48.249312   31033 request.go:530] Throttling request took 189.877158ms, request: POST:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/clusterroles
I1031 16:18:48.449307   31033 request.go:530] Throttling request took 195.86853ms, request: PUT:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/clusterroles/system:coredns
I1031 16:18:48.650121   31033 request.go:530] Throttling request took 198.286357ms, request: POST:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/clusterrolebindings
I1031 16:18:48.849300   31033 request.go:530] Throttling request took 196.19422ms, request: PUT:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/clusterrolebindings/system:coredns
[addons] Applied essential addon: CoreDNS
I1031 16:18:49.049271   31033 request.go:530] Throttling request took 146.459988ms, request: POST:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/clusterrolebindings
I1031 16:18:49.249379   31033 request.go:530] Throttling request took 195.347278ms, request: PUT:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/clusterrolebindings/kubeadm:node-proxier
I1031 16:18:49.449396   31033 request.go:530] Throttling request took 198.120697ms, request: POST:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/namespaces/kube-system/roles
I1031 16:18:49.649555   31033 request.go:530] Throttling request took 197.170914ms, request: POST:https://172.27.32.165:6443/apis/rbac.authorization.k8s.io/v1/namespaces/kube-system/rolebindings
[addons] Applied essential addon: kube-proxy

[upgrade/successful] SUCCESS! Your cluster was upgraded to "v1.12.10". Enjoy!

[upgrade/kubelet] Now that your control plane is upgraded, please proceed with upgrading your kubelets if you haven't already done so.
```

升级成功后升级 kubectl：    
```shell
# upgrade kubectl
yum upgrade -y  kubectl-1.12.10 --disableexcludes=kubernetes
```

## 升级 kubelet
逐台节点升级 kubelet。    
升级前最好先备份下当前kubelet的配置：    
```shell
cp /usr/lib/systemd/system/kubelet.service.d/10-kubeadm.conf 10-kubeadm.conf.bak
```
```shell
# upgrade kubelet/kubeadm
yum upgrade -y  kubelet-1.12.10 kubeadm-1.12.10 --disableexcludes=kubernetes
# kubeadm upgrade node config
kubeadm upgrade node config --kubelet-version $(kubelet --version | cut -d ' ' -f 2)'
# restart
systemctl daemon-reload
systemctl restart kubelet
```

至此升级完成，可以执行`kubectl get nodes`，进行验证，是否所有 node 都正常启动。    
