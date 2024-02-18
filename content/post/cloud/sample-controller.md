---
title: "Sample Controller"
date: "2019-03-18T12:53:41+08:00"
author: "Maoqide"
tags: ["cloud", "kubernetes", "kubernetes-operator"]
draft: false
---

自己构建 sample-controller.    
<!--more--> 

https://github.com/maoqide/sample-controller    
[https://github.com/kubernetes/sample-controller](https://github.com/kubernetes/sample-controller)    

## 编写 CRD 定义
```
sample-controller
├── hack
│   ├── boilerplate.go.txt
│   ├── custom-boilerplate.go.txt
│   ├── update-codegen.sh
│   └── verify-codegen.sh
└── pkg
    └── apis
        └── samplecontroller
            ├── register.go
            └── v1alpha1
                ├── doc.go
                ├── register.go
                └── types.go
```

首先，项目初始如上结构：    
`hack`目录下的脚本可以复用，主要是调用了 [https://github.com/kubernetes/code-generator](https://github.com/kubernetes/code-generator) 项目中的 `generate-groups.sh` 脚本，code-gengrator 项目 `cmd` 目录下的代码，需要提前`go install`生成对应二进制文件。    
`pkg`目录下的文件，需要自己手动编写，`pkg/apis/samplecontroller`是 CRD 所属的 `apiGroup`，`v1alpha1` 是 `apiVersion`，v1alpha1目录下的`types.go`文件，包含了 CRD 类型 `Foo` 的完整定义。    
`pkg/apis/samplecontroller/register.go`中，定义了后面所需的全局变量。    
`pkg/apis/samplecontroller/v1alpha1/doc.go`中，包含了 `+<tag-name>[=value]` 格式的注释，这就是 Kubernetes 进行源码生成用的 Annotation 风格的注释，doc.go 中的注释，起到的是全局范围的作用，包下面的每个 go 文件，同样可以定义自己的 Annotation 注释。(关于代码生成，可以看[这篇文章](https://blog.openshift.com/kubernetes-deep-dive-code-generation-customresources/))    
`pkg/apis/samplecontroller/v1alpha1/types.go`，包含了`Foo`类型的完整定义。`Foo`是Kubernetes对象的标准定义；`FooSpec`是我们需要定义的`Foo`类型的具体结构；`FooList`包含一组 `Foo` 对象，apiserver 的 List 接口，返回的是 List 对象类型；`FooStatus`描述`Foo`类型实例状态的结构体，可以使用`+genclient:noStatus` 注释，则不需要定义`FooStatus`。    
`pkg/apis/samplecontroller/v1alpha1/register.go`，主要作用是通过`addKnownTypes()`方法，将我们定义的 CRD 类型 `Foo` 添加到 Scheme。    


## 代码生成
`pkg`下的上述文件完成，即可执行`./hack/update-codegen.sh`，即可生成管理新定义的 CRD 类型所需的 Kubernetes 代码：    
```
sample-controller
├── hack
│   ├── boilerplate.go.txt
│   ├── custom-boilerplate.go.txt
│   ├── update-codegen.sh
│   └── verify-codegen.sh
└── pkg
    ├── apis
    │   └── samplecontroller
    │       ├── register.go
    │       └── v1alpha1
    │           ├── doc.go
    │           ├── register.go
    │           ├── types.go
    │           └── zz_generated.deepcopy.go
    └── generated
        ├── clientset
        │   └── versioned
        │       ├── clientset.go
        │       ├── doc.go
        │       ├── fake
        │       │   ├── clientset_generated.go
        │       │   ├── doc.go
        │       │   └── register.go
        │       ├── scheme
        │       │   ├── doc.go
        │       │   └── register.go
        │       └── typed
        │           └── samplecontroller
        │               └── v1alpha1
        │                   ├── doc.go
        │                   ├── fake
        │                   │   ├── doc.go
        │                   │   ├── fake_foo.go
        │                   │   └── fake_samplecontroller_client.go
        │                   ├── foo.go
        │                   ├── generated_expansion.go
        │                   └── samplecontroller_client.go
        ├── informers
        │   └── externalversions
        │       ├── factory.go
        │       ├── generic.go
        │       ├── internalinterfaces
        │       │   └── factory_interfaces.go
        │       └── samplecontroller
        │           ├── interface.go
        │           └── v1alpha1
        │               ├── foo.go
        │               └── interface.go
        └── listers
            └── samplecontroller
                └── v1alpha1
                    ├── expansion_generated.go
                    └── foo.go
```

自动生成了 `clientset`，`informers`，`listers` 三个文件夹下的文件和`apis`下的`zz_generated.deepcopy.go`文件。     
其中`zz_generated.deepcopy.go`中包含 `pkg/apis/samplecontroller/v1alpha1/types.go` 中定义的结构体的 `DeepCopy()` 方法。    
另外三个文件夹`clientset`，`informers`，`listers`下都是 Kubernetes 生成的客户端库，在 controller 中会用到。    

## controller 代码编写
接下来就是编写具体 controller 的代码，通过上述步骤生成的客户端库访问 apiserver，监听 CRD 资源的变化，并触发对应的动作，如创建或删除 `Deployment` 等。     

编写自定义controller(Operator)时，可以使用 Kubernetes 提供的 `client-go` 客户端库。下图是 Kubernetes 提供的在使用`client-go`开发 controller 的过程中，`client-go` 和 controller 的交互流程：    
![](/media/posts/cloud/sample-controller/client-go-controller-interaction.jpeg)

### client-go 组件
- Reflector: 定义在 cache 包的 [Reflector](https://github.com/kubernetes/client-go/blob/master/tools/cache/reflector.go) 类中，它监听特定资源类型(Kind)的 Kubernetes API，在`ListAndWatch`方法中执行。监听的对象可以是 Kubernetes 的内置资源类型或者是自定义资源类型。当 reflector 通过 watch API 发现新的资源实例被创建，它将通过对应的 list API 获取到新创建的对象并在`watchHandler`方法中将其加入到`Delta Fifo`队列中。    

- Informer: 定义在 cache 包的 [base controller](https://github.com/kubernetes/client-go/blob/master/tools/cache/controller.go) 中，它从`Delta Fifo`队列中 pop 出对象，在`processLoop`方法中执行。base controller 的工作是将对象保存一遍后续获取，并调用 controller 将对象传给 controller。    

- Indexer: 提供对象的 indexing 方法，定义在 cache 包的 [Indexer](https://github.com/kubernetes/client-go/blob/master/tools/cache/index.go)中。一个典型的 indexing 的应用场景是基于对象的 label 创建索引。Indexer 基于几个 indexing 方法维护索引，它使用线程安全的 data store 来存储对象和他们的key。在 cache 包的 [Store](https://github.com/kubernetes/client-go/blob/master/tools/cache/store.go) 类中定义了一个名为`MetaNamespaceKeyFunc`的默认方法，可以为对象生成一个`<namespace>/<name>`形式的key。    

### 自定义 controller 组件
- Informer reference: 它是对 Informer 实例的引用，知道如何使用自定义资源对象。你编写的自定义 controller 需要创建正确的 Informer。    
- Indexer reference: 它是对 Indexer 实例的引用，你编写的自定义 controller 代码中需要创建它，在获取对象供后续使用时你会用到这个引用。

client-go 中的 base controller 提供了`NewIndexerInformer`来创建 Informer 和 Indexer。在你的代码中，你可以直接使用 [此方法](https://github.com/kubernetes/client-go/blob/master/examples/workqueue/main.go#L174)，或者使用 [工厂方法](https://github.com/kubernetes/sample-controller/blob/master/main.go#L61) 创建 informer。    

- Resource Event Handlers: 一些回调方法，当 Informer 想要发送一个对象给 controller 时，会调用这些方法。典型的编写回调方法的模式，是获取资源对象的 key 并放入一个 `work queue`队列，等待进一步的处理(Proceess item)。    
- Work queue: 在 controller 代码中创建的队列，用来解耦对象的传递和对应的处理。Resource Event Handlers 的方法就是用来接收对象并将其加入 `work queue`。    
- Process Item: 在 controller 代码中创建的方法，用来对`work queue`中的对象做对应处理，可以有一个或多个其他的方法实际做处理，这些方法一般会使用`Indexer reference`，或者 list 方法来获取 key 对应的对象。    

### 编写自定义 controller
以 sample-controller 为例，整体流程如下：    
```golang
/*
*** main.go
*/
// 创建 clientset
kubeClient, err := kubernetes.NewForConfig(cfg)		// k8s clientset, "k8s.io/client-go/kubernetes"
exampleClient, err := clientset.NewForConfig(cfg)	// sample clientset, "k8s.io/sample-controller/pkg/generated/clientset/versioned"

// 创建 Informer
kubeInformerFactory := kubeinformers.NewSharedInformerFactory(kubeClient, time.Second*30)		// k8s informer, "k8s.io/client-go/informers"
exampleInformerFactory := informers.NewSharedInformerFactory(exampleClient, time.Second*30)		// sample informer, "k8s.io/sample-controller/pkg/generated/informers/externalversions"

// 创建 controller，传入 clientset 和 informer
controller := NewController(kubeClient, exampleClient,
		kubeInformerFactory.Apps().V1().Deployments(),
		exampleInformerFactory.Samplecontroller().V1alpha1().Foos())

// 运行 Informer，Start 方法为非阻塞，会运行在单独的 goroutine 中
kubeInformerFactory.Start(stopCh)	
exampleInformerFactory.Start(stopCh)

// 运行 controller
controller.Run(2, stopCh)

/*
*** controller.go 
*/
NewController() *Controller {}
	// 将 CRD 资源类型定义加入到 Kubernetes 的 Scheme 中，以便 Events 可以记录 CRD 的事件
	utilruntime.Must(samplescheme.AddToScheme(scheme.Scheme))

	// 创建 Broadcaster
	eventBroadcaster := record.NewBroadcaster()
	// ... ...

	// 监听 CRD 类型'Foo'并注册 ResourceEventHandler 方法，当'Foo'的实例变化时进行处理
	fooInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: controller.enqueueFoo,
		UpdateFunc: func(old, new interface{}) {
			controller.enqueueFoo(new)
		},
	})

	// 监听 Deployment 变化并注册 ResourceEventHandler 方法，
	// 当它的 ownerReferences 为 Foo 类型实例时，将该 Foo 资源加入 work queue
	deploymentInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: controller.handleObject,
		UpdateFunc: func(old, new interface{}) {
			newDepl := new.(*appsv1.Deployment)
			oldDepl := old.(*appsv1.Deployment)
			if newDepl.ResourceVersion == oldDepl.ResourceVersion {
				return
			}
			controller.handleObject(new)
		},
		DeleteFunc: controller.handleObject,
	})

func (c *Controller) Run(threadiness int, stopCh <-chan struct{}) error {}
	// 在启动 worker 前等待缓存同步
	if ok := cache.WaitForCacheSync(stopCh, c.deploymentsSynced, c.foosSynced); !ok {
		return fmt.Errorf("failed to wait for caches to sync")
	}
	// 运行两个 worker 来处理资源
	for i := 0; i < threadiness; i++ {
		go wait.Until(c.runWorker, time.Second, stopCh)
	}
	// 无限循环，不断的调用 processNextWorkItem 处理下一个对象
	func (c *Controller) runWorker() {
		for c.processNextWorkItem() {
		}
	}
	// 从workqueue中获取下一个对象并进行处理，通过调用 syncHandler
	func (c *Controller) processNextWorkItem() bool {
		obj, shutdown := c.workqueue.Get()
		if shutdown {
			return false
		}
		err := func(obj interface{}) error {
			// 调用 workqueue.Done(obj) 方法告诉 workqueue 当前项已经处理完毕，
			// 如果我们不想让当前项重新入队，一定要调用 workqueue.Forget(obj)。
			// 当我们没有调用Forget时，当前项会重新入队 workqueue 并在一段时间后重新被获取。
			defer c.workqueue.Done(obj)
			var key string
			var ok bool
			// 我们期望的是 key 'namespace/name' 格式的 string
			if key, ok = obj.(string); !ok {
				// 无效的项调用Forget方法，避免重新入队。
				c.workqueue.Forget(obj)
				utilruntime.HandleError(fmt.Errorf("expected string in workqueue but got %#v", obj))
				return nil
			}
			if err := c.syncHandler(key); err != nil {
				// 放回workqueue避免偶发的异常
				c.workqueue.AddRateLimited(key)
				return fmt.Errorf("error syncing '%s': %s, requeuing", key, err.Error())
			}
			// 如果没有异常，Forget当前项，同步成功
			c.workqueue.Forget(obj)
			klog.Infof("Successfully synced '%s'", key)
			return nil
		}(obj)
		if err != nil {
			utilruntime.HandleError(err)
			return true
		}

		return true
	}
	// 对比真实的状态和期望的状态并尝试合并，然后更新Foo类型实例的状态信息
	func (c *Controller) syncHandler(key string) error {
		// 通过 workqueue 中的 key 解析出 namespace 和 name
		namespace, name, err := cache.SplitMetaNamespaceKey(key)
		// 调用 lister 接口通过 namespace 和 name 获取 Foo 实例
		foo, err := c.foosLister.Foos(namespace).Get(name)
		deploymentName := foo.Spec.DeploymentName
		// 获取 Foo 实例中定义的 deploymentname
		deployment, err := c.deploymentsLister.Deployments(foo.Namespace).Get(deploymentName)
		// 没有发现对应的 deployment，新建一个
		if errors.IsNotFound(err) {
			deployment, err = c.kubeclientset.AppsV1().Deployments(foo.Namespace).Create(newDeployment(foo))
		}
		// OwnerReferences 不是 Foo 实例，warning并返回错误
		if !metav1.IsControlledBy(deployment, foo) {
			msg := fmt.Sprintf(MessageResourceExists, deployment.Name)
			c.recorder.Event(foo, corev1.EventTypeWarning, ErrResourceExists, msg)
			return fmt.Errorf(msg)
		}
		// deployment 中 的配置和 Foo 实例中 Spec 的配置不一致，即更新 deployment
		if foo.Spec.Replicas != nil && *foo.Spec.Replicas != *deployment.Spec.Replicas {
			deployment, err = c.kubeclientset.AppsV1().Deployments(foo.Namespace).Update(newDeployment(foo))
		}
		// 更新 Foo 实例状态
		err = c.updateFooStatus(foo, deployment)
		c.recorder.Event(foo, corev1.EventTypeNormal, SuccessSynced, MessageResourceSynced)
	}
```

接下来编写对应的 CRD 和 对应 CRD 实例的 yaml 文件及 operator 的 Dockerfile：    
```
sample-controller
├── artifacts
│   └── examples
│       ├── crd.yaml
│       └── example-foo.yaml
├── controller.go
├── Dockerfile
├── hack
│   ├── boilerplate.go.txt
│   ├── custom-boilerplate.go.txt
│   ├── update-codegen.sh
│   └── verify-codegen.sh
├── main.go
└── pkg
    ├── apis
    │   └── samplecontroller
    │       ├── register.go
    │       └── v1alpha1
    │           ├── doc.go
    │           ├── register.go
    │           ├── types.go
    │           └── zz_generated.deepcopy.go
    ├── generated
    │   ├── clientset
    │   │   └── ...
    │   ├── informers
    │   │   └── ...
    │   └── listers
    │       └── ...
    └── signals
        └── signal.go
```

### 部署到 k8s
controller 镜像 Dockerfile:    
```Dockerfile
FROM golang
RUN mkdir -p /go/src/k8s.io/sample-controller
ADD . /go/src/k8s.io/sample-controller
WORKDIR /go
RUN go get -v ./...
RUN go install -v ./...
CMD ["/go/bin/sample-controller"]
```

controller RBAC 及 Deployment yaml:    
```yaml
apiVersion: apps/v1beta1
kind: Deployment
metadata:
  name: sample-controller
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: sample
    spec:
      containers:
      - name: sample
        image: "maoqide/sample-controller"
---

apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: operator-role
rules:
- apiGroups:
  - ""
  resources:
  - events
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
- apiGroups:
  - apps
  resources:
  - deployments
  - events
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
- apiGroups:
  - samplecontroller.k8s.io
  resources:
  - foos
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
---

apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: operator-rolebinding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: operator-role
subjects:
- kind: ServiceAccount
  name: default
  namespace: default
```

将 operator 部署到 k8s 中并创建一个 CRD 对象，即可看到 operator 自动按照 CRD 对象 的配置创建出一个 nginx Deployment。    
