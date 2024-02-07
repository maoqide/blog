---
title: "The Go Memory Model"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["golang"]
date: 2019-06-19T09:10:37+08:00
draft: false
---

[译]https://golang.google.cn/ref/mem     

Go内存模型指定了一个条件，在该条件下，可以保证在一个 goroutine 中读取变量，能够获取到另一个不同 goroutine 写入同一变量产生的值。    

<!--more-->

## Introduction
Go内存模型指定了一个条件，在该条件下，可以保证在一个 goroutine 中读取变量，能够获取到另一个不同 goroutine 写入同一变量产生的值。    

## Advice
如果一个程序要修改被多个 goroutine 同时访问的数据，必须序列化此类访问。    

要序列化访问，请使用 channel 操作或其他同步原语（例如`sync`和`sync/atomic`包中的那些）来保护数据。    

如果您必须阅读本文档的其余部分以了解程序的行为，那么您就太聪明了。    

别聪明。    

## Happens Before
在单个 goroutine 中，读取和写入必须表现得好像它们按程序指定的顺序执行。也就是说，只有当重新排序不改变语言规范中定义的 goroutine 的行为时，编译器和处理器才可以对在单个 goroutine 中读取和写入操作的执行进行重新排序。由于这种重新排序，一个 goroutine 观察到的执行顺序可能与另一个 goroutine 感知到的顺序不同。例如，如果一个 goroutine 执行`a = 1; b = 2;`，另一个 goroutine 可能会在 a 的值更新之前观察到 b 的更新值。    

为了指定读取和写入的要求，我们定义 发生之前(hanppen before)，Go 程序中内存操作的局部顺序。如果事件 e1 在事件 e2 发生之前(hanppen before)，那么我们说事件 e2 在事件 e1 发生之后(hanppen after)。另外，如果 e1 在 e2 之前没有发生并且在 e2 之后没有发生，那么我们说 e1 和 e2 同时发生。    

在单个goroutine中，`happens-before` 顺序是程序表达的顺序。     

如果以下两个都成立，则允许变量 v 的读取操作 r 观察到写入操作 w 写入到 v 的值：    
	1. r 没有发生在 w 之前。    
	2. 在 w 之后但在 r 之前没有其他写入操作 w'。    

为了保证对变量 v 的读取操作 r 观察到特定写入操作 w 对 v 写入的值，确保 w 是允许读取操作 r 观察到的唯一的写入操作。也就是说，如果以下两个条件都成立，才能保证读取操作 r 能够观察到写入操作 w：    
	1. w 发生在 r 之前。    
	2. 任何其他对共享变量 v 的写入操作，要么发生在 w 之前，要么发生在 r 之后。    

这组条件比第一组更加严格。它要求没有其他写入与 w 或 r 同时发生。    

在单个goroutine中，没有并发，因此这两个定义是等效的：一个读取操作 r 观察最近的写入操作 w 写入 v 的值。    

具有零值的 v 的类型的变量 v 的初始化表现为以上存储模型中的写入。    

对于大于单个机器字的值的读取和写入操作，表现为以未指定顺序进行的多个 机器字大小的操作。     

## Synchronization
### Initialization
程序的初始化在单个 goroutine 中运行，但该 goroutine 可能会创建其他并发运行的 goroutine。    

如果包 p 导入包 q，则 q 的 init 函数在包 p 的任何代码开始之前完成。    

函数 main.main 在所有的 init 函数完成后开始执行。    

### Goroutine creation
启动新 goroutine 的 go 语句发生在该 goroutine 开始执行之前。    

例如，在此程序中：    
```golang
var a string

func f() {
	print(a)
}

func hello() {
	a = "hello, world"
	go f()
}
```
调用`hello`将在未来的某个时刻打印“hello，world”（也许在`hello`返回之后）。    

### Goroutine destruction
goroutine 的退出不保证在程序中的任何事件之前发生。例如，在此程序中：    
```golang
var a string

func hello() {
	go func() { a = "hello" }()
	print(a)
}
```
对 a 的赋值没有伴随任何同步事件，因此不保证任何其他 goroutine 都能观察到它。事实上，一个激进的编译器可能会删掉整条 go 语句。    

如果一个 goroutine 影响必须被另一个 goroutine 观察到，要使用锁或 channel 通信等同步机制来建立相对顺序。    

### Channel communication
channel 通信是 goroutine 之间同步的主要方法。特定 channel 上的每一个 send 操作都与该 channel 对应的 receive 操作相匹配，通常在不同的 goroutine 中。    
	
#### channel 的 send 在该 channel 相应的 receive 操作完成之前发生       

示例程序：    
```golang
var c = make(chan int, 10)
var a string

func f() {
	a = "hello, world"
	c <- 0
}

func main() {
	go f()
	<-c
	print(a)
}
```
保证打印出 "hello, world"。对 a 的写入发生在 c 的 send 之前，即发生在 c 的相应的 receive 完成之前，即发生在`print`之前。    

#### channel 的关闭发生在因通道已关闭而接收到零值返回之前    

在前面的示例中，用` close(c)`替换`c <- 0`会产生具有保证同样行为的程序。    

无缓冲 channel 的 receive 操作在该 channel 的 send 操作完成之前发生。    

