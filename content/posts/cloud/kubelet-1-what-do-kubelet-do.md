---
title: "Kubelet-1 Kubelet 会做些什么"
author: "Maoqide"
tags: ["cloud", "kubernetes", "source-code"]
date: 2019-07-14T11:30:24+08:00
# draft: true
---

Kubelet 是 Kubernetes 集群中非常重要的组件，起在集群中的每个几点上，具体 Kubelet 会做那些事情，可以通过 Kubelet 的源码找到答案。    
<!--more-->

本文的 Kubelet 源码基于 Kubernetes-1.14。    
```golang
// k8s.io\kubernetes\pkg\kubelet\kubelet.go
func (kl *Kubelet) Run(updates <-chan kubetypes.PodUpdate) {}
	kl.initializeModules()
		// Prometheus metrics.
		metrics.Register(
			kl.runtimeCache,
			collectors.NewVolumeStatsCollector(kl),
			collectors.NewLogMetricsCollector(kl.StatsProvider.ListPodStats),
		)
		metrics.SetNodeName(kl.nodeName)
		// TODO: 1.!!! 
		// Start async garbage collection of images.
		kl.imageManager.Start()

		// TODO: 2.!!!!!! 
		// Watches cadvisor for system oom's and records an event for every system oom encountered.
		kl.oomWatcher.Start(kl.nodeRef)

		kl.resourceAnalyzer.Start()
			// updateCachedPodVolumeStats calculates and caches the PodVolumeStats for every Pod known to the kubelet.
			go wait.Forever(func() { s.updateCachedPodVolumeStats() }, s.calcPeriod)

	// TODO: 3.!!!!!
	// VolumeManager runs a set of asynchronous loops that figure out which
	// volumes need to be attached/mounted/unmounted/detached based on the pods
	// scheduled on this node and makes it so.
	go kl.volumeManager.Run(kl.sourcesReady, wait.NeverStop)

		// DesiredStateOfWorldPopulator periodically loops through the list of active
		// pods and ensures that each one exists in the desired state of the world cache
		// if it has volumes. It also verifies that the pods in the desired state of the
		// world cache still exist, if not, it removes them.
		go vm.desiredStateOfWorldPopulator.Run(sourcesReady, stopCh)

		// Reconciler runs a periodic loop to reconcile the desired state of the world
		// with the actual state of the world by triggering attach, detach, mount, and
		// unmount operations.
		go vm.reconciler.Run(stopCh)

	// TODO:important. 4.!!!!!!!!!! 
	// Start syncing node status immediately, this may set up things the runtime needs to run.
	go wait.Until(kl.syncNodeStatus, kl.nodeStatusUpdateFrequency, wait.NeverStop)
		// syncNodeStatus should be called periodically from a goroutine.
		// It synchronizes node status to master if there is any change or enough time
		// passed from the last sync, registering the kubelet first if necessary.
		func (kl *Kubelet) syncNodeStatus() {}
			kl.registerWithAPIServer()
			// updateNodeStatus updates node status to master with retries if there is any
			// change or enough time passed from the last sync.
			kl.updateNodeStatus()
				// In large clusters, GET and PUT operations on Node objects coming
				// from here are the majority of load on apiserver and etcd.
				// To reduce the load on etcd, we are serving GET operations from
				// apiserver cache (the data might be slightly delayed but it doesn't
				// seem to cause more conflict - the delays are pretty small).
				// If it result in a conflict, all retries are served directly from etcd.
				tryUpdateNodeStatus()
	// fastStatusUpdateOnce starts a loop that checks the internal node indexer cache for when a CIDR
	// is applied  and tries to update pod CIDR immediately. After pod CIDR is updated it fires off
	// a runtime update and a node status update. Function returns after one successful node status update.
	// Function is executed only during Kubelet start which improves latency to ready node by updating
	// pod CIDR, runtime status and node statuses ASAP.
	go kl.fastStatusUpdateOnce()
		// ....................
		// 不断尝试更新 CIDR，成功后，直接调用 syncNodeStatus() 更新 node 状态.
		if node.Spec.PodCIDR != "" {
			if _, err := kl.updatePodCIDR(node.Spec.PodCIDR); err != nil {
				klog.Errorf("Pod CIDR update failed %v", err)
				continue
			}
			kl.updateRuntimeUp()
			kl.syncNodeStatus()
			return
		}

	// start syncing lease
	// create or update lease periodically
	if utilfeature.DefaultFeatureGate.Enabled(features.NodeLease) {
		go kl.nodeLeaseController.Run(wait.NeverStop)
	}

	// TODO:important. 5.!!!!!!!!! 
	// updateRuntimeUp calls the container runtime status callback, 
	// initializing the runtime dependent modules when the container runtime first comes up,
	// and returns an error if the status check fails.  If the status check is OK,
	// update the container runtime uptime in the kubelet runtimeState.
	go wait.Until(kl.updateRuntimeUp, 5*time.Second, wait.NeverStop)
		func (kl *Kubelet) updateRuntimeUp() {}
			kl.containerRuntime.Status()
			initializeRuntimeDependentModules() {}
				kl.cadvisor.Start()
				// get nodeinfo or initilized.
				kl.getNodeAnyWay()
				// 
				kl.containerManager.Start(node, kl.GetActivePods, kl.sourcesReady, kl.statusManager, kl.runtimeService)
					cm.cpuManager.Start(cpumanager.ActivePodsFunc(activePods), podStatusProvider, runtimeService)
					cm.setupNode(activePods)
					// Start starts the Device Plugin Manager and start initialization of
					// podDevices and allocatedDevices information from checkpointed state and
					// starts device plugin registration service.
					cm.deviceManager.Start(devicemanager.ActivePodsFunc(activePods), sourcesReady)
					// TODO: important. 6 !!!!!! 
					// Start starts the control loop to observe and response to low compute resources.
					kl.evictionManager.Start(kl.StatsProvider, kl.GetActivePods, kl.podResourcesAreReclaimed, evictionMonitoringPeriod)
				// Needed to observe and respond to situations that could impact node stability
				kl.containerLogManager.Start()
				if kl.enablePluginsWatcher {
					// Adding Registration Callback function for CSI Driver
					kl.pluginWatcher.AddHandler(pluginwatcherapi.CSIPlugin, pluginwatcher.PluginHandler(csi.PluginHandler))
					// Adding Registration Callback function for Device Manager
					kl.pluginWatcher.AddHandler(pluginwatcherapi.DevicePlugin, kl.containerManager.GetPluginRegistrationHandler())
					// Start the plugin watcher
					klog.V(4).Infof("starting watcher")
					err := kl.pluginWatcher.Start()


	// Start loop to sync iptables util rules
	if kl.makeIPTablesUtilChains {
		// syncNetworkUtil ensures the network utility are present on host.
		// Network util includes:
		// 1. 	In nat table, KUBE-MARK-DROP rule to mark connections for dropping
		// 	Marked connection will be drop on INPUT/OUTPUT Chain in filter table
		// 2. 	In nat table, KUBE-MARK-MASQ rule to mark connections for SNAT
		// 	Marked connection will get SNAT on POSTROUTING Chain in nat table
		go wait.Until(kl.syncNetworkUtil, 1*time.Minute, wait.NeverStop)
	}

	// podKiller launches a goroutine to kill a pod received from the channel if
	// another goroutine isn't already in action.
	go wait.Until(kl.podKiller, 1*time.Second, wait.NeverStop)

	// Syncs pods statuses with apiserver; also used as a cache of statuses.
	// case syncRequest := <-m.podStatusChannel: syncPod(syncRequest)
	// case <-syncTicker: m.syncBatch() 
	kl.statusManager.Start()

	// TODO: 7.!!!! 
	// pod probe
	kl.probeManager.Start()

	// ...
	go kl.runtimeClassManager.Run(wait.NeverStop)

	// TODO: 8.!!!!
	// Start the pod lifecycle event generator.
	kl.pleg.Start()
		// Get all the pods. 
		// g.runtime.GetPods(true)
		// kube
		// pods := kubecontainer.Pods(podList)
		// Compare the old and the current pods, and generate events.
		// computeEvents
		// If there are events associated with a pod, we should update the podCache.
		go wait.Until(g.relist, g.relistPeriod, wait.NeverStop)
			// relist queries the container runtime for list of pods/containers, compare
			// with the internal pods/containers, and generates events accordingly.
			func (g *GenericPLEG) relist() {}


	// TODO:important. 9.!!!!!!!
	// syncLoop is the main loop for processing changes. It watches for changes from
	// three channels (file, apiserver, and http) and creates a union of them. For
	// any new change seen, will run a sync against desired state and running state. If
	// no changes are seen to the configuration, will synchronize the last known desired
	// state every sync-frequency seconds. Never returns.
	kl.syncLoop(updates, kl)
		kl.syncLoopIteration(updates, handler, syncTicker.C, housekeepingTicker.C, plegCh)
```

