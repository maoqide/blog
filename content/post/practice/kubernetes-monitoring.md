---
title: "Kubernetes Monitoring"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["practicing"]
date: 2019-09-25T10:15:26+08:00
draft: true
---

完整的记录 kubernetes 监控从部署到配置。    
<!--more-->

## prometheus operator/statefulset
https://github.com/kubernetes/kubernetes/tree/master/cluster/addons/prometheus

```shell
# change namespace
sed -i s/kube-system/monitoring/g *

# dynamic provision storage class

kubectl create -f prometheus-configmap.yaml 
kubectl create -f prometheus-rbac.yaml 
kubectl create -f prometheus-statefulset.yaml 
kubectl create -f prometheus-service.yaml 

# kube-metrics-server
kubectl create -f kube-state-metrics-deployment.yaml
kubectl create -f kube-state-metrics-rbac.yaml
kubectl create -f kube-state-metrics-service.yaml
# node-exporter
kubectl create -f node-exporter-ds.yml
kubectl create -f node-exporter-service.yaml
```

/etc/systemd/system/kubelet.service.d/10-kubeadm.conf 
```
[Service]
Environment="KUBELET_EXTRA_ARGS=--pod-infra-container-image=harbor.guahao-inc.com/kubernetes/pause-amd64:3.1 --hostname-override=172.27.32.165"
Environment="KUBELET_KUBECONFIG_ARGS=--bootstrap-kubeconfig=/etc/kubernetes/bootstrap-kubelet.conf --kubeconfig=/etc/kubernetes/kubelet.conf"
Environment="KUBELET_SYSTEM_PODS_ARGS=--pod-manifest-path=/etc/kubernetes/manifests --allow-privileged=true"
Environment="KUBELET_NETWORK_ARGS=--network-plugin=cni --cni-conf-dir=/etc/cni/net.d --cni-bin-dir=/opt/cni/bin"
Environment="KUBELET_DNS_ARGS=--cluster-dns=10.254.0.10 --cluster-domain=cluster.local"
Environment="KUBELET_AUTHZ_ARGS=--authorization-mode=Webhook --client-ca-file=/etc/kubernetes/pki/ca.crt"
Environment="KUBELET_CADVISOR_ARGS=--cadvisor-port=0"
Environment="KUBELET_CGROUP_ARGS=--cgroup-driver=systemd"
Environment="KUBELET_CERTIFICATE_ARGS=--rotate-certificates=true --cert-dir=/var/lib/kubelet/pki"
ExecStart=
ExecStart=/usr/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_SYSTEM_PODS_ARGS $KUBELET_NETWORK_ARGS $KUBELET_DNS_ARGS $KUBELET_AUTHZ_ARGS $KUBELET_CADVISOR_ARGS $KUBELET_CGROUP_ARGS $KUBELET_CERTIFICATE_ARGS $KUBELET_EXTRA_ARGS
```

```shell
# https://github.com/coreos/prometheus-operator/blob/master/Documentation/troubleshooting.md     
# all node
KUBEADM_SYSTEMD_CONF=/etc/systemd/system/kubelet.service.d/10-kubeadm.conf
sed -e "/cadvisor-port=0/d" -i "$KUBEADM_SYSTEMD_CONF"
if ! grep -q "authentication-token-webhook=true" "$KUBEADM_SYSTEMD_CONF"; then
  sed -e "s/--authorization-mode=Webhook/--authentication-token-webhook=true --authorization-mode=Webhook/" -i "$KUBEADM_SYSTEMD_CONF"
fi
systemctl daemon-reload
systemctl restart kubelet

# master
sed -e "s/- --address=127.0.0.1/- --address=0.0.0.0/" -i /etc/kubernetes/manifests/kube-controller-manager.yaml
sed -e "s/- --address=127.0.0.1/- --address=0.0.0.0/" -i /etc/kubernetes/manifests/kube-scheduler.yaml
```

```
[Service]
Environment="KUBELET_EXTRA_ARGS=--pod-infra-container-image=harbor.guahao-inc.com/kubernetes/pause-amd64:3.1 --hostname-override=172.27.32.165"
Environment="KUBELET_KUBECONFIG_ARGS=--bootstrap-kubeconfig=/etc/kubernetes/bootstrap-kubelet.conf --kubeconfig=/etc/kubernetes/kubelet.conf"
Environment="KUBELET_SYSTEM_PODS_ARGS=--pod-manifest-path=/etc/kubernetes/manifests --allow-privileged=true"
Environment="KUBELET_NETWORK_ARGS=--network-plugin=cni --cni-conf-dir=/etc/cni/net.d --cni-bin-dir=/opt/cni/bin"
Environment="KUBELET_DNS_ARGS=--cluster-dns=10.254.0.10 --cluster-domain=cluster.local"
Environment="KUBELET_AUTHZ_ARGS=--authentication-token-webhook=true --authorization-mode=Webhook --client-ca-file=/etc/kubernetes/pki/ca.crt"
Environment="KUBELET_CGROUP_ARGS=--cgroup-driver=systemd"
Environment="KUBELET_CERTIFICATE_ARGS=--rotate-certificates=true --cert-dir=/var/lib/kubelet/pki"
ExecStart=
ExecStart=/usr/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_SYSTEM_PODS_ARGS $KUBELET_NETWORK_ARGS $KUBELET_DNS_ARGS $KUBELET_AUTHZ_ARGS $KUBELET_CADVISOR_ARGS $KUBELET_CGROUP_ARGS $KUBELET_CERTIFICATE_ARGS $KUBELET_EXTRA_ARGS
```


## grafana 
```shell
docker run -d -p 3000:3000 --name grafana grafana:grafana
wget https://grafana.com/api/plugins/grafana-kubernetes-app/versions/1.0.1/download
unzip grafana-kubernetes-app-31da38a.zip
docker cp grafana-kubernetes-app-31da38a/ grafana:/var/lib/grafana/plugins/
docker restart grafana
```


## Q&A
https://github.com/prometheus/prometheus/wiki/FAQ#error-file-already-closed

WAL log samples: log series: write /data/wal/000003: file already closed

log series: no space left on device

```shell
/data/wal $ ls
000001  000005  000009  000013  000017  000021  000025  000029  000033  000037  000041  000045  000049  000053  000057  000061  000065  000069  000073  000077  000081  000085  000089  000093  000097
000002  000006  000010  000014  000018  000022  000026  000030  000034  000038  000042  000046  000050  000054  000058  000062  000066  000070  000074  000078  000082  000086  000090  000094  000098
000003  000007  000011  000015  000019  000023  000027  000031  000035  000039  000043  000047  000051  000055  000059  000063  000067  000071  000075  000079  000083  000087  000091  000095  000099
000004  000008  000012  000016  000020  000024  000028  000032  000036  000040  000044  000048  000052  000056  000060  000064  000068  000072  000076  000080  000084  000088  000092  000096  000100
/data/wal $ pwd
```

