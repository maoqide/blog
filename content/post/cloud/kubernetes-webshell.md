---
title: "Kubernetes Webshell"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "webshell", "websocket", "xterm", "terminal"]
date: 2019-08-11T11:32:17+08:00
draft: true
---

通过 client-go 提供的方法，实现通过网页进入 kubernetes pod 的终端操作。    
<!--more-->

- client-go remotecommand    
- websocket    
- xterm.js

## remotecommand
`k8s.io/client-go/tools/remotecommand` kubernetes client-go 提供的 remotecommand 包，提供了方法与集群中的容器建立长连接，并设置容器的 stdin，stdout 等。     
remotecommand 包提供基于 [SPDY](https://en.wikipedia.org/wiki/SPDY) 协议的 Executor interface，进行和 pod 终端的流的传输。初始化一个 Executor 很简单，只需要调用 remotecommand 的 NewSPDYExecutor 并传入对应参数。    
Executor 的 Stream 方法，会建立一个流传输的连接，直到服务端和调用端一端关闭连接，才会停止传输。常用的做法是定义一个如下 `PtyHandler` 的 interface，然后使用你想用的客户端实现该 interface 对应的`Read(p []byte) (int, error)`和`Write(p []byte) (int, error)`方法即可，调用 Stream 方法时，只要将 StreamOptions 的 Stdin Stdout 都设置为 ptyHandler，Executor 就会通过你定义的 write 和 read 方法来传输数据。     
```golang
// PtyHandler
type PtyHandler interface {
	io.Reader
	io.Writer
	remotecommand.TerminalSizeQueue
}

// NewSPDYExecutor
req := kubeClient.CoreV1().RESTClient().Post().
		Resource("pods").
		Name(podName).
		Namespace(namespace).
		SubResource("exec")
req.VersionedParams(&corev1.PodExecOptions{
	Container: containerName,
	Command:   cmd,
	Stdin:     true,
	Stdout:    true,
	Stderr:    true,
	TTY:       true,
}, scheme.ParameterCodec)
executor, err := remotecommand.NewSPDYExecutor(cfg, "POST", req.URL())
if err != nil {
	log.Printf("NewSPDYExecutor err: %v", err)
	return err
}

// Stream
err = executor.Stream(remotecommand.StreamOptions{
		Stdin:             ptyHandler,
		Stdout:            ptyHandler,
		Stderr:            ptyHandler,
		TerminalSizeQueue: ptyHandler,
		Tty:               true,
	})
```

## websocket
[github.com/gorilla/websocket](https://github.com/gorilla/websocket) 是 go 的一个 websocket 实现，提供了全面的 websocket 相关的方法，这里使用它来实现上面所说的`PtyHandler`接口。    
首先定义一个 TerminalSession 类，该类包含一个 `*websocket.Conn`，通过 websocket 连接实现`PtyHandler`接口的读写方法，Next 方法在 remotecommand。    
```golang
// TerminalSession
type TerminalSession struct {
	wsConn   *websocket.Conn
	sizeChan chan remotecommand.TerminalSize
	doneChan chan struct{}
}

// Next called in a loop from remotecommand as long as the process is running
func (t *TerminalSession) Next() *remotecommand.TerminalSize {
	select {
	case size := <-t.sizeChan:
		return &size
	case <-t.doneChan:
		return nil
	}
}

// Read called in a loop from remotecommand as long as the process is running
func (t *TerminalSession) Read(p []byte) (int, error) {
	_, message, err := t.wsConn.ReadMessage()
	if err != nil {
		log.Printf("read message err: %v", err)
		return copy(p, webshell.EndOfTransmission), err
	}
	var msg webshell.TerminalMessage
	if err := json.Unmarshal([]byte(message), &msg); err != nil {
		log.Printf("read parse message err: %v", err)
		// return 0, nil
		return copy(p, webshell.EndOfTransmission), err
	}
	switch msg.Operation {
	case "stdin":
		return copy(p, msg.Data), nil
	case "resize":
		t.sizeChan <- remotecommand.TerminalSize{Width: msg.Cols, Height: msg.Rows}
		return 0, nil
	default:
		log.Printf("unknown message type '%s'", msg.Operation)
		// return 0, nil
		return copy(p, webshell.EndOfTransmission), fmt.Errorf("unknown message type '%s'", msg.Operation)
	}
}

// Write called from remotecommand whenever there is any output
func (t *TerminalSession) Write(p []byte) (int, error) {
	msg, err := json.Marshal(webshell.TerminalMessage{
		Operation: "stdout",
		Data:      string(p),
	})
	if err != nil {
		log.Printf("write parse message err: %v", err)
		return 0, err
	}
	if err := t.wsConn.WriteMessage(websocket.TextMessage, msg); err != nil {
		log.Printf("write message err: %v", err)
		return 0, err
	}
	return len(p), nil
}

// Close close session
func (t *TerminalSession) Close() error {
	return t.wsConn.Close()
}
```