首先，Kubelet 的代码入口在`k8s.io/kubernetes/cmd/kubelet/kubelet.go`, 暂时略过一系列的参数校验，结构体构建及初始化操作，直接看`k8s.io/kubernetes/cmdkubelet/app/server.go`中最关键的`startKubelet`方法, 这个方法中调用了 Kubelet 的 `func (kl *Kubelet) Run(updates <-chan kubetypes.PodUpdate) {}`方法，Kubelet 具体做的事情，几乎都可以在这个方法中找到，接下来主要以此方法为入口，分析 Kubelet 启动执行的动作。     

### initializeModules
此方法源码中的注释为`initializeModules will initialize internal modules that do not require the container runtime to be up. Note that the modules here must not depend on modules that are not initialized here.`，即初始化不需要启动容器运行时的内部模块，并且不依赖于尚未初始化的模块。主要包含的有：prometheus metrics 的采集模块，创建目录（如：pod目录，kubelet root 目录，pod 日志目录等）， 启动 imageManager（负责镜像gc），启动serverCertificateManager（证书更新），启动 oomWatcher（监听oom并记录事件），启动 resourceAnalyzer。    

### volumeManager
goroutine 启动 volumeManager，保证调度到本节点的 pod 的 volume 执行正确的 mount 或 unmount 等操作。volumeManager 会启动两个 goroutine `desiredStateOfWorldPopulator`和`reconciler`。`desiredStateOfWorldPopulator` 通过两个方法`findAndAddNewPods`和`findAndRemoveDeletedPods`遍历节点上所有 pod，对新添加的和已删除的 pod 执行 volume 操作；`reconciler`包含两种 cache，`desiredStateOfWorld`和`actualStateOfWorld`，启动 reconciler 会遍历 cache 中的所有 volume，通过执行对应的 mount/unmount 操作来保证实际的 volume 状态和预期的相同。     

