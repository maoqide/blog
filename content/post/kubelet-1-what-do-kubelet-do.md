---
title: "Kubelet-1 Kubelet 会做些什么"
author: "Maoqide"
tags: ["cloud", "kubernetes", "source-code"]
date: 2019-06-10T21:30:24+08:00
draft: true
---

Kubelet 是 Kubernetes 集群中非常重要的组件，起在集群中的每个几点上，具体 Kubelet 会做那些事情，可以通过 Kubelet 的源码找到答案。    
<!--more-->

本文的 Kubelet 源码基于 Kubernetes-1.13。    
```golang
k8s.io\kubernetes\pkg\kubelet\kubelet.go
func (kl *Kubelet) Run(updates <-chan kubetypes.PodUpdate) {}
	kl.initializeModules()
		// Start async garbage collection of images.
		kl.imageManager.Start()

		// Watches cadvisor for system oom's and records an event for every system oom encountered.
		kl.oomWatcher.Start(kl.nodeRef)

		kl.resourceAnalyzer.Start()
			// updateCachedPodVolumeStats calculates and caches the PodVolumeStats for every Pod known to the kubelet.
			go wait.Forever(func() { s.updateCachedPodVolumeStats() }, s.calcPeriod)

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

	// It synchronizes node status to master if there is any change or enough time
	// passed from the last sync, registering the kubelet first if necessary.
	go wait.Until(kl.syncNodeStatus, kl.nodeStatusUpdateFrequency, wait.NeverStop)

	// create or update lease periodically
	go kl.nodeLeaseController.Run(wait.NeverStop)

	// updateRuntimeUp calls the container runtime status callback, initializing
	// the runtime dependent modules when the container runtime first comes up,
	// and returns an error if the status check fails.  If the status check is OK,
	// update the container runtime uptime in the kubelet runtimeState.
	go wait.Until(kl.updateRuntimeUp, 5*time.Second, wait.NeverStop)

	// Start loop to sync iptables util rules
	if kl.makeIPTablesUtilChains {
		go wait.Until(kl.syncNetworkUtil, 1*time.Minute, wait.NeverStop)
	}

	// podKiller launches a goroutine to kill a pod received from the channel if
	// another goroutine isn't already in action.
	go wait.Until(kl.podKiller, 1*time.Second, wait.NeverStop)

	// Syncs pods statuses with apiserver; also used as a cache of statuses.
	// case syncRequest := <-m.podStatusChannel: syncPod(syncRequest)
	// case <-syncTicker: m.syncBatch() 
	kl.statusManager.Start()

	// pod probe
	kl.probeManager.Start()

	// ...
	go kl.runtimeClassManager.Run(wait.NeverStop)

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

	// syncLoop is the main loop for processing changes. It watches for changes from
	// three channels (file, apiserver, and http) and creates a union of them. For
	// any new change seen, will run a sync against desired state and running state. If
	// no changes are seen to the configuration, will synchronize the last known desired
	// state every sync-frequency seconds. Never returns.
	kl.syncLoop(updates, kl)
		kl.syncLoopIteration(updates, handler, syncTicker.C, housekeepingTicker.C, plegCh)
```

首先，Kubelet 的代码入口在`k8s.io/kubernetes/cmd/kubelet/kubelet.go`, 暂时略过一系列的参数校验，结构体构建及初始化操作，直接看`k8s.io/kubernetes/cmdkubelet/app/server.go`中最关键的`startKubelet`方法, 这个方法中调用了 Kubelet 的 `func (kl *Kubelet) Run(updates <-chan kubetypes.PodUpdate) {}`方法，Kubelet 具体做的事情，几乎都可以在这个方法中找到。     