---
title: "Apiserver 源码阅读"
date: "2018-11-21T19:46:06+08:00"
author: "Maoqide"
tags: ["cloud", "kubernetes", "source-code"]
draft: false
---

k8s apiserver 源码阅读笔记 
<!--more--> 
## 代码结构
	本部分用于记录 apiserver 代码整体结构及关键方法，便于到源码中查找，个人阅读记录，读者可跳过。本文所有代码均基于 kubernetes 1.9.6。
```golang
app.Run()
	CreateServerChain()
		CreateNodeDialer()	//ssh 连接
		CreateKubeAPIServerConfig()	//
			defaultOptions()
				DefaultAdvertiseAddress()
				DefaultServiceIPRange()
				MaybeDefaultWithSelfSignedCerts()
				ApplyAuthorization()
				IsValidServiceAccountKeyFile()
			Validate() //validate options
			BuildGenericConfig()	//takes the master server options and produces the genericapiserver.Config associated with it
				genericConfig
				genericConfig.OpenAPIConfig //config swagger
				BuildStorageFactory()		//constructs the storage factory

					func NewStorageFactory(storageConfig storagebackend.Config, defaultMediaType string, serializer runtime.StorageSerializer,
						defaultResourceEncoding *serverstorage.DefaultResourceEncodingConfig, storageEncodingOverrides map[string]schema.GroupVersion, resourceEncodingOverrides []schema.GroupVersionResource,
						defaultAPIResourceConfig *serverstorage.ResourceConfig, resourceConfigOverrides utilflag.ConfigurationMap) (*serverstorage.DefaultStorageFactory, error)

						// storageConfig -> ETCD配置
						// defaultAPIResourceConfig ->
						func DefaultAPIResourceConfigSource() *serverstorage.ResourceConfig
							type ResourceConfig struct {
								GroupVersionResourceConfigs map[schema.GroupVersion]*GroupVersionResourceConfig
							}
							func (o *ResourceConfig) EnableVersions(versions ...schema.GroupVersion)		//Enable GroupVersion
							func (o *ResourceConfig) EnableResources(resources ...schema.GroupVersionResource)    //daemonsets,deployments,ingresses,networkpolicies,replicasets,podsecuritypolicies

							// Specifies the overrides for various API group versions.
							// This can be used to enable/disable entire group versions or specific resources.
							type GroupVersionResourceConfig struct {
								// Whether to enable or disable this entire group version.  This dominates any enablement check.
								// Enable=true means the group version is enabled, and EnabledResources/DisabledResources are considered.
								// Enable=false means the group version is disabled, and EnabledResources/DisabledResources are not considered.
								Enable bool

								// DisabledResources lists the resources that are specifically disabled for a group/version
								// DisabledResources trumps EnabledResources
								DisabledResources sets.String

								// EnabledResources lists the resources that should be enabled by default.  This is a little
								// unusual, but we need it for compatibility with old code for now.  An empty set means
								// enable all, a non-empty set means that all other resources are disabled.
								EnabledResources sets.String
							}
					EtcdServersOverrides //override etcd配置
				client, err := internalclientset.NewForConfig(genericConfig.LoopbackClientConfig) // new a loopback client
				sharedInformers := informers.NewSharedInformerFactory(client, 10*time.Minute)	
					// SharedInformerFactory provides shared informers for resources in all known API group versions.
					type SharedInformerFactory interface {
						internalinterfaces.SharedInformerFactory
						ForResource(resource schema.GroupVersionResource) (GenericInformer, error)
						WaitForCacheSync(stopCh <-chan struct{}) map[reflect.Type]bool

						Admissionregistration() admissionregistration.Interface
						Apps() apps.Interface
						Autoscaling() autoscaling.Interface
						Batch() batch.Interface
						Certificates() certificates.Interface
						Core() core.Interface
						Extensions() extensions.Interface
						Networking() networking.Interface
						Policy() policy.Interface
						Rbac() rbac.Interface
						Scheduling() scheduling.Interface
						Settings() settings.Interface
						Storage() storage.Interface
					}
				serviceResolver
					// A ServiceResolver knows how to get a URL given a service.
					type ServiceResolver interface {
						ResolveEndpoint(namespace, name string) (*url.URL, error)
					}

			DefaultServiceIPRange()
			BuildStorageFactory()
			readCAorNil()	//auth CA

			config := &master.Config{}
				type Config struct {
					GenericConfig *genericapiserver.Config
					ExtraConfig   ExtraConfig
				}
		createAPIExtensionsConfig()
		createAPIExtensionsServer() // apiextensions-apiserver\pkg\apiserver\apiserver.go New() is the function for CustomResourceDefinitions to register router handler on GenericAPIServer
		CreateKubeAPIServer() // creates and wires a workable kube-apiserver,
			// returns a new instance of Master from the given config
			func (c completedConfig) New(delegationTarget genericapiserver.DelegationTarget) (*Master, error){} // goproject\src\k8s.io\kubernetes\pkg\master\master.go
				c.GenericConfig.New("kube-apiserver", delegationTarget)	// creates a new server which logically combines the handling chain with the passed server   !! important
					apiServerHandler := NewAPIServerHandler(name, c.RequestContextMapper, c.Serializer, handlerChainBuilder, delegationTarget.UnprotectedHandler())
						// k8s.io\apiserver\pkg\server\handler.go construct gorestfulContainer and add default handler(NotFoundHandler, RecoverHandler, ServiceErrorHandler)
						func NewAPIServerHandler(name string, contextMapper request.RequestContextMapper, s runtime.NegotiatedSerializer, handlerChainBuilder HandlerChainBuilderFn, notFoundHandler http.Handler) *APIServerHandler {}
							director := director{...}
								type director struct {
									name               string
									goRestfulContainer *restful.Container
									nonGoRestfulMux    *mux.PathRecorderMux
								}
								func (d director) ServeHTTP(w http.ResponseWriter, req *http.Request) {}
					s := &GenericAPIServer{}	// k8s.io\apiserver\pkg\server\genericapiserver.go type GenericAPIServer
					add PostStartHooks & PreShutdownHooks
					AddPostStartHook(PostStartHookFunc)	//	{c.SharedInformerFactory.Start(context.StopCh)}
					add healthzChecks
					installAPI(s, c.Config)		// install utils routes like SwaggerUI, Profiling, Metrics
				if () routes.DefaultMetrics{}.Install(s.Handler.NonGoRestfulMux)
				if () routes.Logs{}.Install(s.Handler.GoRestfulContainer)
				m := &Master{ GenericAPIServer: s, }
				m.InstallLegacyAPI(&c, c.GenericConfig.RESTOptionsGetter, legacyRESTStorageProvider)	// k8s.io\kubernetes\pkg\master\master.go, install core api routes, !!!!important 
					NewLegacyRESTStorage() -> //定义如下 返回 LegacyRESTStorage和APIGroupInfo, Storage保存了具体资源对象的结构，如 PodStrorage
						// LegacyRESTStorage returns stateful information about particular instances of REST storage to master.go for wiring controllers
						func (c LegacyRESTStorageProvider) NewLegacyRESTStorage(restOptionsGetter generic.RESTOptionsGetter) (LegacyRESTStorage, genericapiserver.APIGroupInfo, error) {} // k8s.io\kubernetes\pkg\registry\core\rest\storage_core.go
							// Info about an API group.
							type APIGroupInfo struct {
								GroupMeta apimachinery.GroupMeta
								// Info about the resources in this group. Its a map from version to resource to the storage.
								VersionedResourcesStorageMap map[string]map[string]rest.Storage	// !!! important!!!!
								// OptionsExternalVersion controls the APIVersion used for common objects in the
								// schema like api.Status, api.DeleteOptions, and metav1.ListOptions. Other implementors may
								// define a version "v1beta1" but want to use the Kubernetes "v1" internal objects.
								// If nil, defaults to groupMeta.GroupVersion.
								// TODO: Remove this when https://github.com/kubernetes/kubernetes/issues/19018 is fixed.
								OptionsExternalVersion *schema.GroupVersion
								// MetaGroupVersion defaults to "meta.k8s.io/v1" and is the scheme group version used to decode
								// common API implementations like ListOptions. Future changes will allow this to vary by group
								// version (for when the inevitable meta/v2 group emerges).
								MetaGroupVersion *schema.GroupVersion

								// Scheme includes all of the types used by this group and how to convert between them (or
								// to convert objects from outside of this group that are accepted in this API).
								// TODO: replace with interfaces
								Scheme *runtime.Scheme
								// NegotiatedSerializer controls how this group encodes and decodes data
								NegotiatedSerializer runtime.NegotiatedSerializer
								// ParameterCodec performs conversions for query parameters passed to API calls
								ParameterCodec runtime.ParameterCodec
							}
							restStorage := LegacyRESTStorage{}
							// NewREST for basic resources
							podTemplateStorage := podtemplatestore.NewREST(restOptionsGetter)
							eventStorage := eventstore.NewREST(restOptionsGetter, uint64(c.EventTTL.Seconds()))
							limitRangeStorage := limitrangestore.NewREST(restOptionsGetter)
							resourceQuotaStorage, resourceQuotaStatusStorage := resourcequotastore.NewREST(restOptionsGetter)
							secretStorage := secretstore.NewREST(restOptionsGetter)
							serviceAccountStorage := serviceaccountstore.NewREST(restOptionsGetter)
							persistentVolumeStorage, persistentVolumeStatusStorage := pvstore.NewREST(restOptionsGetter)
							persistentVolumeClaimStorage, persistentVolumeClaimStatusStorage := pvcstore.NewREST(restOptionsGetter)
							configMapStorage := configmapstore.NewREST(restOptionsGetter)
							namespaceStorage, namespaceStatusStorage, namespaceFinalizeStorage := namespacestore.NewREST(restOptionsGetter)
		
							endpointsStorage := endpointsstore.NewREST(restOptionsGetter)
							endpointRegistry := endpoint.NewRegistry(endpointsStorage)
							podStorage := podstore.NewStorage()
							serviceRESTStorage, serviceStatusStorage := servicestore.NewREST(restOptionsGetter)
							serviceRegistry := service.NewRegistry(serviceRESTStorage)

							restStorageMap := map[string]rest.Storage{
								"pods":             podStorage.Pod,
								"pods/attach":      podStorage.Attach,
								// ...............
								"configMaps":                    configMapStorage,
								"componentStatuses": componentstatus.NewStorage(componentStatusStorage{c.StorageFactory}.serversToValidate),
							}
							apiGroupInfo.VersionedResourcesStorageMap["v1"] = restStorageMap // set APIGroupInfo.VersionedResourcesStorageMap to return, !!!!!
					
					// construct BootstrapController and add hook
					NewBootstrapController()	// a controller for watching the core capabilities of the master
					AddPostStartHookOrDie() 	// { controller.start() }
					AddPreShutdownHookOrDie()   // { controller.stop() }

					InstallLegacyAPIGroup()
						func (s *GenericAPIServer) InstallLegacyAPIGroup(apiPrefix string, apiGroupInfo *APIGroupInfo) error {}
							if legacyAPIGroupPrefixes.Has(apiPrefix)
							installAPIResources()	// a private method for installing the REST storage backing each api groupversionresource
								for apiGroupInfo.GroupMeta.GroupVersions {
									// get rest.Storage from apiGroupInfo.VersionedResourcesStorageMap[groupVersion.Version]
									apiGroupVersion := s.getAPIGroupVersion(apiGroupInfo, groupVersion, apiPrefix)
									// InstallREST registers the REST handlers (storage, watch, proxy and redirect) into a restful Container
									apiGroupVersion.InstallREST(s.Handler.GoRestfulContainer)
										installer := &APIInstaller{ group: g,...}
										installer.Install()
											// Install handlers for API resources. k8s.io\apiserver\pkg\endpoints\installer.go
											func (a *APIInstaller) Install() ([]metav1.APIResource, *restful.WebService, []error) {}
												paths := make([]string, len(a.group.Storage))
												for paths(storages) {
													apiResource, err := a.registerResourceHandlers(path, a.group.Storage[path], ws, proxyHandler)	
														// !!important(700+ lines...), function to actually add route to go-restful. k8s.io\apiserver\pkg\endpoints\installer.go
														// kubernetes把所有对资源对象的操作接口封装到一个action对象中，在 registerResourceHandlers 方法中，
														// 根据如 storage.(rest.Getter)的方法，获取 what verbs are supported by the storage, used to know what verbs we support per path，
														// 根据scope: RESTScopeNameRoot(Handle non-namespace scoped resources like nodes) 或 RESTScopeNameNamespace(Handler for standard REST verbs (GET, PUT, POST and DELETE))
														// 将 action append 到一个 actions 切片中(不同 scope ，path前缀不同)
														// 最后遍历actions，根据不同的action.Verb，注册到go-restful的 restful.WebService中，并将此对象支持的Verbs将入到apiResource.Verbs中并返回apiResource对象。
														func (a *APIInstaller) registerResourceHandlers(path string, storage rest.Storage, ws *restful.WebService, proxyHandler http.Handler) (*metav1.APIResource, error) {}
															// Struct capturing information about an action ("GET", "POST", "WATCH", "PROXY", etc).
															type action struct {
																Verb          string               // Verb identifying the action ("GET", "POST", "WATCH", "PROXY", etc).
																Path          string               // The path of the action
																Params        []*restful.Parameter // List of parameters associated with the action.
																Namer         handlers.ScopeNamer
																AllNamespaces bool // true iff the action is namespaced but works on aggregate result for all namespaces
															}
															// APIResource specifies the name of a resource and whether it is namespaced.
															type APIResource struct {
																// name is the plural name of the resource.
																Name string `json:"name" protobuf:"bytes,1,opt,name=name"`
																// singularName is the singular name of the resource.  This allows clients to handle plural and singular opaquely.
																// The singularName is more correct for reporting status on a single item and both singular and plural are allowed
																// from the kubectl CLI interface.
																SingularName string `json:"singularName" protobuf:"bytes,6,opt,name=singularName"`
																// namespaced indicates if a resource is namespaced or not.
																Namespaced bool `json:"namespaced" protobuf:"varint,2,opt,name=namespaced"`
																// group is the preferred group of the resource.  Empty implies the group of the containing resource list.
																// For subresources, this may have a different value, for example: Scale".
																Group string `json:"group,omitempty" protobuf:"bytes,8,opt,name=group"`
																// version is the preferred version of the resource.  Empty implies the version of the containing resource list
																// For subresources, this may have a different value, for example: v1 (while inside a v1beta1 version of the core resource's group)".
																Version string `json:"version,omitempty" protobuf:"bytes,9,opt,name=version"`
																// kind is the kind for the resource (e.g. 'Foo' is the kind for a resource 'foo')
																Kind string `json:"kind" protobuf:"bytes,3,opt,name=kind"`
																// verbs is a list of supported kube verbs (this includes get, list, watch, create,
																// update, patch, delete, deletecollection, and proxy)
																Verbs Verbs `json:"verbs" protobuf:"bytes,4,opt,name=verbs"`
																// shortNames is a list of suggested short names of the resource.
																ShortNames []string `json:"shortNames,omitempty" protobuf:"bytes,5,rep,name=shortNames"`
																// categories is a list of the grouped resources this resource belongs to (e.g. 'all')
																Categories []string `json:"categories,omitempty" protobuf:"bytes,7,rep,name=categories"`
															}
													apiResources = append(apiResources, *apiResource)
												}
								}
				m.InstallAPIs(c.ExtraConfig.APIResourceConfigSource, c.GenericConfig.RESTOptionsGetter, restStorageProviders...)	// InstallAPIs will install the APIs for the restStorageProviders if they are enabled.
					for restStorageProviders {
						apiGroupsInfo = append(apiGroupsInfo, apiGroupInfo)
					}
					for i := range apiGroupsInfo {
						m.GenericAPIServer.InstallAPIGroup(&apiGroupsInfo[i])
							// installAPIResources is a private method for installing the REST storage backing each api groupversionresource, k8s.io\apiserver\pkg\server\genericapiserver.go
							func (s *GenericAPIServer) installAPIResources(apiPrefix string, apiGroupInfo *APIGroupInfo) error {}
								// ！！InstallREST registers the REST handlers (storage, watch, proxy and redirect) into a restful Container, k8s.io\apiserver\pkg\endpoints\groupversion.go
								apiGroupVersion.InstallREST(s.Handler.GoRestfulContainer
					}
				m.installTunneler(c.ExtraConfig.Tunneler, corev1client.NewForConfigOrDie(c.GenericConfig.LoopbackClientConfig).Nodes())
				m.GenericAPIServer.AddPostStartHookOrDie("ca-registration", c.ExtraConfig.ClientCARegistrationHook.PostStartHook)
			AddPostStartHook()		// addfunc {sharedInformers.Start(context.StopCh)}
		// openapi swagger
		// this wires up openapi
		kubeAPIServer.GenericAPIServer.PrepareRun()
		// This will wire up openapi for extension api server
		apiExtensionsServer.GenericAPIServer.PrepareRun()
		aggregatorConfig, err := createAggregatorConfig(*kubeAPIServerConfig.GenericConfig, runOptions, versionedInformers, serviceResolver, proxyTransport)
		aggregatorServer, err := createAggregatorServer(aggregatorConfig, kubeAPIServer.GenericAPIServer, apiExtensionsServer.Informers)
			aggregatorServer, err := aggregatorConfig.Complete().NewWithDelegate(delegateAPIServer)
				genericServer, err := c.GenericConfig.New("kube-aggregator", delegationTarget) // ----same function with called in CreateKubeAPIServer->New() (91)
				apiregistrationClient, err := internalclientset.NewForConfig(c.GenericConfig.LoopbackClientConfig)
					configShallowCopy.RateLimiter = flowcontrol.NewTokenBucketRateLimiter(configShallowCopy.QPS, configShallowCopy.Burst)
					cs.apiregistration, err = apiregistrationinternalversion.NewForConfig(&configShallowCopy)
					cs.DiscoveryClient, err = discovery.NewDiscoveryClientForConfig(&configShallowCopy)
					informerFactory := informers.NewSharedInformerFactory(apiregistrationClient,5*time.Minute,)
					s := &APIAggregator{}	// APIAggregator contains state for a Kubernetes cluster master/api server.
					v1beta1storage := map[string]rest.Storage{}
					apiServiceREST := apiservicestorage.NewREST(Scheme, c.GenericConfig.RESTOptionsGetter)
					v1beta1storage["apiservices"] = apiServiceREST
					v1beta1storage["apiservices/status"] = apiservicestorage.NewStatusREST(Scheme, apiServiceREST)
					// rest implements a RESTStorage for API services against etcd
					type REST struct {
						*genericregistry.Store
					}
					apiGroupInfo.VersionedResourcesStorageMap["v1beta1"] = v1beta1storage
					s.GenericAPIServer.InstallAPIGroup(&apiGroupInfo)		// ----same function with called in CreateKubeAPIServer->New()->InstallAPIs() (237)
					s.GenericAPIServer.Handler.NonGoRestfulMux.Handle("/apis", apisHandler)
					s.GenericAPIServer.Handler.NonGoRestfulMux.UnlistedHandle("/apis/", apisHandler)
					apiserviceRegistrationController := NewAPIServiceRegistrationController(informerFactory.Apiregistration().InternalVersion().APIServices(), c.GenericConfig.SharedInformerFactory.Core().V1().Services(), s) // add event handler to informer
					s.GenericAPIServer.AddPostStartHook("start-kube-aggregator-informers")
					s.GenericAPIServer.AddPostStartHook("apiservice-registration-controller")
					s.GenericAPIServer.AddPostStartHook("apiservice-status-available-controller")
					// BuildAndRegisterAggregator registered OpenAPI aggregator handler. 
					openAPIAggregator, err := openapicontroller.BuildAndRegisterAggregator()
			// create controllers for auto-registration
			apiRegistrationClient, err := apiregistrationclient.NewForConfig(aggregatorConfig.GenericConfig.LoopbackClientConfig)
			// ......
```