### syncNodeStatus
接下来，kubelet 会执行`syncNodeStatus`进行节点状态同步，这时会做好启动运行时所需要的配置。`syncNodeStatus`方法在节点有任何变化，或距上次同步一定时间后，向 master 同步本节点的状态，在必要时会首先向 master 进行注册（注册即将当前节点信息提交给 apiserver）。`syncNodeStatus`会调用`tryUpdateNodeStatus`尝试更新，`tryUpdateNodeStatus`方法在尝试更新节点状态时，首先会尝试从 apiserver 缓存中获取信息，当获取到的信息发生冲突时，会重新尝试直接获取 etcd 的数据并重新尝试同步。（在大规模集群中，节点状态同步中所调用的 GET 和 PUT 方法，是 apiserver 和 etcd 负载的主要来源，为了减小负载，tryUpdateNodeStatus 调用的 GET 方法优先从缓存中获取）。    

### fastStatusUpdateOnce
在 kubelet 启动时，还会调用一个`fastStatusUpdateOnce`，该方法会调用不断尝试更新 pod CIDR，一旦更新成功，会立即执行`updateRuntimeUp`和`syncNodeStatus`来进行运行时的更新和节点状态更新。此方法只在 Kubelet 启动时会执行，目的是为了通过更新 pod CIDR，减少节点达到 ready 状态的时延，尽可能快的进行 runtime update 和 node status update。     

### nodeLeaseController
`nodeLeaseController` 非常简单，它是一个无限循环，为 Kubelet 声明并定时更新对节点的租约。    

### updateRuntimeUp
`updateRuntimeUp`调用容器运行时状态回调，当容器运行时首次启动时初始化运行时依赖的模块，如果状态检测 ok，在 kubelet 的`runtimeState`中更新容器运行时的启动时间。updateRuntimeUp 方法首先调用`containerRuntime.Status()`获取容器运行时状态，当状态ok后，会调用`initializeRuntimeDependentModules`方法，初始化并运行 kubelet 中需要依赖容器运行时的模块。包括 containerManager、evictionManager、containerLogManager、pluginWatcher等。关于这几个模块，通过名字应该基本可以猜测到大概的功能，后面再做详细的分析。    

### syncNetworkUtil
设置 iptables 规则，配置`KUBE-MARK-DROP`和`KUBE-MARK-MASQ`规则。     

### podKiller
podKiller 从 kubelet 的`podKillingCh` channel 中接受并启动一个 goroutine 来 kill pod，kill 之前会先判断该 pod 是否已经有其他 goroutine 在执行 kill。    
### statusManager
statusManager 和 apiserver 同步 pod 状态，同时也被用作状态的缓存。    

### probeManager
probeManager 处理 pod 的探针，并根据结果更新 pod 状态。    

### pleg
pleg 是 PodLifecycleEventGenerator，即 pod 生命周期时间生成器。它周期性的执行 relist 方法，查询容器运行时来查询 pod/container 列表，和内部的 pod/container 列表作比对，并由此生成事件。    

### syncLoop
最后，进入 syncLoop，即 kubelet 的主循环。syncLoop 从三个 channel 监听变化（file，apiserver，http），并将他们合并。对于发现的任何改变，kubelet 针对期望状态和实际运行状态作同步，如果没有变化，就在一定同步周期内，和上次发现的期望状态同步，永远不会退出。

### syncLoopIteration
syncLoop 中 执行 syncLoopIteration 方法进行真正的同步操作。具体代码在`pkg/kubelet/kubelet.go`中，逻辑较复杂，后面单独分析。        