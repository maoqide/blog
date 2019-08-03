---
title: "Go Concurrency"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["golang", "concurrency"]
date: 2019-07-20T21:38:08+08:00
---

go 语言相比其他语言的一大优势，就是便捷，高效的并发代码的编写。本文具体介绍 go 语言的并发机制和使用 go 语言作并发编程的方法。    

<!--more--> 

## 并发模型
- 线程与锁          
- Actor     
  Actor 模型是一种并发运算上的模型。“actor”是一种程序上的抽象概念，被视为并发运算的基本单元：当一个actor接收到一则消息，它可以做出一些决策、创建更多的actor、发送更多的消息、决定要如何回答接下来的消息。    
- *CSP*(communicating sequential processes)    
  通信顺序进程，与 Actor 模型类似，区别是 CSP 不关心收发消息的实体，只关心传送消息的通道(channel)。    

  **golang 的并发基于 CSP 模型。**    


	*推荐书籍：《七周七并发模型》*    

## goroutine 调度
### MPG
- G: goroutine, 保存协程的状态，及执行时所需的栈空间信息。   
- P: processor, 保存 goroutine 的队列，能够进行 goroutine 的调度，可以控制并行的 goroutine 数量。    
- M: machine, 系统线程, goroutine G 会通过 P 被调度到 M 上执行。       

具体关系如下图:    
![](/media/posts/golang/go-concurrency/golang-GPM.jpg)     

### 调度
- 系统调用    
  如果G被阻塞在某个system call操作上，那么不光G会阻塞，执行该G的M也会解绑P(实质是被sysmon抢走了)，与G一起进入sleep状态。如果此时有idle的M，则P与其绑定继续执行其他G；如果没有idle M，但仍然有其他G要去执行，那么就会创建一个新M。
- channel/IO    
  如果G被阻塞在某个channel操作或network I/O操作上时，G会被放置到某个wait队列中，而M会尝试运行下一个runnable的G；如果此时没有runnable的G供m运行，那么m将解绑P，并进入sleep状态。。当I/O available或channel操作完成，在wait队列中的G会被唤醒，标记为runnable，放入到某P的队列中，绑定一个M继续执行。
- 抢占调度    
	sysmon向长时间运行(10ms)的G任务发出抢占调度，一旦G的抢占标志位被设为true，那么待这个G下一次调用函数或方法时，runtime便可以将G抢占，并移出运行状态，放入P的local runq中，等待下一次被调度。    

### sysmon
Go程序启动时，runtime会去启动一个名为sysmon的m(一般称为监控线程)，该m无需绑定p即可运行，每20us~10ms启动一次，主要负责以下工作：    
- 释放闲置超过5分钟的span物理内存；    
- 如果超过2分钟没有*垃圾回收*，强制执行；    
- 将长时间未处理的netpoll结果添加到任务队列；    
- 向长时间运行的G任务发出*抢占调度*；    
- 收回因syscall长时间阻塞的P；    

## 用法
### goroutine
goroutine有一个简单的模型：它是一个与同一地址空间中的其他 goroutine 同时执行的函数。goroutine 是轻量级的，初始分配的空间很小，可以根据需要动态的分配（和释放）堆存储空间。    
goroutine 的用法：    
```golang
go func(){
	// do something
}()
```

### channel
上面的例子非常简单，在实际的项目中不太适用，因为 goroutine 无法发送信号告送其他函数，自己何时结束，以及执行的结果，此时，我们就需要 channel 了。     

初始化一个channel（channel 分为有缓冲和无缓冲）：    
```golang
ci := make(chan int)            // unbuffered channel of integers
cj := make(chan int, 0)         // unbuffered channel of integers
cs := make(chan *os.File, 100)  // buffered channel of pointers to Files
```

