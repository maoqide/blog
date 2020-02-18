---
title: "Golang Gc & Memory Allocation"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["think"]
date: 2020-02-18T17:20:47+08:00
draft: true
---

关于 Golang GC 和内存管理相关的流程和原理的总结。    
<!--more-->

## GC 流程
![](/media/posts/golang/golang-gc/GC-Algorithm-Phases.png)    

## STW

## 写屏障

## GC触发

## 内存分配
	堆：有引用到的内存空间，靠 GC 回收。    
	栈：函数内部执行中声明的变量，函数执行完毕即回收。    

## 内存逃逸
逃逸场景