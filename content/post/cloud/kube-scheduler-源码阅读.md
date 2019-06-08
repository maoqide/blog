---
title: "Kube Scheduler 源码阅读"
date: "2019-03-07T20:00:30+08:00"
author: "Maoqide"
tags: ["cloud", "kubernetes", "source-code"]
draft: false
---


k8s kube-scheduler 源码阅读笔记 
<!--more--> 

```golang
NewSchedulerCommand()
	runCommand()
		opts.Config()	// create client & informer
		func Run(cc schedulerserverconfig.CompletedConfig, stopCh <-chan struct{}) error {}
			run := func(ctx context.Context) {}
				sched.Run()
				// Run begins watching and scheduling. It waits for cache to be synced, then starts a goroutine and returns immediately.
				func (sched *Scheduler) Run() {}
					go wait.Until(sched.scheduleOne, 0, sched.config.StopEverything)
					// scheduleOne does the entire scheduling workflow for a single pod.
					func (sched *Scheduler) scheduleOne() {}
						pod := sched.config.NextPod()
						sched.schedule(pod)
							func (sched *Scheduler) schedule(pod *v1.Pod) (string, error) {}
								host, err := sched.config.Algorithm.Schedule(pod, sched.config.NodeLister)
									// Schedule tries to schedule the given pod to one of the nodes in the node list.
									// If it succeeds, it will return the name of the node.
									// If it fails, it will return a FitError error with reasons.
									// generic algorithm
									func (g *genericScheduler) Schedule(pod *v1.Pod, nodeLister algorithm.NodeLister) (string, error) {}
										// podPassesBasicChecks makes sanity checks on the pod if it can be scheduled.
										// 检查 pod 是否使用 pvc，且 pvc 是否可用
										podPassesBasicChecks(pod, g.pvcLister)
										// Computing predicates, 并发筛选符合 predicates 的节点
										filteredNodes, failedPredicateMap, err := g.findNodesThatFit(pod, nodes)
											// Filters the nodes to find the ones that fit based on the given predicate functions
											// Each node is passed through the predicate functions to determine if it is a fit
											func (g *genericScheduler) findNodesThatFit(pod *v1.Pod, nodes []*v1.Node) ([]*v1.Node, FailedPredicateMap, error) {}
													fits, failedPredicates, err := podFitsOnNode(pod, meta, g.cachedNodeInfoMap[nodeName], g.predicates, g.schedulingQueue, g.alwaysCheckAllPredicates,)
													workqueue.ParallelizeUntil(ctx, 16, int(allNodes), checkNode)
														// podFitsOnNode checks whether a node given by NodeInfo satisfies the given predicate functions.
														// For given pod, podFitsOnNode will check if any equivalent pod exists and try to reuse its cached
														// predicate results as possible.
														// This function is called from two different places: Schedule and Preempt.
														// When it is called from Schedule, we want to test whether the pod is schedulable
														// on the node with all the existing pods on the node plus higher and equal priority
														// pods nominated to run on the node.
														// When it is called from Preempt, we should remove the victims of preemption and
														// add the nominated pods. Removal of the victims is done by SelectVictimsOnNode().
														// It removes victims from meta and NodeInfo before calling this function.
														func podFitsOnNode(
															pod *v1.Pod,
															meta predicates.PredicateMetadata,
															info *schedulernodeinfo.NodeInfo,
															predicateFuncs map[string]predicates.FitPredicate,
															queue internalqueue.SchedulingQueue,
															alwaysCheckAllPredicates bool,
														) (bool, []predicates.PredicateFailureReason, error) {

										// Prioritizing, 
										priorityList, err := PrioritizeNodes(pod, g.cachedNodeInfoMap, metaPrioritiesInterface, g.prioritizers, filteredNodes, g.extenders)
											// PrioritizeNodes prioritizes the nodes by running the individual priority functions in parallel.
											// Each priority function is expected to set a score of 0-10
											// 0 is the lowest priority score (least preferred node) and 10 is the highest
											// Each priority function can also have its own weight
											// The node scores returned by the priority function are multiplied by the weights to get weighted scores
											// All scores are finally combined (added) to get the total weighted scores of all nodes
											func PrioritizeNodes(
												pod *v1.Pod,
												nodeNameToInfo map[string]*schedulernodeinfo.NodeInfo,
												meta interface{},
												priorityConfigs []algorithm.PriorityConfig,
												nodes []*v1.Node,
												extenders []algorithm.SchedulerExtender,
											) (schedulerapi.HostPriorityList, error) {}
											// PrioritizeNodes prioritizes the nodes by running the individual priority functions in parallel.
											// Each priority function is expected to set a score of 0-10
											// 0 is the lowest priority score (least preferred node) and 10 is the highest
											// Each priority function can also have its own weight
											// The node scores returned by the priority function are multiplied by the weights to get weighted scores
											// All scores are finally combined (added) to get the total weighted scores of all nodes
											func PrioritizeNodes(
												pod *v1.Pod,
												nodeNameToInfo map[string]*schedulernodeinfo.NodeInfo,
												meta interface{},
												priorityConfigs []algorithm.PriorityConfig,
												nodes []*v1.Node,
												extenders []algorithm.SchedulerExtender,
											) (schedulerapi.HostPriorityList, error) {}
										// Selecting host
										g.selectHost(priorityList)
											// selectHost takes a prioritized list of nodes and then picks one
											// in a round-robin manner from the nodes that had the highest score.
											func (g *genericScheduler) selectHost(priorityList schedulerapi.HostPriorityList) (string, error) {}

```

- Predicate 算法：pkg\scheduler\algorithm\predicates    
- Priority 算法：pkg\scheduler\algorithm\priorities