## app.Run
kubernetes所有组件的入口，基本上都是在`$GOPATH\k8s.io\kubernetes\cmd\xxx(组件名称)`下面的main文件中。
apiserver对应的路径为`$GOPATH\k8s.io\kubernetes\cmd\kube-apiserver\apiserver.go`，main函数中通过`app.Run(s, stopCh)`方法，执行具体逻辑。
具体Run方法，定义在`$GOPATH\k8s.io\kubernetes\cmd\kube-apiserver\app\server.go`中。

apiserver的`app.Run()`，主要通过 `CreateServerChain()` 方法，创建出一个`*genericapiserver.GenericAPIServer`实例。    
在`GenericAPIServer`中，包含的主要结构体有

- `*APIServerHandler`(*Handler holds the handlers being used by this API server*)    
- `DelegationTarget`(*delegationTarget is the next delegate in the chain or nil*)    
其中最重要的是`APIServerHandler`这个结构体，它包含了go-restful中的`*restful.Container`结构体，后面注册API时用到的`InstallAPIs()`方法，最终也是将路由注册到这个Container中，定义如下:
```golang
// APIServerHandlers holds the different http.Handlers used by the API server.
// This includes the full handler chain, the director (which chooses between gorestful and nonGoRestful,
// the gorestful handler (used for the API) which falls through to the nonGoRestful handler on unregistered paths,
// and the nonGoRestful handler (which can contain a fallthrough of its own)
// FullHandlerChain -> Director -> {GoRestfulContainer,NonGoRestfulMux} based on inspection of registered web services
type APIServerHandler struct {
	// FullHandlerChain is the one that is eventually served with.  It should include the full filter
	// chain and then call the Director.
	FullHandlerChain http.Handler
	// The registered APIs.  InstallAPIs uses this.  Other servers probably shouldn't access this directly.
	GoRestfulContainer *restful.Container
	// NonGoRestfulMux is the final HTTP handler in the chain.
	// It comes after all filters and the API handling
	// This is where other servers can attach handler to various parts of the chain.
	NonGoRestfulMux *mux.PathRecorderMux
	// Other servers should only use this opaquely to delegate to an API server.
	Director http.Handler
}
```
`DelegationTarget`(*DelegationTarget is an interface which allows for composition of API servers with top level handling that works as expected.*)是一个`interface`，是构成方法名`CreateServerChain`中ServerChain的结构，结构体内定义了`NextDelegate()`方法，返回chain中的下一个`DelegationTarget`，由它串起了多个api servers。(为什么会有多个api server从后面代码中可以看到。)    

