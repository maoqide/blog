---
title: "Golang Websocket Message Pushing"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["golang", "websocket"]
date: 2020-01-11T20:49:24+08:00
draft: false
---

使用 golang 的 websocket 框架 [melody](https://github.com/olahol/melody)，实现通用的消息分组推送服务。针对同一推送对象，只起一个后端协程进行广播推送，减少资源消耗，并提供监控接口查询当前的协程和websocket连接。    
github：[ws-notifier](https://github.com/maoqide/ws-notifier)    
<!--more-->

## melody
melody 是一个 golang 的 websocket 框架，通过对 [websocket](https://github.com/gorilla/websocket) 包装，实现方便的广播或推送消息给多个指定的 session。     

## ws-notifier
ws-notifier 在 melody 的基础上，通过给 Session 添加特定的key，实现对特定的 group 的消息推送，并实现负责后端推送的 worker 和 group 的关联，对同一group只需起一个 worker 的 goroutine 进行推送，减少后端推送的资源消耗。     

## example
### handler
[https://github.com/maoqide/ws-notifier/tree/master/example](https://github.com/maoqide/ws-notifier/tree/master/example)     
使用 golang 的 ticker 对不同组的客户端推送消息，同一组的客户端推送消息相同。     
```golang
n := notifier.Default()
```
使用 default 配置获取默认配置的 notifier 实例。    

```golang
	//...
	group := strings.Trim(r.RequestURI, "/")
	// should be random generated
	sessionID := "123456"
	// ...
```
使用请求 URL 的 path 作为 group 的标识，随机生成的唯一 ID 作为 session 的标识，通过 group 对同一组的客户端广播，通过 sessionID 可对某一客户端单独推送。    
```golang
	// n.Notify 启动后端推送 worker，如果已经启动则直接返回
	n.Notify(groupID, tickerWorker, time.Hour*24)

	n.HandleRequestWithKeys(w, r, map[string]interface{}{"group": groupID, "id": groupID + "_" + sessionID})
```
`HandleRequestWithKeys`传入对应 groupID 和 sessionID，将 session 加入 melody 的 hub 中管理，并使 group 和 sessionID 生效。    

### worker
```golang
func tickerWorker(groupID string, sigChan chan int8, n *notifier.Notifier) error {
	worker := fmt.Sprintf("ticker_worker_%s_%d", groupID, time.Now().Unix())
	fmt.Printf("worker: %s\n", worker)

	defer func() {
		select {
		case sigChan <- 0:
			log.Printf("ticker worker: %s exit", worker)
		case <-time.After(time.Second * 3):
			log.Printf("ticker worker: %s exit after 3s delaying", worker)
		}
	}()
	// ...
}
```
worker 退出前，要向外部管理 goroutine 发送退出信号，以便 notifier 回收内部 worker map的 worker，待下一个 session 连接时启动新的 worker。    
```golang
for {
	// ...
	select {
		case signal := <-sigChan:
			log.Printf("receice stop signal %d for ticker worker: %s", signal, worker)
			return nil
		case <-ticker.C:
			// ...
		}
	// ...
	}
```
推送过程中，接收信号 channel，当收到退出信号后退出循环。    
