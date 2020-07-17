---
title: "Sample Operator"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["think"]
date: 2020-06-29T15:40:29+08:00
draft: true
---

sample operator for kubernetes sample controller.    
<!--more-->

## kubebuilder


### 生成脚手架
```bash
# cd 到项目根目录
kubebuilder init --domain <domain_name>
```

```
➜  sample-operator git:(master) kubebuilder init --domain k8s.io
Writing scaffold for you to edit...
Get controller runtime:
$ go get sigs.k8s.io/controller-runtime@v0.5.0
go: downloading sigs.k8s.io/controller-runtime v0.5.0
go: downloading k8s.io/apimachinery v0.17.2
go: downloading k8s.io/client-go v0.17.2
go: downloading github.com/go-logr/logr v0.1.0
go: downloading k8s.io/api v0.17.2
go: downloading github.com/golang/groupcache v0.0.0-20180513044358-24b0969c4cb7
go: downloading k8s.io/apiextensions-apiserver v0.17.2
go: downloading github.com/imdario/mergo v0.3.6
go: downloading gomodules.xyz/jsonpatch/v2 v2.0.1
go: downloading golang.org/x/crypto v0.0.0-20190820162420-60c769a6c586
go: downloading gopkg.in/yaml.v2 v2.2.4
Update go.mod:
$ go mod tidy
go: downloading github.com/go-logr/zapr v0.1.0
go: downloading github.com/onsi/ginkgo v1.11.0
go: downloading github.com/onsi/gomega v1.8.1
go: downloading go.uber.org/atomic v1.3.2
go: downloading golang.org/x/xerrors v0.0.0-20190717185122-a985d3407aa7
Running make:
$ make
go: creating new go.mod: module tmp
go: downloading sigs.k8s.io/controller-tools v0.2.5
go: found sigs.k8s.io/controller-tools/cmd/controller-gen in sigs.k8s.io/controller-tools v0.2.5
go: downloading github.com/gobuffalo/flect v0.2.0
go: downloading github.com/fatih/color v1.7.0
go: downloading gopkg.in/yaml.v3 v3.0.0-20190905181640-827449938966
go: downloading golang.org/x/tools v0.0.0-20190920225731-5eefd052ad72
go: downloading github.com/mattn/go-colorable v0.1.2
go: downloading github.com/mattn/go-isatty v0.0.8
/Users/maoqide/go/bin/controller-gen object:headerFile="hack/boilerplate.go.txt" paths="./..."
go fmt ./...
go vet ./...
go build -o bin/manager main.go
Next: define a resource with:
$ kubebuilder create api
```

目录结构:    
```
.
├── Dockerfile
├── Makefile
├── PROJECT
├── README.md
├── bin
│   └── manager
├── config
│   ├── certmanager
│   │   ├── certificate.yaml
│   │   ├── kustomization.yaml
│   │   └── kustomizeconfig.yaml
│   ├── default
│   │   ├── kustomization.yaml
│   │   ├── manager_auth_proxy_patch.yaml
│   │   ├── manager_webhook_patch.yaml
│   │   └── webhookcainjection_patch.yaml
│   ├── manager
│   │   ├── kustomization.yaml
│   │   └── manager.yaml
│   ├── prometheus
│   │   ├── kustomization.yaml
│   │   └── monitor.yaml
│   ├── rbac
│   │   ├── auth_proxy_client_clusterrole.yaml
│   │   ├── auth_proxy_role.yaml
│   │   ├── auth_proxy_role_binding.yaml
│   │   ├── auth_proxy_service.yaml
│   │   ├── kustomization.yaml
│   │   ├── leader_election_role.yaml
│   │   ├── leader_election_role_binding.yaml
│   │   └── role_binding.yaml
│   └── webhook
│       ├── kustomization.yaml
│       ├── kustomizeconfig.yaml
│       └── service.yaml
├── go.mod
├── go.sum
├── hack
│   └── boilerplate.go.txt
└── main.go
```


```bash
kubebuilder create api --group sampleoperator --version v1alpha1 --kind Foo
```

```
➜  sample-operator git:(master) ✗ kubebuilder create api --group sampleoperator --version v1alpha1 --kind Foo
Create Resource [y/n]
y
Create Controller [y/n]
y
Writing scaffold for you to edit...
api/v1alpha1/foo_types.go
controllers/foo_controller.go
Running make:
$ make
go: creating new go.mod: module tmp
go: found sigs.k8s.io/controller-tools/cmd/controller-gen in sigs.k8s.io/controller-tools v0.2.5
/Users/maoqide/go/bin/controller-gen object:headerFile="hack/boilerplate.go.txt" paths="./..."
go fmt ./...
go vet ./...
go build -o bin/manager main.go
```