## CreateServerChain
```golang
// CreateServerChain creates the apiservers connected via delegation.
func CreateServerChain(runOptions *options.ServerRunOptions, stopCh <-chan struct{}) (*genericapiserver.GenericAPIServer, error) {}
```
`CreateServerChain()`方法中，先后执行了`CreateNodeDialer`, `CreateKubeAPIServerConfig`, `createAPIExtensionsConfig`, `createAPIExtensionsServer`, `CreateKubeAPIServer`, `createAggregatorConfig`, `createAggregatorServer`几个方法，根据方法名可以看出启动apiserver的流程。

- `CreateNodeDialer`(*CreateNodeDialer creates the dialer infrastructure to connect to the nodes*), add SSH Key, 返回一个`tunneler.Tunneler`, 可以通过创建到node节点的SSH连接。

- `CreateKubeAPIServerConfig`(*creates all the resources for running the API server, but runs none of them*), 创建出所有apiserver所需的配置和资源，包括配置的Validate，命令行参数解析，openapi/swagger配置，StorageFactory,clientset, informer, serviceResolver 等资源的创建。

- `createAPIExtensionsConfig`, 传入由上一步生成的配置`*kubeAPIServerConfig.GenericConfig`和 informer, 通过`apiextensionscmd.NewCRDRESTOptionsGetter(etcdOptions)`初始化`ExtraConfig.CRDRESTOptionsGetter`并创建 apiextensionsConfig 返回。

