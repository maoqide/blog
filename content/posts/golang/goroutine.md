---
title: "Goroutine 的管理"
date: 2018-12-28T16:29:32+08:00
author: "Maoqide"
tags: ["golang"]
draft: false
---

goroutine 是 go 的最重要特性之一，可以方便的实现并发编程。但是真正用起来，如果不多加注意，很容易造成 goroutine 的泄漏或者脱离管理，造成代码跑一段时间，就是产生大量无法回收的goroutine(可通过 [pprof](https://golang.org/pkg/net/http/pprof/) 查看)。最近学习整理了下 go 语言中管理 goroutine 的几种方法和一些最佳实践。     
<!--more-->


## 几点原则
[go-best-practices-concurrency](https://github.com/codeship/go-best-practices/tree/master/concurrency)    
在 github上的 [go-best-practices](https://github.com/codeship/go-best-practices) 项目中，提到了几点最佳实践，这里记录下。    
### 不要和 goroutine 失去联系
> Don't loose contact with your goroutines    

如何避免? 使用`make(chan struct{})`/`sync.WaitGroup`/`context.Context`或`select`。    
你可能需要这样：    
1. 当必要的时候可以*中断*创建的 goroutine。    
2. 等待直到产生的所有 goroutine 都完成了。    

**中断(Interruption)**    
可以用以下方式实现：    
1. 共享一个无缓冲的空结构体通道（`make（chan struct {}）`），由 goroutine 的创建者发出关闭信号以关闭。    
2. 一个可取消的`context.Context`。    
3. 确保你的 goroutine 使用`select`来不时检查他们的信号，而不会无限期地阻塞住。    

**等待 goroutine 完成(Waiting for goroutines to finish)**    
实现的最简单方法是使用`sync.WaitGroup`。在创建 goroutine 之前，请确保调用了`wg.Add(1)`。在运行 goroutine 之后，但在它 return 之前，请确保`wg.Done()`。这种场景下，`defer`是很好的选择。

### 不要用 WaitGroup 来计数多种类型的 goroutine
> Don't use wait groups to count more than one type of goroutine    

这里说的 gouroutine 的类型和被作为 gouroutine 调用的函数相关联，此函数可以是另一种类型的成员函数，可以是包中的命名函数，也可以是匿名函数。重要的一点是，你不应该在作为goroutine 调用的不同函数之间共享 WaitGroup。保持简单，如果你需要对一个不同类型的函数使用`go`关键字，创建一个新的 WaitGroup，并对它正确命名。     
```golang
type Parent struct {
  wgFoo sync.WaitGroup
  wgBar sync.WaitGroup
}

func (p *Parent) foo() {
  defer p.wgFoo.Done()
}

func (p *Parent) bar() {
  defer p.wgBar.Done()
}

func (p *Parent) Go() {
  p.wgFoo.Add(1)
  go p.foo()

  p.wgBar.Add(1)
  go.bar()
}
```
虽然共享一个 WaitGroup 可能是正确的解决方案，但是当下一位工程师接受时，它会增加问题的认知复杂性。    

### 不要让一个 channel 的消费者说什么时候结束
> Don't let a channel consumer say when it is done    
    
*对一个已关闭的 channel 发送会导致 panic*    
首先且最重要的是，代码是基于 channel 的消费者和生产者模型的实现，这本身就是一种很好的做法。这是一个明显的关注点分离。    
golang 给你在编译时定义一个 channel 的方向的能力`recvOnly <-chan Thing := make(chan Thing)`。这在定义变量时很少有用，但是，在定义函数的接收参数时非常有用。比如：
```golang
func consume(things <-chan Thing) {
  // will do work until close
  for thing := range things {
    // do work
  }
}
```
这强制（在编译时）消费者 goroutine 无法在对 channel 发送数据，包括关闭该 channel 的能力。    
这强制顶一个租户(goroutine)安全管理 channel。只有当所有生产者停止发送，才关闭 channel。谨记对**一个已关闭的 channel 发送会导致 panic**。    

**关闭 channel 的代码必须选保证不会再对此 channel 发送**    
> The piece of code which closes a channel must first guarantee that nothing else will produce on it    

如果所有对 channel 的发送都在关闭前同步发生，只要你不重试并再次发送，那就是安全的。    
如果该 channel 上的生产(production)被放弃到其他 goroutine，那么你需要能够与这些 goroutine 同步退出。    

如果我们可以保证对 goroutine 进行计数并等待它们退出，那么我们可以确定关闭 channel 不会在其他地方引起 panic。    
```golang
func doConcurrently() {
  var (
    things   = make(chan Thing)
    finished = make(chan struct{})
    wg       sync.WaitGroup
  )

  go func() {
    // will consume until close
    consume(things)
    // signal consumption has finished
    close(finished)
  }()

  for i := 0; i < noOfThingsWeWantToDo; i++ {
    wg.Add(1)
    go func() {
      defer wg.Done()

      things <- Thing{}
    }()
  }
  
  // wait until all producers have stopped
  wg.Wait()

  // then you can close
  close(things)

  // wait until finished consuming
  <-finished
}
```
### 总结
1. 确保消费者只能消费。使用`recvOnly <-chan Thing` 。    
2. 跟踪 gouroutine 的完成。使用`sync.WaitGroup`。    
3. 只有在确认生产者 goroutine 不能再对 channel 进行发送的情况下，再关闭channel。    

## 从外部结束一个 goroutine
[参考][从外部结束一个 goroutine](https://gulu-dev.com/post/2016-02-02-kill-goroutine#toc_3)    

**可响应 channel 的 goroutine**    
最直接的方法是关闭与这个 goroutine 通信的 channel close(ch)。如果这个 goroutine 此时阻塞在 read 上，那么阻塞会失效，并在第二个返回值中返回 false (此时可以检测并退出)；如果阻塞在 write 上，那么会 panic，这时合理的做法是在 goroutine 的顶层 recover 并退出。
更健壮的设计一般会把 data channel (用于传递业务逻辑的数据) 和 signal channel (用于管理 goroutine 的状态) 分开。不会让 goroutine 直接读写 data channel，而是通过 select-default 或 select-timeout 来避免完全阻塞，同时周期性地在 signal channel 检查是否有结束的请求。    

**不可响应的 goroutine**    
1. 尽量使用 Non-blocking IO (正如 go runtime 那样)    
2. 尽量使用阻塞粒度较小的 sys calls (对外部调用也一样)    
3. 业务逻辑总是考虑退出机制，编码时避免潜在的死循环    
4. 在合适的地方插入响应 channel 的代码，保持一定频率的 channel 响应能力    

## 使用 context
[GO Context blog](https://blog.golang.org/context)    
[GO Context pkg](https://golang.org/pkg/context/)    
对上面两篇文章的整理翻译。

### context
对一个 Go 服务，处理传入请求时应该创建一个`Context`，外部调用时应该接受一个`Context`。它们间的函数调用链必须传递`Context`，传递的 Context 也可以是使用`WithCancel`, `WithDeadline`, `WithTimeout`, or `WithValue`创建的继承来的`Context`。当一个`Context`被取消，所有继承它的`Context`也都会取消。    

```golang
// A Context carries a deadline, cancelation signal, and request-scoped values
// across API boundaries. Its methods are safe for simultaneous use by multiple
// goroutines.
type Context interface {
    // Done returns a channel that is closed when this Context is canceled
    // or times out.
    Done() <-chan struct{}

    // Err indicates why this context was canceled, after the Done channel
    // is closed.
    Err() error

    // Deadline returns the time when this Context will be canceled, if any.
    Deadline() (deadline time.Time, ok bool)

    // Value returns the value associated with key or nil if none.
    Value(key interface{}) interface{}
}
```
- `Done` 返回一个只读信道（channel），它是表示 Context 是否已关闭(cancel)的信号。    
- `Err` 返回`Context`被关闭的原因。    
- `Deadline` 让方法可以决定是否应该开始工作，如果剩下的时间太少，可能不需要运行。也可以使用 deadline 来设置IO操作的超时时间。    
- `Value` 方法允许`Context`绑定一个请求范围内(`request-scoped`)的数据。这个数据一定是线程安全的。    

`Context`没有 cancel 方法和`Done` 信道是只读的原因一样：接收关闭信号(signal)的方法(function)通常不是发送信号的方法，尤其是，当父操作为子操作启动 goroutine 时，这些子操作的 goroutine 不应该能够关闭父操作。相反，`WithCancel`方法提供了关闭新`Context`的方式。    

多个 goroutine 同时使用一个`Context`是安全的。代码可以将单个`Context`传递给任意数量的 goroutine，并关闭该`Conetxt`以向所有这些 goroutine 发出信号。    

### Derived contexts
`context`包提供了从现有`Context`中继承新的`Context`的方法。这些`Context`构成一个树：当一个`Context`被关闭(cancel)时，继承自它的所有`Context`都会被关闭。    

`Background` 是所有 Context 树的根，它永远不会关闭(cancel)：    
```golang
// Background returns an empty Context. It is never canceled, has no deadline,
// and has no values. Background is typically used in main, init, and tests,
// and as the top-level Context for incoming requests.
func Background() Context
```
`WithCancel`和`WithTimeout`返回派生的`Context`，这些值可以比父`Context`更早取消。通常在请求处理程序返回时关闭与传入请求相关联的`Context`。`WithCancel`对于在使用多个副本时关闭冗余请求很有用。`WithTimeout`对设置后端服务器请求的截止日期时很有用：    
```golang
/ WithCancel returns a copy of parent whose Done channel is closed as soon as
// parent.Done is closed or cancel is called.
func WithCancel(parent Context) (ctx Context, cancel CancelFunc)

// A CancelFunc cancels a Context.
type CancelFunc func()

// WithTimeout returns a copy of parent whose Done channel is closed as soon as
// parent.Done is closed, cancel is called, or timeout elapses. The new
// Context's Deadline is the sooner of now+timeout and the parent's deadline, if
// any. If the timer is still running, the cancel function releases its
// resources.
func WithTimeout(parent Context, timeout time.Duration) (Context, CancelFunc)
```
`WithValue`提供了一种将请求范围的值与`Context`绑定的方法：    
```golang
// WithValue returns a copy of parent whose Value method returns val for key.
func WithValue(parent Context, key interface{}, val interface{}) Context
```  

### 使用原则
*Programs that use Contexts should follow these rules to keep interfaces consistent across packages and enable static analysis tools to check context propagation:*    
	使用Context的程序包需要遵循如下的原则来满足接口的一致性以及便于静态分析:        
*Do not store Contexts inside a struct type; instead, pass a Context explicitly to each function that needs it. The Context should be the first parameter, typically named ctx*    
	**不要把 Context 存在一个结构体当中，显式地传入函数。Context变量需要作为第一个参数使用，一般命名为ctx**     
*Do not pass a nil Context, even if a function permits it. Pass context.TODO if you are unsure about which Context to use*    
	**即使方法允许，也不要传入一个 nil 的 Context，如果你不确定你要用什么 Context 的时候传一个 context.TODO**    
*Use context Values only for request-scoped data that transits processes and APIs, not for passing optional parameters to functions*    
	**使用context的Value相关方法只应该用于在程序和接口中传递的和请求相关的元数据，不要用它来传递一些可选的参数**    
*The same Context may be passed to functions running in different goroutines; Contexts are safe for simultaneous use by multiple goroutines.*    
	**同样的Context可以用来传递到不同的goroutine中，Context在多个goroutine中是安全的。**