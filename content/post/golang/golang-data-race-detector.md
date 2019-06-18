---
title: "Golang Data Race Detector"
author: "Maoqide"
tags: ["golang"]
date: 2019-06-18T09:26:13+08:00
---

[译] https://golang.google.cn/doc/articles/race_detector.html     

golang 中的几种 Data Race 场景及 Data Race 检测工具。    
<!--more-->

## Introduction
数据竞争是并发系统中最常见和最难 debug 的 bug 类型之一，当两个 goroutine 同时访问同一个变量并且至少有一个是写入时，就会发生 data race(数据竞争)。详细内容可以阅读[The Go Memory Model](https://golang.google.cn/ref/mem/)。    
以下是可能导致崩溃和内存损坏的 data race 示例：    
```golang
func main() {
	c := make(chan bool)
	m := make(map[string]string)
	go func() {
		m["1"] = "a" // First conflicting access.
		c <- true
	}()
	m["2"] = "b" // Second conflicting access.
	<-c
	for k, v := range m {
		fmt.Println(k, v)
	}
}
```

## Usage
为了帮助诊断此类错误，Go 包含一个内置的 data race detector。要使用它，请在go命令中添加-race标志：    
```shell
$ go test -race mypkg    // to test the package
$ go run -race mysrc.go  // to run the source file
$ go build -race mycmd   // to build the command
$ go install -race mypkg // to install the package
```

# Report Format 
当 data race detector 在程序中发现有 data race 时，它会打印一个报告。该报告包含冲突访问的堆栈跟踪，以及创建相关 goroutine 的堆栈。以下一个例子：    
```shell
WARNING: DATA RACE
Read by goroutine 185:
  net.(*pollServer).AddFD()
      src/net/fd_unix.go:89 +0x398
  net.(*pollServer).WaitWrite()
      src/net/fd_unix.go:247 +0x45
  net.(*netFD).Write()
      src/net/fd_unix.go:540 +0x4d4
  net.(*conn).Write()
      src/net/net.go:129 +0x101
  net.func·060()
      src/net/timeout_test.go:603 +0xaf

Previous write by goroutine 184:
  net.setWriteDeadline()
      src/net/sockopt_posix.go:135 +0xdf
  net.setDeadline()
      src/net/sockopt_posix.go:144 +0x9c
  net.(*conn).SetDeadline()
      src/net/net.go:161 +0xe3
  net.func·061()
      src/net/timeout_test.go:616 +0x3ed

Goroutine 185 (running) created at:
  net.func·061()
      src/net/timeout_test.go:609 +0x288

Goroutine 184 (running) created at:
  net.TestProlongTimeout()
      src/net/timeout_test.go:618 +0x298
  testing.tRunner()
      src/testing/testing.go:301 +0xe8
```

## Options
环境变量 `GORACE` 用来设置 data race detector 选项，格式如下：    
```shell
GORACE="option1=val1 option2=val2"
```

option 有：    
- `log_path` (default `stderr`): race detector 将其报告写入名为`log_path.pid`的文件。`stdout`和`stderr` 分别让报告写入标准输出和标准错误。    
- `exitcode` (default `66`): 检测到的 race 后使用的退出状态码。    
- `strip_path_prefix` (default `""`): 从所有报告的文件路径中删除此前缀，以使报告更简洁。    
- `history_size` (default `1`): 每个 goroutine 内存访问历史记录是`32K * 2**history_size elements`。加大此值可以避免“无法还原堆栈”错误报告，但会增加内存使用量。    
- `halt_on_error` (default `0`): 控制在报告第一次数据竞争后程序是否退出。    

示例：    
```shell
$ GORACE="log_path=/tmp/race/report strip_path_prefix=/my/go/sources/" go test -race
```

## Excluding Tests
当使用 `-race` 标志构建时，go 命令定义了额外的[构建参数](https://golang.google.cn/pkg/go/build/#hdr-Build_Constraints)`race`。运行 race detector 时，你可以使用此标记排除某些代码和测试。下面是一些实例：    
```golang
// +build !race

package foo

// The test contains a data race. See issue 123.
func TestFoo(t *testing.T) {
	// ...
}

// The test fails under the race detector due to timeouts.
func TestBar(t *testing.T) {
	// ...
}

// The test takes too long under the race detector.
func TestBaz(t *testing.T) {
	// ...
}
```

To start, run your tests using the race detector (go test -race). The race detector only finds races that happen at runtime, so it can't find races in code paths that are not executed. If your tests have incomplete coverage, you may find more races by running a binary built with -race under a realistic workload.

## How To Use 
首先，使用 race detector 运行测试(`go test -race`)。race detector 仅查找运行时发生的 race，因此无法在未执行的代码路径中找到 race，如果你的测试覆盖率不完全，在实际工作负载下运行使用`-race`构建的二进制文件，你可能会发现更多的 race。    

## Typical Data Races 
以下是一些典型的 data race 场景。所有这些都可以通过 race detector 检测到：    

### Race on loop counter(循环计数器竞争)
```golang
func main() {
	var wg sync.WaitGroup
	wg.Add(5)
	for i := 0; i < 5; i++ {
		go func() {
			fmt.Println(i) // Not the 'i' you are looking for.
			wg.Done()
		}()
	}
	wg.Wait()
}
```

函数传参中的变量`i`与 for 循环使用的变量相同，因此 goroutine 中的读取与循环的自增产生 race（此程序通常会打印出 55555，而不是 01234）。zhegewenti可以通过对变量`i`进行复制来修复；    
```golang
func main() {
	var wg sync.WaitGroup
	wg.Add(5)
	for i := 0; i < 5; i++ {
		go func(j int) {
			fmt.Println(j) // Good. Read local copy of the loop counter.
			wg.Done()
		}(i)
	}
	wg.Wait()
}
```
### Accidentally shared variable(意外的共享变量)
```golang
// ParallelWrite writes data to file1 and file2, returns the errors.
func ParallelWrite(data []byte) chan error {
	res := make(chan error, 2)
	f1, err := os.Create("file1")
	if err != nil {
		res <- err
	} else {
		go func() {
			// This err is shared with the main goroutine,
			// so the write races with the write below.
			// 此 err 变量和主 goroutine 共享，所以此写入和下面的写入产生 race。
			_, err = f1.Write(data)
			res <- err
			f1.Close()
		}()
	}
	f2, err := os.Create("file2") // The second conflicting write to err.
	if err != nil {
		res <- err
	} else {
		go func() {
			_, err = f2.Write(data)
			res <- err
			f2.Close()
		}()
	}
	return res
}
```

修复方法是在 goroutines 中引入新变量（注意使用 :=）：    
```golang
			...
			_, err := f1.Write(data)
			...
			_, err := f2.Write(data)
			...
```

### Unprotected global variable(无保护的全局变量)
如果有多个 goroutine 调用以下代码，则会导致 map类型的变量`service`产生 race。并发读取和写入同一个 map 是不安全的：    
```golang
var service map[string]net.Addr

func RegisterService(name string, addr net.Addr) {
	service[name] = addr
}

func LookupService(name string) net.Addr {
	return service[name]
}
```

为了使代码安全，用互斥锁`mutex`来保护访问权限：    
```golang
var (
	service   map[string]net.Addr
	serviceMu sync.Mutex
)

func RegisterService(name string, addr net.Addr) {
	serviceMu.Lock()
	defer serviceMu.Unlock()
	service[name] = addr
}

func LookupService(name string) net.Addr {
	serviceMu.Lock()
	defer serviceMu.Unlock()
	return service[name]
}
```

### Primitive unprotected variable(原始无保护变量)
data race 也可能发生在原始类型的变量上（bool，int，int64 等），如下例所示：    
```golang
type Watchdog struct{ last int64 }

func (w *Watchdog) KeepAlive() {
	w.last = time.Now().UnixNano() // First conflicting access.
}

func (w *Watchdog) Start() {
	go func() {
		for {
			time.Sleep(time.Second)
			// Second conflicting access.
			if w.last < time.Now().Add(-10*time.Second).UnixNano() {
				fmt.Println("No keepalives for 10 seconds. Dying.")
				os.Exit(1)
			}
		}
	}()
}
```

即使是这种“无辜的” data race 也会导致难以调试的问题，这些问题是由存储器访问的非原子性，编译器优化的干扰或访问处理器存储的重新排序问题引起的。    

这种 data race 的典型修复方法是使用 channel 或 mutex。为了保持无锁行为，还可以使用`sync/atomic`包。    
```golang
type Watchdog struct{ last int64 }

func (w *Watchdog) KeepAlive() {
	atomic.StoreInt64(&w.last, time.Now().UnixNano())
}

func (w *Watchdog) Start() {
	go func() {
		for {
			time.Sleep(time.Second)
			if atomic.LoadInt64(&w.last) < time.Now().Add(-10*time.Second).UnixNano() {
				fmt.Println("No keepalives for 10 seconds. Dying.")
				os.Exit(1)
			}
		}
	}()
}
```

## Supported Systems
Trace detector 可以运行在 darwin/amd64, freebsd/amd64, linux/amd64 和 windows/amd64.    

## Runtime Overhead
竞争检测的成本因程序而异，但对于一个典型的程序，内存使用量可能增加5-10倍，执行时间增加2-20倍。    