- `createAPIExtensionsServer`, 通过上一步生成的`apiExtensionsConfig`，通过一个`genericapiserver.EmptyDelegate`创建 apiExtensionsServer。返回 apiserver 的是一个`apiextensionsapiserver.CustomResourceDefinitions`结构体。其中生成 CustomResourceDefinitions 结构体的 New() 方法，真正将 CRD 接口添加到`apiGroupInfo.VersionedResourcesStorageMap`中，并注册到 go-resetful 的 webService，同时会通过`AddPostStartHook`添加启动后hook，启动informer(事件监听)和`crdController`, `namingController`, `finalizingController`三个 Controler 监听 CRD Resource 的变化。

- `CreateKubeAPIServer`(*creates and wires a workable kube-apiserver*), 通过以上几步生成的 apiserver 配置，通过`createAPIExtensionsServer`生成的`DelegationTarget`创建 apiserver 实例(*master.Master*)。这个过程中会 install kubernetes 的 core api 并 启动 BootStrapController(*a controller for watching the core capabilities of the master*),  install nodeTunneler 并添加`ca-registration`的 PostStartHook。    

- `createAggregatorConfig`, 通过上面生成的 apiserver 配置生成 AggregatorConfig。(代码中只是浅拷贝一份`kubeAPIServerConfig.GenericConfig`并添加了 Proxy 相关的 ExtraConfig 到返回的`*aggregatorapiserver.Config`结构体中。)

- `createAggregatorServer`, 生成 AggregatorServer(*Aggregator for Kubernetes-style API servers: dynamic registration, discovery summarization, secure proxy
*)。这个过程中，会启动`apiserviceRegistrationController`, `availableController` 去监听 api service 资源，完成 api service 的发现和注册。    

这里解释一下 aggregator, 这是 kubernetes 为了增强 apiserver 的扩展性，方便用户开发自己的 api服务而开发的机制。它允许k8s的开发人员编写一个自己的服务，可以把这个服务注册到k8s的api里面，这样，就像k8s自己的api一样，你的服务只要运行在k8s集群里面，k8s 的Aggregate通过service名称就可以转发到你写的service里面去了。   
>Aggregated（聚合的）API server是为了将原来的API server这个巨石（monolithic）应用给拆分成，为了方便用户开发自己的API server集成进来，而不用直接修改kubernetes官方仓库的代码，这样一来也能将API server解耦，方便用户使用实验特性。这些API server可以跟core API server无缝衔接，使用kubectl也可以管理它们。

到这里， apiserver的启动就基本完成了。    
下面主要分析下以上几个流程中`CreateKubeAPIServerConfig`和`CreateKubeAPIServer`两个方法，这也是创建出核心的apiserver 和真正执行k8s core api 注册的过程。

## CreateKubeAPIServerConfig
```golang
kubeAPIServerConfig, sharedInformers, versionedInformers, insecureServingOptions, serviceResolver, err := CreateKubeAPIServerConfig(runOptions, nodeTunneler, proxyTransport)

// CreateKubeAPIServerConfig creates all the resources for running the API server, but runs none of them
func CreateKubeAPIServerConfig(s *options.ServerRunOptions, nodeTunneler tunneler.Tunneler, proxyTransport *http.Transport) (*master.Config, informers.SharedInformerFactory, clientgoinformers.SharedInformerFactory, *kubeserver.InsecureServingInfo, aggregatorapiserver.ServiceResolver, error) {}
```
方法的注释是 创建为了运行API server所需的所有资源，但是不会运行。就是说，这个方法负责创建后面启动的apiserver所需的所有配置及相关类的初始化。通过返回参数看，这些资源至少包括apiserver的配置, `SharedInformerFactory`(*provides shared informers for resources in all known API group versions*), `InsecureServingInfo`(*is required to serve http.  HTTP does NOT include authentication or authorization.*), `ServiceResolver`(*knows how to get a URL given a service*)。    

### 主要流程
CreateKubeAPIServerConfig 首先是通过 `defaultOptions` 方法 在创建真正的 apiserver配置前将 options 中的参数以默认值补全，并对参数进行`Validate`, 然后通过`BuildGenericConfig`方法，根据 options 创建`*genericapiserver.Config`, 同时 `SharedInformer`和`ServiceResolver`都是在这个方法中创建的。
`BuildGenericConfig`方法中调用了很多`ApplyTo`方法，作用是将 options 中的各项配置参数解析到生成的config中, 在这个方法中还创建了`[]admission.PluginInitializer`。    
在这之后还有一个重要的方法是`BuildStorageFactory`，创建StorageFactory的时候需要传入 etcd 相关的配置。`Storage`是apiserver中一个很重要的概念，通过它执行对具体资源对象的操作，如对 POD 的 CRUD 等操作就是通过 `PodStorage`对象进行并连接到后端的 etcd 的。（同时 Storage 也是和 对应资源对象的 API 对应，后面installAPI的时候也是通过 Storage 来注册 API 路由的。）    
最后，配置默认的ServiceIPRange 和 获取 CA 证书等配置，将上面创建的配置注入一个`&master.Config`实例并返回。