示例程序(和上面一样，但是交换了 send 和 receive 语句并且使用了无缓冲的 channel)：    
```golang
var c = make(chan int)
var a string

func f() {
	a = "hello, world"
	<-c
}

func main() {
	go f()
	c <- 0
	print(a)
}
```
同样保证打印出 "hello, world"。对 a 的写入发生在 c 的 receive 之前，即发生在 c 的相应的 send 完成之前，即发生在`print`之前。    

如果 channel 是有缓冲的，（例如，c = make(chan int, 1)），那么程序将不能保证打印 "hello, world"。（可能会打印空字符串，崩溃或执行其他操作。）    

*具有容量`C`的 channel 的第 `k` 次 receive 操作，在第 `k+C` 次 send 操作完成之前。*     
此规则概括了先前的有缓冲的 channel 的规则。它允许用有缓冲的 channel 建立的计数信号量：channel 中的 data 数量对应于当前的使用数量，channel 的容量对应于允许最大同时使用的数量，发送一条 data 来获取信号量，接收一条 data 来释放信号量。这是限制并发数量的常用用法。    

该程序为工作列表中的每个条目启动一个 goroutine，但是 goroutine 利用`limit`这个 channel 来确保一次最多有三个正在运行的`work`函数。    
```golang
var limit = make(chan int, 3)

func main() {
	for _, w := range work {
		go func(w func()) {
			limit <- 1
			w()
			<-limit
		}(w)
	}
	select{}
}
```

### Locks
`sync`包实现了两种锁的类型，`sync.Mutex` 和 `sync.RWMutex`。    

**对于任何`sync.Mutex`或`sync.RWMutex`类型的变量`l`，并且n < m，第n次调用`l.Unock()`在第m次调用`l.Lock()`返回之前发生。**    
示例程序：    
```golang
var l sync.Mutex
var a string

func f() {
	a = "hello, world"
	l.Unlock()
}

func main() {
	l.Lock()
	go f()
	l.Lock()
	print(a)
}
```
保证打印出"hello, world"。第一次调用` l.Unlock() `（在f()中），在第二次调用`l.Lock()`（在main()中）返回之前发生，即在`print`之前发生。    

For any call to l.RLock on a sync.RWMutex variable l, there is an n such that the l.RLock happens (returns) after call n to l.Unlock and the matching l.RUnlock happens before call n+1 to l.Lock.

对于`sync.RWMutex`类型的变量`l`的`l.RLock()`的任意调用，有一个 n 使得本次`l.RLock()`在第 n 次调用`l.Unlock()`之后发生（返回）并且对应的`l.RUnlock()`在第 n+1 调用`l.Lock()`之前发生。    

### Once
`sync`包通过使用Once类型，在存在多个 goroutine 的情况下提供了一种安全的初始化机制。多个线程可以对特定的 f 执行`nce.Do(f)`，但是只有一个线程会真正运行`f()`，并且其他调用会阻塞直到`f()`返回。    

**从`once.Do(f) `中对`f()`的单次调用在任意`once.Do(f)`的调用之前发生（返回）。**    
在如下程序中：    
```golang
var a string
var once sync.Once

func setup() {
	a = "hello, world"
}

func doprint() {
	once.Do(setup)
	print(a)
}

func twoprint() {
	go doprint()
	go doprint()
}
```
调用`twoprint()`将只会调用`setup()`一次。setup 方法将在`print`之前完成。结果是"hello, world"将被打印两次。    

## Incorrect synchronization
注意，读取操作 r 可以观察到与r同时发生的写入操作 w 所写的值。即使发生这种情况，也不意味着在 r 之后发生的读取操作将观察到在 w 之前发生的写入操作。    
如下程序中：    
```golang
var a, b int

func f() {
	a = 1
	b = 2
}

func g() {
	print(b)
	print(a)
}

func main() {
	go f()
	g()
}
```
可能会发生 g 先打印 2 然后打印 0。     

这使一些常见的管用语法无效。    

双重检查锁 是为了避免同步的开销。    
例如，`twoprint`程序可能被错误的写为：     
```golang
var a string
var done bool

func setup() {
	a = "hello, world"
	done = true
}

func doprint() {
	if !done {
		once.Do(setup)
	}
	print(a)
}

func twoprint() {
	go doprint()
	go doprint()
}
```
但是这不能保证，在`doprint`中，观察到`done`的写入操作意味着同样能观察到对`a`的写入操作。这个版本可能（错误地）打印空字符串而不是"hello，world"。     

另一个不正确的惯用语法是忙着等待一个值，如：    
```golang
var a string
var done bool

func setup() {
	a = "hello, world"
	done = true
}

func main() {
	go setup()
	for !done {
	}
	print(a)
}
```
像之前一样，不能保证在`main`中，观察到`done`的写入操作意味着同样能观察到对`a`的写入操作，因此这个程序也可能打印出空的字符串。更糟的是，还无法保证`main`能观察到对`done`的写入操作，因为两个线程之间没有同步事件。`main`中的循环无法保证能完成。     

这个主题有更微妙的变体，例如这个程序：    
```golang
type T struct {
	msg string
}

var g *T

func setup() {
	t := new(T)
	t.msg = "hello, world"
	g = t
}

func main() {
	go setup()
	for g == nil {
	}
	print(g.msg)
}
```
即使`main`观察到`g != nil`并且退出循环，无法保证它会观察到`g.msg`的初始化值。    

在所有这些示例中，解决方案是相同的：使用显式的同步。    
