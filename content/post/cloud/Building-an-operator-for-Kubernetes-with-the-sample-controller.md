---
title: "Building an Operator for Kubernetes With the Sample Controller"
date: "2019-03-16T21:34:46+08:00"
author: "Maoqide"
tags: ["cloud", "kubernetes", "kubernetes-operator"]
draft: false
---

    An Operator is an application-specific controller that extends the Kubernetes API to create, configure, and manage instances of complex stateful applications on behalf of a Kubernetes user.     
Operator 是一个特定的应用程序的控制器，通过扩展 Kubernetes API 以代表 Kubernetes 用户创建，配置和管理复杂有状态应用程序的实例。    
Operator 是一种软件，它结合了特定的领域知识并通过 CRD(Custom Resource Definition ) 机制扩展了Kubernetes API，使用户像管理 Kubernetes 的内置资源一样创建，配置和管理应用程序。Operator 管理整个集群中的多个实例，而不仅仅管理应用程序的单个实例。    
<!--more-->

[译] https://itnext.io/building-an-operator-for-kubernetes-with-the-sample-controller-b4204be9ad56    

## The sample-controller

创建示例的 operator 程序需要用到的第一个工具是 [sample-controller](https://github.com/kubernetes/sample-controller), 可以在 https://github.com/kubernetes/sample-controller 找到。    

这个项目实现了一个简单的 `Foo` 类型的 operator, 当创建一个自定义类型的对象 `foo`，operator 会创建一个 以几个公开的 docker 镜像和特定的副本数创建一个 `Deployment`。    
要安装和编译它，需要确认你的 `GOPATH`，然后执行:    
```shell
go get github.com/kubernetes/sample-controller
cd $GOPATH/src/k8s.io/sample-controller
go build -o ctrl .
```
接着我们可以用`artifacts/examples`目录下的文件，创建`Foo`类型的自定义资源定义(CRD)。    
```shell
kubectl apply -f artifacts/examples/crd-validation.yaml
```
现在从另一个终端，我们可以操作`Foo`对象并观察 controller 发生了什么：    
```shell
$ kubectl apply -f artifacts/examples/example-foo.yaml
$ kubectl get pods
NAME                           READY  STATUS    RESTARTS   AGE
example-foo-6cbc69bf5d-j8lhx   1/1    Running   0          18s
$ kubectl delete -f artifacts/examples/example-foo.yaml
$ kubectl get pods
NAME                           READY  STATUS        RESTARTS   AGE
example-foo-6cbc69bf5d-j8lhx   0/1    Terminating   0          38s
```

	在 Kubernetes 1.11.0，controller 会进入无限循环，当 foo 对象创建一个 deployment 后更新它的状态：在`updateFooStatus`方法中，你必调用`UpdateStatus(fooCopy)`代替`Update(fooCopy)`。    

到目前为止，控制器完成了这样一项工作：它在我们创建`foo`对象时创建一个`deployment`并在我们删除对象时停止`deployment`。    

现在我们可以进一步调整 CRD 和 controller 以使用我们自己的自定义资源定义。    

## Adapting the sample-controller

假设我们的目标是编写一个在集群节点上部署守护程序的 operator。它会使用 DaemonSet 对象来部署此守护程序，并且能够指定标签，仅在打上此标签的节点上部署守护程序。我们，还希望能够指定部署的 docker 镜像，而不是像`sample-controller`的例子那样静态的。    

我们首先为`GenericDaemon`类型创建自定义资源定义：    
```yaml
// artifacts/generic-daemon/crd.yaml
apiVersion: apiextensions.k8s.io/v1beta1
kind: CustomResourceDefinition
metadata:
  name: genericdaemons.mydomain.com
spec:
  group: mydomain.com
  version: v1beta1
  names:
    kind: Genericdaemon
    plural: genericdaemons
  scope: Namespaced
  validation:
    openAPIV3Schema:
      properties:
        spec:
          properties:
            label:
              type: string
            image:
              type: string
          required:
            - image
```

以及第一个要部署的守护程序的示例：    
```yaml
// artifacts/generic-daemon/syslog.yaml
apiVersion: mydomain.com/v1beta1
kind: Genericdaemon
metadata:
  name: syslog
spec:
  label: logs
  image: mbessler/syslogdocker
```

现在我们必须为 operator 访问新的自定义资源定义(CRD)的 API 构建 go 文件。为此，我们要创建一个新的目录`pkg/apis/genericdaemon`，在这个目录中复制`pkg/apis/samplecontroller`目录下的文件(除了`zz_generated.deepcopy.go`)。    
```shell
$ tree pkg/apis/genericdaemon/
pkg/apis/genericdaemon/
├── register.go
└── v1beta1
    ├── doc.go
    ├── register.go
    └── types.go
```
并调整其内容：    
```golang
////////////////
// register.go
////////////////
package genericdaemon
const (
 GroupName = "mydomain.com"
)
/////////////////////
// v1beta1/doc.go
/////////////////////
// +k8s:deepcopy-gen=package
// Package v1beta1 is the v1beta1 version of the API.
// +groupName=mydomain.com
package v1beta1
/////////////////////////
// v1beta1/register.go
/////////////////////////
package v1beta1
import (
 metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
 "k8s.io/apimachinery/pkg/runtime"
 "k8s.io/apimachinery/pkg/runtime/schema"
genericdaemon "k8s.io/sample-controller/pkg/apis/genericdaemon"
)
// SchemeGroupVersion is group version used to register these objects
var SchemeGroupVersion = schema.GroupVersion{Group: genericdaemon.GroupName, Version: "v1beta1"}
// Kind takes an unqualified kind and returns back a Group qualified GroupKind
func Kind(kind string) schema.GroupKind {
 return SchemeGroupVersion.WithKind(kind).GroupKind()
}
// Resource takes an unqualified resource and returns a Group qualified GroupResource
func Resource(resource string) schema.GroupResource {
 return SchemeGroupVersion.WithResource(resource).GroupResource()
}
var (
 SchemeBuilder = runtime.NewSchemeBuilder(addKnownTypes)
 AddToScheme   = SchemeBuilder.AddToScheme
)
// Adds the list of known types to Scheme.
func addKnownTypes(scheme *runtime.Scheme) error {
 scheme.AddKnownTypes(SchemeGroupVersion,
  &Genericdaemon{},
  &GenericdaemonList{},
 )
 metav1.AddToGroupVersion(scheme, SchemeGroupVersion)
 return nil
}
//////////////////////
// v1beta1/types.go
//////////////////////
package v1beta1
import (
 metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)
// +genclient
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
// Genericdaemon is a specification for a Generic Daemon resource
type Genericdaemon struct {
 metav1.TypeMeta   `json:",inline"`
 metav1.ObjectMeta `json:"metadata,omitempty"`
 Spec   GenericdaemonSpec   `json:"spec"`
 Status GenericdaemonStatus `json:"status"`
}
// GenericDaemonSpec is the spec for a GenericDaemon resource
type GenericdaemonSpec struct {
 Label string `json:"label"`
 Image string `json:"image"`
}
// GenericDaemonStatus is the status for a GenericDaemon resource
type GenericdaemonStatus struct {
 Installed int32 `json:"installed"`
}
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
// GenericDaemonList is a list of GenericDaemon resources
type GenericdaemonList struct {
 metav1.TypeMeta `json:",inline"`
 metav1.ListMeta `json:"metadata"`
Items []Genericdaemon `json:"items"`
}
```

脚本`hack/update-codegen.sh`可用于生成我们之前文件中定义的新的自定义资源定义(CRD)的代码，我们必需修改此脚本来为我们的新 CRD 生成文件：    
```shell
# hack/update-codegen.sh
#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
SCRIPT_ROOT=$(dirname ${BASH_SOURCE})/..
CODEGEN_PKG=${CODEGEN_PKG:-$(cd ${SCRIPT_ROOT}; ls -d -1 ./vendor/k8s.io/code-generator 2>/dev/null || echo ../code-generator)}
# generate the code with:
# --output-base    because this script should also be able to run inside the vendor dir of
#                  k8s.io/kubernetes. The output-base is needed for the generators to output into the vendor dir
#                  instead of the $GOPATH directly. For normal projects this can be dropped.
${CODEGEN_PKG}/generate-groups.sh "deepcopy,client,informer,lister" \
  k8s.io/sample-controller/pkg/client k8s.io/sample-controller/pkg/apis \
  genericdaemon:v1beta1 \
  --output-base "$(dirname ${BASH_SOURCE})/../../.." \
  --go-header-file ${SCRIPT_ROOT}/hack/boilerplate.go.txt
```

接着执行此脚本：    
```shell
$ ./hack/update-codegen.sh 
Generating deepcopy funcs
Generating clientset for genericdaemon:v1beta1 at k8s.io/sample-controller/pkg/client/clientset
Generating listers for genericdaemon:v1beta1 at k8s.io/sample-controller/pkg/client/listers
Generating informers for genericdaemon:v1beta1 at k8s.io/sample-controller/pkg/client/informers
```
现在可以调整它来编写我们的 operator。首先，我们必须将所有对之前的`Foo`类型的引用修改为`Genericdaemon`类型。另外，当一个新的 `genericdaemon`实例创建后，我们要创建 DaemonSet 而不是 Deployment。    

## Deploying the operator to the Kubernetes cluster
当我们将`sample-controller`修改为我们需要的之后，我们要将它部署到kubernetes集群。事实上，在这个时候，我们已经使用我们的凭证将它运行在我们的开发系统来测试它。    

这是一个简单的 Dockerfile，用于构建 operator 的 Docker 镜像（你必须删除原有的`sample-controller`中的所有代码才能构建）：    
```Dockerfile
FROM golang
RUN mkdir -p /go/src/k8s.io/sample-controller
ADD . /go/src/k8s.io/sample-controller
WORKDIR /go
RUN go get ./...
RUN go install -v ./...
CMD ["/go/bin/sample-controller"]
```
现在我们可以构建并将镜像推送到 DockerHub：    
```shell
docker build . -t mydockerid/genericdaemon
docker push mydockerid/genericdaemon
```

最后用这个新的镜像部署一个 Deployment：    
```yaml
// deploy.yaml
apiVersion: apps/v1beta1
kind: Deployment
metadata:
  name: sample-controller
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sample
  template:
    metadata:
      labels:
        app: sample
    spec:
      containers:
      - name: sample
		image: "mydockerid/genericdaemon:latest"
```
并`kubectl apply -f deploy.yaml`。    

operator 现在已经运行，但是如果我们查看 pod 的日志，可以看到授权存在问题; pod 没有对不同资源的访问权限：   
```
$ kubectl logs sample-controller-66b79c7d5f-2qnft
E0721 14:34:50.499584       1 reflector.go:134] k8s.io/sample-controller/pkg/client/informers/externalversions/factory.go:117: Failed to list *v1beta1.Genericdaemon: genericdaemons.mydomain.com is forbidden: User "system:serviceaccount:default:default" cannot list genericdaemons.mydomain.com at the cluster scope
E0721 14:34:50.500385       1 reflector.go:134] k8s.io/client-go/informers/factory.go:131: Failed to list *v1.DaemonSet: daemonsets.apps is forbidden: User "system:serviceaccount:default:default" cannot list daemonsets.apps at the cluster scope
[...]
```
我们需要创建一个`ClusterRole`和一个`ClusterRoleBinding`来为 operator 提供必要的权限：    
```yaml
// rbac_role.yaml
kind: ClusterRole
metadata:
  name: operator-role
rules:
- apiGroups:
  - apps
  resources:
  - daemonsets
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
- apiGroups:
  - mydomain.com
  resources:
  - genericdaemons
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
  - delete
// rbac_role_binding.yaml
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
并且部署它：    
```shell
kubectl apply -f rbac_role.yaml
kubectl delete -f deploy.yaml
kubectl apply -f deploy.yaml
```
现在，你的 operator 应该已经部署到你的 Kubernetes 集群并处于活动状态。    