### ServiceResolver
ServiceResolver的定义及创建方法如下，通过 SharedInformer 的 lister 方法监听 kubernetes Service 资源的变化，实现获取 Service 的 URL 的功能。
```golang
serviceResolver = aggregatorapiserver.NewClusterIPServiceResolver(
			versionedInformers.Core().V1().Services().Lister(),
		)

// A ServiceResolver knows how to get a URL given a service.
type ServiceResolver interface {
	ResolveEndpoint(namespace, name string) (*url.URL, error)
}
```

### SharedInformer
CreateKubeAPIServerConfig 返回两个`SharedInformerFactory`, 实际上结构体的定义完全相同，区别是定义在不同的包内，`informers.SharedInformerFactory`定义在 kubernetes 内部的pkg下，而`clientgoinformers.SharedInformerFactory`定义在 client-go 中，因此创建的时候，前者是通过`internalclientset`创建出的clientset创建，而后者是通过client-go的clientset创建，用来创建两者的配置是完全相同的。(第一次阅读，比较疑惑为什么需要两个clientset。猜测是一个用来内部通信，一个是用来外部通信。后面有时间的话，会再具体研究下。)     
`SharedInformerFactory`定义如下：
```golang
// SharedInformerFactory provides shared informers for resources in all known
// API group versions.
type SharedInformerFactory interface {
	internalinterfaces.SharedInformerFactory
	ForResource(resource schema.GroupVersionResource) (GenericInformer, error)
	WaitForCacheSync(stopCh <-chan struct{}) map[reflect.Type]bool

	Admissionregistration() admissionregistration.Interface
	Apps() apps.Interface
	Autoscaling() autoscaling.Interface
	Batch() batch.Interface
	Certificates() certificates.Interface
	Core() core.Interface
	Extensions() extensions.Interface
	Networking() networking.Interface
	Policy() policy.Interface
	Rbac() rbac.Interface
	Scheduling() scheduling.Interface
	Settings() settings.Interface
	Storage() storage.Interface
}
```

