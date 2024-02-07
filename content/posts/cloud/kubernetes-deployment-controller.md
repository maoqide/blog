---
title: "Kubernetes Deployment Controller"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["think"]
date: 2021-05-23T14:16:27+08:00
draft: true
---

Cut out summary from your post content here.

<!--more-->

DeploymentController
Informer: Deployment, Rs, POd
SyncDeployment

getReplicaSetsForDeployment
	adopt/release rs for deployment
	return current adopted rs

getPodMapForDeployment
	returns the Pods managed by a Deployment by rs.UID

if d.DeletionTimestamp != nil { 
	syncStatusOnly
		getAllReplicaSetsAndSyncRevision(..., createIfNotExisted=false)
		calculateStatus
}


checkPausedConditions


if paused
	sync
		**getAllReplicaSetsAndSyncRevision(... , createIfNotExisted=true)**
	return

if scale
	sync
		**getAllReplicaSetsAndSyncRevision(... , createIfNotExisted=true)**
	return



rolloutRecreate || rolloutRolling
	getAllReplicaSetsAndSyncRevision()
		NewRSNewReplicas()


---
rolloutRolling
	reconcileNewReplicaSet

		maxTotalPods=deployment.Spec.Replicas+maxSurge
		if currentPodCount >= maxTotalPods {
			// cannot scale up
		}
		scaleUpCount = min(maxTotalPods-currentPodCount, deployment.Spec.Replicas-newRS.Spec.Replicas)

	reconcileOldReplicaSets

		minAvailable=deployment.Spec.Replicas-maxUnavailable
		newRSUnavailablePodCount=newRS.Spec.Replicas-newRS.Status.AvailableReplicas
		maxScaledDown=allPodsCount-minAvailable-newRSUnavailablePodCount
		if maxScaledDown <= 0 { return }
		maxScaledDown > 0:
			cleanupUnhealthyReplicas
			scaleDownOldReplicaSetsForRollingUpdate