```
.
├── Dockerfile
├── Makefile
├── PROJECT
├── api
│   └── v1alpha1
│       ├── foo_types.go
│       ├── groupversion_info.go
│       └── zz_generated.deepcopy.go
├── bin
│   └── manager
├── config
│   ├── certmanager
│   │   ├── certificate.yaml
│   │   ├── kustomization.yaml
│   │   └── kustomizeconfig.yaml
│   ├── crd
│   │   ├── kustomization.yaml
│   │   ├── kustomizeconfig.yaml
│   │   └── patches
│   │       ├── cainjection_in_foos.yaml
│   │       └── webhook_in_foos.yaml
│   ├── default
│   │   ├── kustomization.yaml
│   │   ├── manager_auth_proxy_patch.yaml
│   │   ├── manager_webhook_patch.yaml
│   │   └── webhookcainjection_patch.yaml
│   ├── manager
│   │   ├── kustomization.yaml
│   │   └── manager.yaml
│   ├── prometheus
│   │   ├── kustomization.yaml
│   │   └── monitor.yaml
│   ├── rbac
│   │   ├── auth_proxy_client_clusterrole.yaml
│   │   ├── auth_proxy_role.yaml
│   │   ├── auth_proxy_role_binding.yaml
│   │   ├── auth_proxy_service.yaml
│   │   ├── foo_editor_role.yaml
│   │   ├── foo_viewer_role.yaml
│   │   ├── kustomization.yaml
│   │   ├── leader_election_role.yaml
│   │   ├── leader_election_role_binding.yaml
│   │   └── role_binding.yaml
│   ├── samples
│   │   └── sampleoperator_v1alpha1_foo.yaml
│   └── webhook
│       ├── kustomization.yaml
│       ├── kustomizeconfig.yaml
│       └── service.yaml
├── controllers
│   ├── foo_controller.go
│   └── suite_test.go
├── go.mod
├── go.sum
├── hack
│   └── boilerplate.go.txt
└── main.go
```

到此，我们初始化好了一个最基础的 k8s operator 开发的脚手架。    
此时，在项目根目录执行`make manifests`，会生成 k8s operator 所需的一些配置文件，如 CRD、RBAC 等，生成到 configs 文件夹下。    
如果此时本地机器可以直接通过`kubectl`命令操作目标 k8s 集群，可以执行`make install`，这条命令会将生成的 CRD 的 yaml 文件直接 apply 到集群中创建 CRD。    
执行`make generate`，会进行代码生成，如`zz_generated.deepcopy.go`，如果修改了代码中的形如`// +comment`的注解，需要重新执行此命令生成代码。    
此时，直接执行`go run ./main.go`，即可运行 operator 代码。    
```bash
➜  sample-operator git:(master) go run ./main.go
2020-07-14T17:58:34.172+0800    INFO    controller-runtime.metrics      metrics server is starting to listen    {"addr": ":8080"}
2020-07-14T17:58:34.172+0800    INFO    setup   starting manager
2020-07-14T17:58:34.172+0800    INFO    controller-runtime.manager      starting metrics server {"path": "/metrics"}
2020-07-14T17:58:34.172+0800    INFO    controller-runtime.controller   Starting EventSource    {"controller": "foo", "source": "kind source: /, Kind="}
2020-07-14T17:58:34.273+0800    INFO    controller-runtime.controller   Starting EventSource    {"controller": "foo", "source": "kind source: /, Kind="}
2020-07-14T17:58:34.374+0800    INFO    controller-runtime.controller   Starting Controller     {"controller": "foo"}
2020-07-14T17:58:34.374+0800    INFO    controller-runtime.controller   Starting workers        {"controller": "foo", "worker count": 1}
2020-07-14T17:58:34.399+0800    DEBUG   controller-runtime.controller   Successfully Reconciled {"controller": "foo", "request": "default/foo-sample"}
```

### crd 定义
编辑 api/v1alpha1/foo_types.go 文件，更改定义需要的结构体定义。    
在非必须的 field 定义上可以加上`// +optional`注解    
如果后续需要获取和更新自定义资源的状态信息，可以在结构体定义上加上 subresource 注解，如下:    
```golang
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status

// Foo is the Schema for the foos API
type Foo struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   FooSpec   `json:"spec,omitempty"`
	Status FooStatus `json:"status,omitempty"`
}
```

### 添加 Reconcile 逻辑
controller 主要逻辑在 controllers/foo_controller.go 中。

