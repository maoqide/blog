---
title: "Golang Mutex"
date:  2019-03-11T16:35:20+08:00
author: "Maoqide"
tags: ["golang"]
#draft: true
---

golang 的`sync`包中有两种锁，互斥锁`sync.Mutex` 和读写锁`sync.RWMutex`。    
<!--more-->

## sync.Mutex
- Mutex 为互斥锁，`Lock()` 加锁，`Unlock()` 解锁    
- 使用 `Lock()` 加锁后，在使用`Unlock()`解锁前便不能再次对其进行加锁，否则会导致死锁    
- 在`Lock()`前使用`Unlock()`会导致 panic 异常    
- 适用于读写不确定场景，即读写次数没有明显的区别，并且只允许只有一个读或者写的场景    

## sync.RWMutex
- RWMutex 是单写多读锁，可以加多个读锁或者一个写锁    
- 读锁占用的情况下会阻止写，不会阻止读，多个 goroutine 可以同时获取读锁     
- 写锁会阻止其他 goroutine（无论读和写）进来，整个锁由该 goroutine 独占    
- 适用于读多写少的场景     

### Lock()/Unlock() 
- `Lock()` 加写锁，`Unlock()` 解写锁     
- 写锁权限高于读锁，有写锁时优先加写锁      
- 在 `Lock()` 之前使用 `Unlock()` 会导致 panic 异常    

### RLock()/RUnlock()
- `RLock()` 加读锁，`RUnlock()` 解读锁    
- `RLock()` 加读锁时，如果存在写锁，则无法加读锁；当只有读锁或者没有锁时，可以加读锁，读锁可以加多个    
- `RUnlock()` 解读锁，`RUnlock()` 撤销单次 `RLock()` 调用，对于其他同时存在的读锁没有作用    
- 不能在没有读锁的情况下调用`RUnlock()`，`RUnlock()`不得多于`RLock()`，否则会导致 panic 异常    


	参考：https://blog.csdn.net/chenbaoke/article/details/41957725