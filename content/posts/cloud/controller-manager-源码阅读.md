---
title: "Controller Manager 源码阅读"
date: "2019-02-23T16:52:30+08:00"
author: "Maoqide"
tags: ["cloud", "kubernetes", "source-code"]
draft: false
---

k8s controller-manager 源码阅读笔记 
<!--more-->

## 代码结构
	本部分用于记录 kube-controller-manager 代码整体结构及关键方法，便于到源码中查找，个人阅读记录，读者可跳过。本文所有代码均基于 kubernetes release-1.13。        
```golang
// cmd/kube-controller-manager/controller-manager.go
	main()
		command := app.NewControllerManagerCommand()

// cmd/kube-controller-manager/app/controllermanager.go
	NewControllerManagerCommand()
		/*
		**	指定 port，所有默认 port 在 pkg/master/ports/ports.go 这个文件中
		**	将默认配置传入 Options，设置每个 controller 基础配置（证书，同步间隔...）
		**	设置 gcIgnoredResources
		**	var ignoredResources = map[schema.GroupResource]struct{}{
		**		{Group: "", Resource: "events"}: {},
		**	}
		*/
		NewKubeControllerManagerOptions()		// creates a new KubeControllerManagerOptions with a default config.
		cmd := &cobra.Command{
			// ...

			Run: func (cmd *cobra.Command, args []string) {}
				//...

				s.Config(KnownControllers(), ControllersDisabledByDefault.List())
				// ControllersDisabledByDefault = sets.NewString("bootstrapsigner", "tokencleaner",)
					s.Validate(allControllers, disabledByDefaultControllers)	// validate all controllers options and config
					client, err := clientset.NewForConfig(restclient.AddUserAgent(kubeconfig, KubeControllerManagerUserAgent))
					leaderElectionClient := clientset.NewForConfigOrDie(restclient.AddUserAgent(&config, "leader-election"))
					// an EventRecorder can be used to send events to this EventBroadcaster
					// with the event source set to the given event source.
					eventRecorder := createRecorder(client, KubeControllerManagerUserAgent)
						func createRecorder(kubeClient clientset.Interface, userAgent string) record.EventRecorder {}
							eventBroadcaster.StartRecordingToSink(&v1core.EventSinkImpl{Interface: kubeClient.CoreV1().Events("")})
							return eventBroadcaster.NewRecorder(clientgokubescheme.Scheme, v1.EventSource{Component: userAgent})
					c := &kubecontrollerconfig.Config{
						Client:               client,
						Kubeconfig:           kubeconfig,
						EventRecorder:        eventRecorder,
						LeaderElectionClient: leaderElectionClient,
					}				
				KnownControllers()
					// NewControllerInitializers is a public map of named controller groups (you can start more than one in an init func)
					// paired to their InitFunc. 
					NewControllerInitializers(loopMode ControllerLoopMode) map[string]InitFunc {}
						controllers["endpoint"] = startEndpointController
						controllers["replicationcontroller"] = startReplicationController
						controllers["podgc"] = startPodGCController
						controllers["resourcequota"] = startResourceQuotaController
						controllers["namespace"] = startNamespaceController
						controllers["serviceaccount"] = startServiceAccountController
						controllers["garbagecollector"] = startGarbageCollectorController
						controllers["daemonset"] = startDaemonSetController
						controllers["job"] = startJobController
						controllers["deployment"] = startDeploymentController
						controllers["replicaset"] = startReplicaSetController
						controllers["horizontalpodautoscaling"] = startHPAController
						controllers["disruption"] = startDisruptionController
						controllers["statefulset"] = startStatefulSetController
						controllers["cronjob"] = startCronJobController
						controllers["csrsigning"] = startCSRSigningController
						controllers["csrapproving"] = startCSRApprovingController
						controllers["csrcleaner"] = startCSRCleanerController
						controllers["ttl"] = startTTLController
						controllers["bootstrapsigner"] = startBootstrapSignerController
						controllers["tokencleaner"] = startTokenCleanerController
						controllers["nodeipam"] = startNodeIpamController
						controllers["nodelifecycle"] = startNodeLifecycleController
						controllers["persistentvolume-binder"] = startPersistentVolumeBinderController
						controllers["attachdetach"] = startAttachDetachController
						controllers["persistentvolume-expander"] = startVolumeExpandController
						controllers["clusterrole-aggregation"] = startClusterRoleAggregrationController
						controllers["pvc-protection"] = startPVCProtectionController
						controllers["pv-protection"] = startPVProtectionController
						controllers["ttl-after-finished"] = startTTLAfterFinishedController
						controllers["root-ca-cert-publisher"] = startRootCACertPublisher
				Run(c.Complete(), wait.NeverStop)
					configz.New(ConfigzName)	// ConfigzName="kubecontrollermanager.config.k8s.io"
					// Start the controller manager HTTP server. insecure as example.
					unsecuredMux = genericcontrollermanager.NewBaseHandler(&c.ComponentConfig.Generic.Debugging, checks...)
					insecureSuperuserAuthn := server.AuthenticationInfo{Authenticator: &server.InsecureSuperuser{}}
					handler := genericcontrollermanager.BuildHandlerChain(unsecuredMux, nil, &insecureSuperuserAuthn)
					InsecureServing.Serve(handler, 0, stopCh)
						RunServer(insecureServer, s.Listener, shutdownTimeout, stopCh)
					run := func(ctx context.Context) {}
						rootClientBuilder := controller.SimpleControllerClientBuilder{
							ClientConfig: c.Kubeconfig,
						}
						controllerContext, err := CreateControllerContext(c, rootClientBuilder, clientBuilder, ctx.Done())
						// CreateControllerContext creates a context struct containing references to resources needed by the
						// controllers such as the cloud provider and clientBuilder. rootClientBuilder is only used for
						// the shared-informers client and token controller.
						func CreateControllerContext(s *config.CompletedConfig, rootClientBuilder, clientBuilder controller.ControllerClientBuilder, stop <-chan struct{}) (ControllerContext, error) {}
							versionedClient := rootClientBuilder.ClientOrDie("shared-informers")
							sharedInformers := informers.NewSharedInformerFactory(versionedClient, ResyncPeriod(s)())
							
							// If apiserver is not running we should wait for some time and fail only then. This is particularly
							// important when we start apiserver and controller manager at the same time.
							genericcontrollermanager.WaitForAPIServer(versionedClient, 10*time.Second)
							// returns the supported resources for all groups and versions, by request "/apis/......."
							availableResources, err := GetAvailableResources(rootClientBuilder)
							ctx := ControllerContext{
								ClientBuilder:      clientBuilder,
								InformerFactory:    sharedInformers,
								ComponentConfig:    s.ComponentConfig,
								RESTMapper:         restMapper,
								AvailableResources: availableResources,
								Cloud:              cloud,
								LoopMode:           loopMode,
								Stop:               stop,
								InformersStarted:   make(chan struct{}),
								ResyncPeriod:       ResyncPeriod(s),
							}

						// serviceAccountTokenControllerStarter is special because it must run first to set up permissions for other controllers.
						// It cannot use the "normal" client builder, so it tracks its own. It must also avoid being included in the "normal"
						// init map so that it can always run first.
						saTokenControllerInitFunc := serviceAccountTokenControllerStarter{rootClientBuilder: rootClientBuilder}.startServiceAccountTokenController
						startServiceAccountTokenController() {}
							// 获取相关证书
							// ...

							controller, err := serviceaccountcontroller.NewTokensController(
								ctx.InformerFactory.Core().V1().ServiceAccounts(),
								ctx.InformerFactory.Core().V1().Secrets(),
								c.rootClientBuilder.ClientOrDie("tokens-controller"),
								serviceaccountcontroller.TokensControllerOptions{
									TokenGenerator: tokenGenerator,
									RootCA:         rootCA,
								},
							)
							NewTokensController() {}	// watch queueServiceAccountSync event 和 queueSecretSync event

						StartControllers(controllerContext, saTokenControllerInitFunc, NewControllerInitializers(controllerContext.LoopMode), unsecuredMux)
							startSATokenController(ctx)	// 先启动 SATokenController
							for controllerName, initFn := range controllers {
								IsControllerEnabled	// 判断是否启用 controller
								// Jitter returns a time.Duration between duration and duration + maxFactor * duration.
								// This allows clients to avoid converging on periodic behavior. If maxFactor
								// is 0.0, a suggested default value will be chosen.
								time.Sleep(wait.Jitter(ctx.ComponentConfig.Generic.ControllerStartInterval.Duration, ControllerStartJitter))
								debugHandler, started, err := initFn(ctx)
								// 
								if debugHandler != nil && unsecuredMux != nil {
									basePath := "/debug/controllers/" + controllerName
									unsecuredMux.UnlistedHandle(basePath, http.StripPrefix(basePath, debugHandler))
									unsecuredMux.UnlistedHandlePrefix(basePath+"/", http.StripPrefix(basePath, debugHandler))
								}
							}
						controllerContext.InformerFactory.Start(controllerContext.Stop)

						// InformersStarted is closed after all of the controllers have been initialized and are running.  After this point it is safe,
						// for an individual controller to start the shared informers. Before it is closed, they should not.
						close(controllerContext.InformersStarted)	// !!!!!
				
					// leader 选举，通过获取锁成为 leader
					leaderelection.RunOrDie(context.TODO(), leaderelection.LeaderElectionConfig{
						Lock:          rl,
						// ... ...
						Callbacks: leaderelection.LeaderCallbacks{
							OnStartedLeading: run,
							OnStoppedLeading: func() {
								klog.Fatalf("leaderelection lost")
							},
						},
						WatchDog: electionChecker,
						Name:     "kube-controller-manager",
					})
		}
```