channel 的一般用法：    
```golang
c := make(chan int)  // Allocate a channel.
// Start the sort in a goroutine; when it completes, signal on the channel.
go func() {
    list.Sort()
    c <- 1  // Send a signal; value does not matter.
}()
doSomethingForAWhile()
<-c   // Wait for sort to finish; discard sent value.
```
`c <- 1` channel 在`<-`符号左边，表示向 channel 发送数据，`<- c` channel 在`<-`右边表示接收数据，此时左边可以有相应类型的变量负责接收数据，否则默认丢弃数据。    
channel 的接收端会一直阻塞，直到有数据发送过来。    
如果是无缓冲 channel，则发送端会在发送数据后阻塞，直到接收端接收到该值。如果是有缓冲 channel，则发送端仅会在缓冲区满时阻塞，如果缓冲区已满，则表示等待某个接收端接收到某个值。    

示例1:    
```golang
var sem = make(chan int, MaxOutstanding)

func handle(r *Request) {
    sem <- 1    // Wait for active queue to drain.
    process(r)  // May take a long time.
    <-sem       // Done; enable next request to run.
}

func Serve(queue chan *Request) {
    for {
        req := <-queue
        go handle(req)  // Don't wait for handle to finish.
    }
}
```
示例1 有一个问题，即使 channel 缓冲区有最大值的限制，但是每进来一个请求，但是 server 创建的 goroutine 并没有限制，理论上有可能会有无限个 goroutine 同时运行，所以我们需要修改 Server 限制下并行的 goroutine 数量。    

示例2: 
```golang
func Serve(queue chan *Request) {
    for req := range queue {
        sem <- 1
        go func() {
            process(req) // Buggy; see explanation below.
            <-sem
        }()
    }
}
```
当缓存区满时，`sem <- 1` 会阻塞，不会再创建新的 goroutine。但是示例2还存在一个问题：在 golang 的 `for` 循环中，循环变量是在每次循环中复用的，所以`req`变量会被所有 goroutine 共享，这会导致最终所有请求都是一样的。这个问题可以通过闭包来解决：   

示例3:     
```golang
func Serve(queue chan *Request) {
    for req := range queue {
        sem <- 1
        go func(req *Request) {
            process(req)
            <-sem
        }(req)
    }
}
```

*另一种解决思路，多个 worker：*     
```golang
func handle(queue chan *Request) {
    for r := range queue {
        process(r)
    }
}
func Serve(clientRequests chan *Request, quit chan bool) {
    // Start handlers
    for i := 0; i < MaxOutstanding; i++ {
        go handle(clientRequests)
    }
    <-quit  // Wait to be told to exit.
}
```

### Channels of channels
channel 本身也是 go 语言中的原生类型之一，也可以通过 channel 进行传递。这个特性可以让我们很方便的实现很多有用的功能。    
示例1（非阻塞并行RPC框架）:     
```golang
type Request struct {
    args        []int
    f           func([]int) int
    resultChan  chan int
}

// 调用端
func sum(a []int) (s int) {
    for _, v := range a {
        s += v
    }
    return
}
request := &Request{[]int{3, 4, 5}, sum, make(chan int)}
// Send request
clientRequests <- request
// Wait for response.
fmt.Printf("answer: %d\n", <-request.resultChan)


// Server 端
func handle(queue chan *Request) {
    for req := range queue {
        req.resultChan <- req.f(req.args)
    }
}
func Serve(clientRequests chan *Request, quit chan bool) {
    // Start handlers
    for i := 0; i < MaxOutstanding; i++ {
        go handle(clientRequests)
    }
    <-quit  // Wait to be told to exit.
}
```

示例2(类unix管道特性，流式处理):     
```golang
type PipeData struct {
    value int
    handler func(int) int
    next chan int
}

// 流式处理
func handle(queue chan *PipeData) {
	for data := range queue {
		data.next <- data.handler(data.value)
	}
}
```