SharedInformerFactory为所有API group versions提供shared informers, shared informer又是什么呢？定义如下：
```golang
// SharedInformer has a shared data cache and is capable of distributing notifications for changes
// to the cache to multiple listeners who registered via AddEventHandler. If you use this, there is
// one behavior change compared to a standard Informer.  When you receive a notification, the cache
// will be AT LEAST as fresh as the notification, but it MAY be more fresh.  You should NOT depend
// on the contents of the cache exactly matching the notification you've received in handler
// functions.  If there was a create, followed by a delete, the cache may NOT have your item.  This
// has advantages over the broadcaster since it allows us to share a common cache across many
// controllers. Extending the broadcaster would have required us keep duplicate caches for each
// watch.
type SharedInformer interface {
	// AddEventHandler adds an event handler to the shared informer using the shared informer's resync
	// period.  Events to a single handler are delivered sequentially, but there is no coordination
	// between different handlers.
	AddEventHandler(handler ResourceEventHandler)
	// AddEventHandlerWithResyncPeriod adds an event handler to the shared informer using the
	// specified resync period.  Events to a single handler are delivered sequentially, but there is
	// no coordination between different handlers.
	AddEventHandlerWithResyncPeriod(handler ResourceEventHandler, resyncPeriod time.Duration)
	// GetStore returns the Store.
	GetStore() Store
	// GetController gives back a synthetic interface that "votes" to start the informer
	GetController() Controller
	// Run starts the shared informer, which will be stopped when stopCh is closed.
	Run(stopCh <-chan struct{})
	// HasSynced returns true if the shared informer's store has synced.
	HasSynced() bool
	// LastSyncResourceVersion is the resource version observed when last synced with the underlying
	// store. The value returned is not synchronized with access to the underlying store and is not
	// thread-safe.
	LastSyncResourceVersion() string
}
```
可以通过先两篇文章了解下SharedInformer,
[https://blog.csdn.net/weixin_42663840/article/details/81699303](https://blog.csdn.net/weixin_42663840/article/details/81699303)    
[https://www.kubernetes.org.cn/2693.html](https://www.kubernetes.org.cn/2693.html)    
简单来说，SharedInformer 有一个共享数据的cache, 并能够将 cache 的变化分发给多个 listener, 这些 listener 都是通过 `AddEventHandler` 方法注册到 SharedInformer。Informer 在初始化的时，先调用 Kubernetes List API 到 ETCD获得某种 resource 的全部 Object，缓存在内存中; 然后，调用 Watch API 去 watch 这种 resource，去维护这份缓存; 最后，Informer 就不再调用 Kubernetes 的任何 API。

## CreateKubeAPIServer
```golang
kubeAPIServer, err := CreateKubeAPIServer(kubeAPIServerConfig, apiExtensionsServer.GenericAPIServer, sharedInformers, versionedInformers)

// CreateKubeAPIServer creates and wires a workable kube-apiserver
func CreateKubeAPIServer(kubeAPIServerConfig *master.Config, delegateAPIServer genericapiserver.DelegationTarget, sharedInformers informers.SharedInformerFactory, versionedInformers clientgoinformers.SharedInformerFactory) (*master.Master, error) {}
```
方法的注释 创建并装配一个可工作的 kube-apiserver, 到这里，一个真正可运行的apiserver实例就创建完成了。可以看到返回的 APIServer 类型是`*master.Master`，传入的就是之前CreateKubeAPIServer返回的配置和资源，加上delegateAPIServer。这是kubernetes组合多个 apiserver 的机制。

### 主要流程
生成 kubeAPIServer 的是`kubeAPIServerConfig.Complete(versionedInformers).New(delegateAPIServer)`方法。在这个方法中，又调用了`c.GenericConfig.New("kube-apiserver", delegationTarget)`创建一个APIServer，并生成 Handler chain 和传入的`delegateAPIServer`组合起来；接着会新建`*master.Master`实例 `m`，并将`c.GenericConfig.New` 返回的 APIServer 赋值给 `m.GenericAPIServer`, 这个`m`也是`CreateKubeAPIServer`方法最终要返回的 APISever 实例。最后要做的就是执行`m.InstallLegacyAPI`, `m.InstallAPIs`注册 API 接口，添加 PostStartHook 然后将`m`返回。

### c.GenericConfig.New
```golang
// New creates a new server which logically combines the handling chain with the passed server.
// name is used to differentiate for logging.
func (c completedConfig) New(name string, delegationTarget DelegationTarget) (*GenericAPIServer, error) {}
```
首先通过`apiServerHandler := NewAPIServerHandler(name, c.RequestContextMapper, c.Serializer, handlerChainBuilder, delegationTarget.UnprotectedHandler())`创建出一个`APIServerHandler`实例，结构体定义上面已经贴过了。    
NewAPIServerHandler 方法中，创建了`nonGoRestfulMux`和`gorestfulContainer`, 并给`gorestfulContainer`添加了几个默认Handler(NotFoundHandler, RecoverHandler, ServiceErrorHandler), 再这两者注入到一个 director 实例中，director 有一个 `ServeHTTP`, 用来最终启动 http 服务, 最后将director 赋值给 `APIServerHandler.Director`, 通过调用`c.BuildHandlerChainFunc(director, c.Config)`装饰`director`并赋值给`APIServerHandler.FullHandlerChain`最后返回。    
接着创建一个`GenericAPIServer`实例`s`，并将 NewAPIServerHandler 方法中返回的`apiServerHandler`赋值给`s.Handler`和`s.listedPathProvider`, 将传入的`delegationTarget`(即delegated apiserver) 中配置的 Hooks 和 HealthzCheckers 传递`s`, 并合并`s`和`delegationTarget`的 listedPathProvider(*an interface for providing paths that should be reported at /*), 最后执行`installAPI(s, c.Config)`安装 API 并返回`s`。    

#### director
如下是`BuildHandlerChainFunc`和`*master.Config`中默认的方法，可以看到是不断追加 handler 方法到 Handler 中。    
```golang
// BuildHandlerChainFunc allows you to build custom handler chains by decorating the apiHandler.
BuildHandlerChainFunc func(apiHandler http.Handler, c *Config) (secure http.Handler)

// default BuildHandlerChainFunc
func DefaultBuildHandlerChain(apiHandler http.Handler, c *Config) http.Handler {
	handler := genericapifilters.WithAuthorization(apiHandler, c.RequestContextMapper, c.Authorizer, c.Serializer)
	handler = genericfilters.WithMaxInFlightLimit(handler, c.MaxRequestsInFlight, c.MaxMutatingRequestsInFlight, c.RequestContextMapper, c.LongRunningFunc)
	handler = genericapifilters.WithImpersonation(handler, c.RequestContextMapper, c.Authorizer, c.Serializer)
	if utilfeature.DefaultFeatureGate.Enabled(features.AdvancedAuditing) {
		handler = genericapifilters.WithAudit(handler, c.RequestContextMapper, c.AuditBackend, c.AuditPolicyChecker, c.LongRunningFunc)
	} else {
		handler = genericapifilters.WithLegacyAudit(handler, c.RequestContextMapper, c.LegacyAuditWriter)
	}
	failedHandler := genericapifilters.Unauthorized(c.RequestContextMapper, c.Serializer, c.SupportsBasicAuth)
	if utilfeature.DefaultFeatureGate.Enabled(features.AdvancedAuditing) {
		failedHandler = genericapifilters.WithFailedAuthenticationAudit(failedHandler, c.RequestContextMapper, c.AuditBackend, c.AuditPolicyChecker)
	}
	handler = genericapifilters.WithAuthentication(handler, c.RequestContextMapper, c.Authenticator, failedHandler)
	handler = genericfilters.WithCORS(handler, c.CorsAllowedOriginList, nil, nil, nil, "true")
	handler = genericfilters.WithTimeoutForNonLongRunningRequests(handler, c.RequestContextMapper, c.LongRunningFunc, c.RequestTimeout)
	handler = genericfilters.WithWaitGroup(handler, c.RequestContextMapper, c.LongRunningFunc, c.HandlerChainWaitGroup)
	handler = genericapifilters.WithRequestInfo(handler, c.RequestInfoResolver, c.RequestContextMapper)
	handler = apirequest.WithRequestContext(handler, c.RequestContextMapper)
	handler = genericfilters.WithPanicRecovery(handler)
	return handler
}
```

如下是`director`的定义及`ServeHTTP`方法，先匹配 path 是否是gorestful中的路径，是的话通过`goRestfulContainer.Dispatch(w, req)`分发到对应 handler 处理请求，不匹配的话就通过`nonGoRestfulMux`分发处理。     
```golang
type director struct {
	name               string
	goRestfulContainer *restful.Container
	nonGoRestfulMux    *mux.PathRecorderMux
}

func (d director) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	path := req.URL.Path

	// check to see if our webservices want to claim this path
	for _, ws := range d.goRestfulContainer.RegisteredWebServices() {
		switch {
		case ws.RootPath() == "/apis":
			// if we are exactly /apis or /apis/, then we need special handling in loop.
			// normally these are passed to the nonGoRestfulMux, but if discovery is enabled, it will go directly.
			// We can't rely on a prefix match since /apis matches everything (see the big comment on Director above)
			if path == "/apis" || path == "/apis/" {
				glog.V(5).Infof("%v: %v %q satisfied by gorestful with webservice %v", d.name, req.Method, path, ws.RootPath())
				// don't use servemux here because gorestful servemuxes get messed up when removing webservices
				// TODO fix gorestful, remove TPRs, or stop using gorestful
				d.goRestfulContainer.Dispatch(w, req)
				return
			}

		case strings.HasPrefix(path, ws.RootPath()):
			// ensure an exact match or a path boundary match
			if len(path) == len(ws.RootPath()) || path[len(ws.RootPath())] == '/' {
				glog.V(5).Infof("%v: %v %q satisfied by gorestful with webservice %v", d.name, req.Method, path, ws.RootPath())
				// don't use servemux here because gorestful servemuxes get messed up when removing webservices
				// TODO fix gorestful, remove TPRs, or stop using gorestful
				d.goRestfulContainer.Dispatch(w, req)
				return
			}
		}
	}

	// if we didn't find a match, then we just skip gorestful altogether
	glog.V(5).Infof("%v: %v %q satisfied by nonGoRestful", d.name, req.Method, path)
	d.nonGoRestfulMux.ServeHTTP(w, req)
}
```

#### ListedPathProvider
```golang
// ListedPathProvider is an interface for providing paths that should be reported at /.
type ListedPathProvider interface {
	// ListedPaths is an alphabetically sorted list of paths to be reported at /.
	ListedPaths() []string
}
```

#### installAPI
这里的 installAPI 方法如下，只根据配置安装了 Index, SwaggerUI, Profiling, Metrics 等 API 到 `NonGoRestfulMux`, Version(`/version`) 到 `GoRestfulContainer`, 核心的 API 还没有安装。    


### m.InstallLegacyAPI
```golang
m.InstallLegacyAPI(&c, c.GenericConfig.RESTOptionsGetter, legacyRESTStorageProvider)

func (m *Master) InstallLegacyAPI(c *completedConfig, restOptionsGetter generic.RESTOptionsGetter, legacyRESTStorageProvider corerest.LegacyRESTStorageProvider) {}
```
用于注册`/api`下的 API, 即core api。首先调用`legacyRESTStorageProvider.NewLegacyRESTStorage`创建`legacyRESTStorage`, 如果配置中`EnableCoreControllers`为`True`的话，创建`BootStrapController`并在 `m`的 PostStartHook 和 dPostStartHook 中添加启动和停止。最后执行`m.GenericAPIServer.InstallLegacyAPIGroup`安装 LegacyAPIGroup。

#### NewLegacyRESTStorage
```golang
legacyRESTStorage, apiGroupInfo, err := legacyRESTStorageProvider.NewLegacyRESTStorage(restOptionsGetter)

func (c LegacyRESTStorageProvider) NewLegacyRESTStorage(restOptionsGetter generic.RESTOptionsGetter) (LegacyRESTStorage, genericapiserver.APIGroupInfo, error) {}
```
这个方法返回两个结构体，`LegacyRESTStorage`和`genericapiserver.APIGroupInfo`, 其中最重要的是 APIGroupInfo。APIGroupInfo 中，有一个`VersionedResourcesStorageMap`, 是API 版本到 Storage 资源的 map 关系，保存了不同版本的所有 Storage。下面贴出了两个结构体的定义。
首先会初始化一个 APIGroupInfo 实例`apiGroupInfo`, 接着会调用不同 Storage 资源的`NewREST`方法创建 Storage, 如: `eventStorage`, `configMapStorage`, `namespaceStorage`, `serviceRESTStorage`, `podStorage`等。`NewREST`方法返回一个 REST 结构体, 而 REST 结构体中，保存了`*genericregistry.Store`, 这个 Store 结构体提供了对应资源的 CRUD 等操作的方法，所有对资源的操作通过 Store 来访问到后端的 ETCD。其中 pod, node 和 service 对应的操作比较多，涉及 Status 的存储和更新, 所以 Storage 创建过程也较为复杂。尤其是 pod, 不仅涉及到本身和状态的存储和更新，还涉及到日志 proxy 等操作，所以单独封装了一个 PodStorage 结构体，其中包含了多种不同的 Store, 例如涉及到日志的`LogREST`需要传入 KubeletConnectionInfo, 涉及到 proxy 的 ProxyREST 需要传入 ProxyTransport等，每种 Store 都提供了对应资源的操作方法，如获取日志，建立连接等。这部分代码在`k8s.io\kubernetes\pkg\registry\core\rest\storage_core.go`, 有关 Pod 和 Service 的 Storage 创建及不同 Storage 对应的方法可以看一下。    
最后，所有 Storage 创建完后，会构建一个`restStorageMap`(具体内容会在下面贴出)，这个 map 最后会赋给`apiGroupInfo.VersionedResourcesStorageMap["v1"]`, 即 core API v1版本的所有资源都可以在这个 map 资源中找到。

```golang
// LegacyRESTStorage returns stateful information about particular instances of REST storage to
// master.go for wiring controllers.
// TODO remove this by running the controller as a poststarthook
type LegacyRESTStorage struct {
	ServiceClusterIPAllocator rangeallocation.RangeRegistry
	ServiceNodePortAllocator  rangeallocation.RangeRegistry
}

// Info about an API group.
type APIGroupInfo struct {
	GroupMeta apimachinery.GroupMeta
	// Info about the resources in this group. Its a map from version to resource to the storage.
	VersionedResourcesStorageMap map[string]map[string]rest.Storage
	// OptionsExternalVersion controls the APIVersion used for common objects in the
	// schema like api.Status, api.DeleteOptions, and metav1.ListOptions. Other implementors may
	// define a version "v1beta1" but want to use the Kubernetes "v1" internal objects.
	// If nil, defaults to groupMeta.GroupVersion.
	// TODO: Remove this when https://github.com/kubernetes/kubernetes/issues/19018 is fixed.
	OptionsExternalVersion *schema.GroupVersion
	// MetaGroupVersion defaults to "meta.k8s.io/v1" and is the scheme group version used to decode
	// common API implementations like ListOptions. Future changes will allow this to vary by group
	// version (for when the inevitable meta/v2 group emerges).
	MetaGroupVersion *schema.GroupVersion

	// Scheme includes all of the types used by this group and how to convert between them (or
	// to convert objects from outside of this group that are accepted in this API).
	// TODO: replace with interfaces
	Scheme *runtime.Scheme
	// NegotiatedSerializer controls how this group encodes and decodes data
	NegotiatedSerializer runtime.NegotiatedSerializer
	// ParameterCodec performs conversions for query parameters passed to API calls
	ParameterCodec runtime.ParameterCodec
}
``` 

```golang
// restStorageMap
restStorageMap := map[string]rest.Storage{
	"pods":             podStorage.Pod,
	"pods/attach":      podStorage.Attach,
	"pods/status":      podStorage.Status,
	"pods/log":         podStorage.Log,
	"pods/exec":        podStorage.Exec,
	"pods/portforward": podStorage.PortForward,
	"pods/proxy":       podStorage.Proxy,
	"pods/binding":     podStorage.Binding,
	"bindings":         podStorage.Binding,
	"podTemplates": podTemplateStorage,
	"replicationControllers":        controllerStorage.Controller,
	"replicationControllers/status": controllerStorage.Status,
	"services":        serviceRest.Service,
	"services/proxy":  serviceRest.Proxy,
	"services/status": serviceStatusStorage,
	"endpoints": endpointsStorage,
	"nodes":        nodeStorage.Node,
	"nodes/status": nodeStorage.Status,
	"nodes/proxy":  nodeStorage.Proxy,
	"events": eventStorage,
	"limitRanges":                   limitRangeStorage,
	"resourceQuotas":                resourceQuotaStorage,
	"resourceQuotas/status":         resourceQuotaStatusStorage,
	"namespaces":                    namespaceStorage,
	"namespaces/status":             namespaceStatusStorage,
	"namespaces/finalize":           namespaceFinalizeStorage,
	"secrets":                       secretStorage,
	"serviceAccounts":               serviceAccountStorage,
	"persistentVolumes":             persistentVolumeStorage,
	"persistentVolumes/status":      persistentVolumeStatusStorage,
	"persistentVolumeClaims":        persistentVolumeClaimStorage,
	"persistentVolumeClaims/status": persistentVolumeClaimStatusStorage,
	"configMaps":                    configMapStorage,
	"componentStatuses": componentstatus.NewStorage(componentStatusStorage{c.StorageFactory}.serversToValidate),
}
```

#### InstallLegacyAPIGroup
```golang
m.GenericAPIServer.InstallLegacyAPIGroup(genericapiserver.DefaultLegacyAPIPrefix, &apiGroupInfo)

func (s *GenericAPIServer) InstallLegacyAPIGroup(apiPrefix string, apiGroupInfo *APIGroupInfo) error {
	if !s.legacyAPIGroupPrefixes.Has(apiPrefix) {
		return fmt.Errorf("%q is not in the allowed legacy API prefixes: %v", apiPrefix, s.legacyAPIGroupPrefixes.List())
	}
	if err := s.installAPIResources(apiPrefix, apiGroupInfo); err != nil {
		return err
	}

	// setup discovery
	apiVersions := []string{}
	for _, groupVersion := range apiGroupInfo.GroupMeta.GroupVersions {
		apiVersions = append(apiVersions, groupVersion.Version)
	}
	// Install the version handler.
	// Add a handler at /<apiPrefix> to enumerate the supported api versions.
	s.Handler.GoRestfulContainer.Add(discovery.NewLegacyRootAPIHandler(s.discoveryAddresses, s.Serializer, apiPrefix, apiVersions, s.requestContextMapper).WebService())
	return nil
}
```
整个方法如上，主要两步，首先调用 installAPIResources(*is a private method for installing the REST storage backing each api groupversionresource*) 安装 API。   
installAPIResources 会遍历`apiGroupInfo`下的所有 groupVersion, 然后通过`s.getAPIGroupVersion`得到该 version 下所有的 Storage, 即上面`apiGroupInfo.VersionedResourcesStorageMap[groupVersion.Version]` map 中所对应的所有 Storage。并通过`InstallREST`注册到 REST API 的 Handler 中。InstallREST方法如下，在 `installer.Install()`方法中, 以上面的`restStorageMap`的 key 为 path, 将所有 Storage 通过`registerResourceHandlers`(*具体方法在 k8s.io\apiserver\pkg\endpoints\installer.go, 一个近700行的 swich-case 的方法，有兴趣可以看下。*)方法注册到 gorestful 的 WebService Route中，并返回一个`*metav1.APIResource`对象，Install 方法会返回所有 Storage 的生成的 APIResources 和注册到的 WebService。    
接着获取 GroupVersions 中的所有版本并注册到 `GoRestfulContainer` 中(adds a service to return the supported api versions at the legacy /api), 返回可支持 API 版本。
```golang
// InstallREST registers the REST handlers (storage, watch, proxy and redirect) into a restful Container.
// It is expected that the provided path root prefix will serve all operations. Root MUST NOT end
// in a slash.
func (g *APIGroupVersion) InstallREST(container *restful.Container) error {
	prefix := path.Join(g.Root, g.GroupVersion.Group, g.GroupVersion.Version)
	installer := &APIInstaller{
		group:                        g,
		prefix:                       prefix,
		minRequestTimeout:            g.MinRequestTimeout,
		enableAPIResponseCompression: g.EnableAPIResponseCompression,
	}

	apiResources, ws, registrationErrors := installer.Install()
	versionDiscoveryHandler := discovery.NewAPIVersionHandler(g.Serializer, g.GroupVersion, staticLister{apiResources}, g.Context)
	versionDiscoveryHandler.AddToWebService(ws)
	container.Add(ws)
	return utilerrors.NewAggregate(registrationErrors)
}

// Install handlers for API resources.
func (a *APIInstaller) Install() ([]metav1.APIResource, *restful.WebService, []error) {
	var apiResources []metav1.APIResource
	var errors []error
	ws := a.newWebService()

	proxyHandler := (&handlers.ProxyHandler{
		Prefix:     a.prefix + "/proxy/",
		Storage:    a.group.Storage,
		Serializer: a.group.Serializer,
		Mapper:     a.group.Context,
	})

	// Register the paths in a deterministic (sorted) order to get a deterministic swagger spec.
	paths := make([]string, len(a.group.Storage))
	var i int = 0
	for path := range a.group.Storage {
		paths[i] = path
		i++
	}
	sort.Strings(paths)
	for _, path := range paths {
		apiResource, err := a.registerResourceHandlers(path, a.group.Storage[path], ws, proxyHandler)
		if err != nil {
			errors = append(errors, fmt.Errorf("error in registering resource: %s, %v", path, err))
		}
		if apiResource != nil {
			apiResources = append(apiResources, *apiResource)
		}
	}
	return apiResources, ws, errors
}
```


### m.InstallAPIs
```golang
m.InstallAPIs(c.ExtraConfig.APIResourceConfigSource, c.GenericConfig.RESTOptionsGetter, restStorageProviders...)

// InstallAPIs will install the APIs for the restStorageProviders if they are enabled.
func (m *Master) InstallAPIs(apiResourceConfigSource serverstorage.APIResourceConfigSource, restOptionsGetter generic.RESTOptionsGetter, restStorageProviders ...RESTStorageProvider) {}
```
用于注册`/apis`下的 API。在调用 InstallAPIs 之前，会创建`/apis`下 Storage 的 `RESTStorageProvider`, 该 interface 的定义及创建在下面代码片段`1`贴出。    
每个 RESTStorageProvider, 都会有一个`NewRESTStorage`方法来创建对应资源的 Storage。调用 InstallAPIs 方法时，会将 restStorageProviders 列表传入。
InstallAPIs 会遍历传入的 restStorageProviders 列表，并调用每个 restStorageProvider 的 `NewRESTStorage`。    
`NewRESTStorage`方法, 会新建一个 APIGroupInfo, 然后针对 enable 的 API 版本, 调用 VXXStorage 获取对应版本的 ResourcesStorageMap 并存入 apiGroupInfo.VersionedResourcesStorageMap[VXX]中。用来获取 ResourcesStorageMap 的方法，和上面 InstallLegacyAPIGroup.NewLegacyRESTStorage 方法中一样，也是 `NewREST`, 具体逻辑也基本相同，返回一个 REST 结构体提供对资源的 CRUD 等操作。    
`NewRESTStorage`方法最终返回的 apiGroupInfo, 会被放入一个 apiGroupsInfo 列表，最后会遍历这个列表并针对每一个 apiGroupInfo 执行 `m.GenericAPIServer.InstallAPIGroup(&apiGroupsInfo[i])`, 这部分逻辑和 InstallLegacyAPIGroup 一样，通过调用 installAPIResources 将 API 注册到 GoRestfulContainer 中，详细的可以对照上面的 InstallLegacyAPIGroup 的分析参考源码。

```golang
// 代码片段 1
// RESTStorageProvider is a factory type for REST storage.
type RESTStorageProvider interface {
	GroupName() string
	NewRESTStorage(apiResourceConfigSource serverstorage.APIResourceConfigSource, restOptionsGetter generic.RESTOptionsGetter) (genericapiserver.APIGroupInfo, bool)
}

// The order here is preserved in discovery.
	// If resources with identical names exist in more than one of these groups (e.g. "deployments.apps"" and "deployments.extensions"),
	// the order of this list determines which group an unqualified resource name (e.g. "deployments") should prefer.
	// This priority order is used for local discovery, but it ends up aggregated in `k8s.io/kubernetes/cmd/kube-apiserver/app/aggregator.go
	// with specific priorities.
	// TODO: describe the priority all the way down in the RESTStorageProviders and plumb it back through the various discovery
	// handlers that we have.
	restStorageProviders := []RESTStorageProvider{
		authenticationrest.RESTStorageProvider{Authenticator: c.GenericConfig.Authenticator},
		authorizationrest.RESTStorageProvider{Authorizer: c.GenericConfig.Authorizer, RuleResolver: c.GenericConfig.RuleResolver},
		autoscalingrest.RESTStorageProvider{},
		batchrest.RESTStorageProvider{},
		certificatesrest.RESTStorageProvider{},
		extensionsrest.RESTStorageProvider{},
		networkingrest.RESTStorageProvider{},
		policyrest.RESTStorageProvider{},
		rbacrest.RESTStorageProvider{Authorizer: c.GenericConfig.Authorizer},
		schedulingrest.RESTStorageProvider{},
		settingsrest.RESTStorageProvider{},
		storagerest.RESTStorageProvider{},
		// keep apps after extensions so legacy clients resolve the extensions versions of shared resource names.
		// See https://github.com/kubernetes/kubernetes/issues/42392
		appsrest.RESTStorageProvider{},
		admissionregistrationrest.RESTStorageProvider{},
		eventsrest.RESTStorageProvider{TTL: c.ExtraConfig.EventTTL},
	}
```