## cmd.Run
目前的 kubernetes 组件全都采用 [cobra](https://github.com/spf13/cobra) 构建。核心的启动流程都在生成的 `cobra.Command` 实例 `cmd` 的 `Run()` 方法中。    
`Run` 方法执行了两个方法，`s.Config(KnownControllers(), ControllersDisabledByDefault.List())`, `Run(c.Complete(), wait.NeverStop)`。    

## s.Config(KnownControllers(), ControllersDisabledByDefault.List())
`KnownControllers()` 方法调用了 `NewControllerInitializers()`, 生成一个 `map[string]InitFunc{}` 的map，保存了 controller 和对应的启动方法的映射。`s.Config` 方法返回了 controller-manager 的配置，首先对所有 controllers 进行 validate，然后会构建一个 k8s clientset 和 一个 `EventRecorder` 对象，具体事件记录的方式，会在后面分析。    
```golang
// EventRecorder knows how to record events on behalf of an EventSource.
// an EventRecorder can be used to send events to this EventBroadcaster
// with the event source set to the given event source.
type EventRecorder interface {
	// Event constructs an event from the given information and puts it in the queue for sending.
	// The resulting event will be created in the same namespace as the reference object.
	Event(object runtime.Object, eventtype, reason, message string)

	// Eventf is just like Event, but with Sprintf for the message field.
	Eventf(object runtime.Object, eventtype, reason, messageFmt string, args ...interface{})

	// PastEventf is just like Eventf, but with an option to specify the event's 'timestamp' field.
	PastEventf(object runtime.Object, timestamp metav1.Time, eventtype, reason, messageFmt string, args ...interface{})

	// AnnotatedEventf is just like eventf, but with annotations attached
	AnnotatedEventf(object runtime.Object, annotations map[string]string, eventtype, reason, messageFmt string, args ...interface{})
}
```

## Run(c.Complete(), wait.NeverStop)
首先`configz.New(ConfigzName)`生成 controller-manager 的配置对象，用名称`kubecontrollermanager.config.k8s.io`注册到注册到路由`/configz`上，可以直接通过 controller-manager 的地址访问到。接着，会新建一个 BaseHandler 实例并启动 HTTP server，用来注册 controller manager 的 `/metric` 和 `/healthz` 接口。接下来，定义了一个内部方法`run()`, 启动 controller-manager 的主要操作，都在这个方法中完成。    
`run()`方法首先创建一个`ControllerContext`, 结构体如下，主要包含 controllers 所需要资源的引用，如 kubernetes 的 clientset 和informer。AvailableResources 由`GetAvailableResources`方法获取，通过 apiserver 的`/api/...`接口获取集群支持的所有 group 和 version 资源。然后开始启动 controllers，在启动其他 controller 前，一定先启动 SATokenController，因为它必须先为其他 controller 创建所需的 token 授权，所以启动`SATokenController`的方法独立于启动其他 controller 的循环之外，作为最先启动的一个。`startServiceAccountTokenController` watch 了`ServiceAccount`和`secret`的增删改事件，并同步本地的 queue 缓存。接下来才会调用`StartControllers`方法依次调用其他 controller 的 `InitFunc` 启动 controllers。最后启动 `controllerContext` 的 InformerFactory 并执行`close(controllerContext.InformersStarted)`。这里的`controllerContext.InformersStarted`是`chan struct{}`类型，当这个 channel 被关闭了，代表所有 controllers 都被初始化并运行起来了，独立的 controller 应该在他关闭后再启动 sharedInformer。    
```golang
type ControllerContext struct {
	// ClientBuilder will provide a client for this controller to use
	ClientBuilder controller.ControllerClientBuilder

	// InformerFactory gives access to informers for the controller.
	InformerFactory informers.SharedInformerFactory

	// ComponentConfig provides access to init options for a given controller
	ComponentConfig kubectrlmgrconfig.KubeControllerManagerConfiguration

	// DeferredDiscoveryRESTMapper is a RESTMapper that will defer
	// initialization of the RESTMapper until the first mapping is
	// requested.
	RESTMapper *restmapper.DeferredDiscoveryRESTMapper

	// AvailableResources is a map listing currently available resources
	AvailableResources map[schema.GroupVersionResource]bool

	// Cloud is the cloud provider interface for the controllers to use.
	// It must be initialized and ready to use.
	Cloud cloudprovider.Interface

	// Control for which control loops to be run
	// IncludeCloudLoops is for a kube-controller-manager running all loops
	// ExternalLoops is for a kube-controller-manager running with a cloud-controller-manager
	LoopMode ControllerLoopMode

	// Stop is the stop channel
	Stop <-chan struct{}

	// InformersStarted is closed after all of the controllers have been initialized and are running.  After this point it is safe,
	// for an individual controller to start the shared informers. Before it is closed, they should not.
	InformersStarted chan struct{}

	// ResyncPeriod generates a duration each time it is invoked; this is so that
	// multiple controllers don't get into lock-step and all hammer the apiserver
	// with list requests simultaneously.
	ResyncPeriod func() time.Duration
}
```
最后，会执行`leaderelection.RunOrDie`方法不断尝试获取或更新(`tryAcquireOrRenew`) leader lease，成功获取到的即为 leader，并执行上面的`run()`方法。实际上就是去获取一个锁并有一定有效期，当一个 contoller-manager 实例获取到锁并且超出了有效期，那么这个实例就会成为leader，成为 leader 的实例仍然会不断执行`tryAcquireOrRenew`来更新获取时间`AcquireTime`以延长有效期。(leader 选举的逻辑在 k8s.io\client-go\tools\leaderelection\leaderelection.go)    

## controllers
上面就是 controller-manager 的整体启动流程和代码结构。接下来会具体分析几个核心的 controller。    

### replicasetcontroller
kubernetes\pkg\controller\replicaset\replica_set.go