## pprof
golang 内置了 runtime/pprof 包可以对代码进行性能分析和监控，并在此基础上封装了 net/http/proof 包，web 项目只要引用这个包，web 服务中就会自动添加 debug/pprof 的路径，可以进行基本的性能分析。    
如果是使用内置 net/http 包的 web 服务，直接在 main 函数中引入`_ "net/http/pprof"`，就可以直接在浏览器的 debug/pprof/ 路径中查看 pprof 信息。    
如果是使用的其他第三方的 go web 框架，则需要手动在路由中添加对应路径，例如 gin 中可以这样添加 https://github.com/gin-contrib/pprof/blob/master/pprof.go 。      

通过 pprof 包，再加上 go tool pprof 工具，就可以方便的对 go 程序中的性能信息进行分析。     
首先启动一个引用了 net/http/proof 包的 web 项目，该项目监听 8080 端口。     
启动后可以使用 [hey](https://github.com/rakyll/hey) 模拟 web 请求。`hey -z 2m -c 10  -q 2 -H 'token: xxxxxxxxxx' 'http://127.0.0.1:8080/xxx'`     
在请请求期间，执行 `go tool pprof test http://127.0.0.1:8080/v1/debug/pprof/profile`（其中 test 为 web 服务编译后的二进制文件），就可以获取在此期间的性能信息。如下所示：     
```shell
File: engine
Type: cpu
Time: Aug 3, 2019 at 3:23pm (CST)
Duration: 30s, Total samples = 580ms ( 1.93%)
Entering interactive mode (type "help" for commands, "o" for options)
(pprof) top
Showing nodes accounting for 460ms, 79.31% of 580ms total
Showing top 10 nodes out of 210
      flat  flat%   sum%        cum   cum%
     120ms 20.69% 20.69%      120ms 20.69%  syscall.syscall
     110ms 18.97% 39.66%      110ms 18.97%  runtime.pthread_cond_wait
      60ms 10.34% 50.00%       60ms 10.34%  runtime.pthread_cond_signal
      40ms  6.90% 56.90%       40ms  6.90%  runtime.kevent
      40ms  6.90% 63.79%       40ms  6.90%  runtime.nanotime
      20ms  3.45% 72.41%       20ms  3.45%  encoding/json.checkValid
      20ms  3.45% 75.86%       20ms  3.45%  runtime.notetsleep
      10ms  1.72% 77.59%       10ms  1.72%  encoding/json.(*decodeState).literalStore
      10ms  1.72% 79.31%       10ms  1.72%  encoding/json.stateInString
(pprof) 
```
其中 Duration: 30s 为性能信息采集的时间，默认为30s，在执行 pprof 时可指定参数，`go tool pprof test http://127.0.0.1:8080/debug/pprof/profile?seconds=60`调整时间。    
在 pprof 交互式命令行中，输入 top 可以查看耗时的函数，结果如上，每一行表示一个函数的信息。前两列表示函数在 CPU 上运行的时间以及百分比；第三列是当前所有函数累加使用 CPU 的比例；第四列和第五列代表这个函数以及子函数运行所占用的时间和比例（也被称为累加值 cumulative），应该大于等于前两列的值；最后一列就是函数的名字。如果应用程序有性能问题，上面这些信息应该能告诉我们时间都花费在哪些函数的执行上了。     
输入 web 命令，能够生成一张 svg 格式整个应用的函数调用关系图，可以直接用浏览器打开，并且图中代表函数的框越大，表示该函数执行的时间越长。    
还有其他有用的命令，可以输入 help 查看。     
例子中获取的是 profile 信息，还可以通过其他 debug url，获取其他信息如 goroutine、heap 等，`go tool pprof http://127.0.0.1:8080/debug/pprof/heap`。     

除了交互式命令行，go tool pprof 还提供了 web 页面，上面的命令加上 -http 参数，`go tool pprof -http=":8081" engine http://127.0.0.1:8080/debug/pprof/profile`，即可在指定端口启动一个 web 服务，通过 web 服务可以查看整个应用程序的各种性能信息及图表分析，火焰图等。    

参考：    
- https://golang.org/doc/effective_go.html#concurrency     
- https://tonybai.com/2017/06/23/an-intro-about-goroutine-scheduler/    
