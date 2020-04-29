---
title: "Kubernetes Events"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["kubernetes", "source code", "event", "kubernetes event"]
date: 2020-04-25T16:38:17+08:00
draft: true
---

通过源码探究 kubernetes 如何记录和存储集群中的大量事件信息。    
<!--more-->

## 收
```golang
// kubelet 为例，所有需要记录事件的组件都需要调用 StartRecordingToSink
// cmd/kubelet/app/server.go
func makeEventRecorder(kubeDeps *kubelet.Dependencies, nodeName types.NodeName) {
	// ...
	eventBroadcaster.StartRecordingToSink(&v1core.EventSinkImpl{Interface: kubeDeps.EventClient.Events("")})

	// ...
}

// 1. staging/src/k8s.io/client-go/tools/record/event.go
func (e *eventBroadcasterImpl) StartRecordingToSink(sink EventSink) watch.Interface{}

	// 2. StartEventWatcher starts sending events received from this EventBroadcaster to the given event handler function.
	func (e *eventBroadcasterImpl) StartEventWatcher(eventHandler func(*v1.Event)) watch.Interface {}

	// 3. eventHandler -> recordToSink
	func recordToSink(sink EventSink, event *v1.Event, eventCorrelator *EventCorrelator, sleepDuration time.Duration) {}

		// 4.
		result, err := eventCorrelator.EventCorrelate(event)
			c.aggregator.EventAggregate(newEvent)
		recordEvent(sink, result.Event, result.Patch, result.Event.Count > 1, eventCorrelator)
 
```

## Kubelet 如何发出 BirthCry
### BirthCry
```golang
// Kubelet BirthCry as example
// BirthCry sends an event that the kubelet has started up.
func (kl *Kubelet) BirthCry() {
	// Make an event that kubelet restarted.
	kl.recorder.Eventf(kl.nodeRef, v1.EventTypeNormal, events.StartingKubelet, "Starting kubelet.")
}

// vendor/k8s.io/client-go/tools/record/event.go
type EventRecorder interface {}
```
kubernetes 几乎每个组件都会发送事件信息，以 kubelet 为例，当 kubelet 启动时，会调用一个 BirthCry 方法，此方法会发送一个事件，方法命名非常形象，代表 kubelet 在启动。那么这个事件是如何发出的呢。    
通过源码阅读，发现发送事件通过`Kubelet.recorder`，该类实现了`record.EventRecorder`接口，接口具体定义在 client-go/tools/record/event.go 中，主要定义了如下发送事件的几个方法。    
```golang
// EventRecorder knows how to record events on behalf of an EventSource.
type EventRecorder interface {
	// The resulting event will be created in the same namespace as the reference object.
	Event(object runtime.Object, eventtype, reason, message string)

	// Eventf is just like Event, but with Sprintf for the message field.
	Eventf(object runtime.Object, eventtype, reason, messageFmt string, args ...interface{})

	// PastEventf is just like Eventf, but with an option to specify the event's 'timestamp' field.
	PastEventf(object runtime.Object, timestamp metav1.Time, eventtype, reason, messageFmt string, args ...interface{})

	// AnnotatedEventf is just like eventf, but with annotations attached
	AnnotatedEventf(object runtime.Object, annotations map[string]string, eventtype, reason, messageFmt string, args ...interface{})
}
```

### makeEventRecorder
recorder 的初始化过程调用了 makeEventRecorder 方法，`eventBroadcaster.NewRecorder`方法返回了一个`record.EventRecorder`接口的具体实现，并且指定的事件发送的来源，这里来源组件为 Kubelet。
可以看到此方法先 New 了一个 `record.EventBroadcaster`，再通过 eventBroadcaster 生成一个 `record.EventRecorder`，这里 NewRecorder 主要是指定该 recorder 发送的 Event 事件中的来源，即 Component 和 Host，StartLogging 和 StartRecordingToSink 都是 eventBroadcaster 的方法，会调用 StartEventWatcher，接受发送过来的事件信息，并调用 eventHandler 方法对事件进行处理，具体过程下面会分析，这里 StartLogging 主要用于 klog 记录日志，StartRecordingToSink 会对事件进行聚合并存储。    
*(一个 chan 如何同时被两个 watcher 接收)*    
```golang
// makeEventRecorder sets up kubeDeps.Recorder if it's nil. It's a no-op otherwise.
func makeEventRecorder(kubeDeps *kubelet.Dependencies, nodeName types.NodeName) {
	if kubeDeps.Recorder != nil {
		return
	}
	eventBroadcaster := record.NewBroadcaster()
	kubeDeps.Recorder = eventBroadcaster.NewRecorder(legacyscheme.Scheme, v1.EventSource{Component: componentKubelet, Host: string(nodeName)})
	eventBroadcaster.StartLogging(klog.V(3).Infof)
	if kubeDeps.EventClient != nil {
		klog.V(4).Infof("Sending events to api server.")
		eventBroadcaster.StartRecordingToSink(&v1core.EventSinkImpl{Interface: kubeDeps.EventClient.Events("")})
	} else {
		klog.Warning("No api server defined - no events will be sent to API server.")
	}
}
```

### recorder
`record.EventRecorder`接口的定义已经在上面贴出来了，这里看一下 kubelet 中使用的 recorder 的具体实现。上面说到 kubelet 调用 makeEventRecorder New 出了一个`record.EventRecorder `实例并赋值给了`kubeDeps.Recorder`，这就是 kubelet中使用的 recorder， 具体的实现为私有类`recorderImpl`，定义在 client-go/tools/record/event.go。
私有方法 generateEvent 负责发送事件，执行 recorder.Action 将 event 加入 Broadcaster 的 incoming 队列，实现消息发送，这里 Action 是 recorder 结构体中包含的`*watch.Broadcaster`定义的方法， incoming 也是`*watch.Broadcaster`中定义的一个带缓存的 channel。这个`*watch.Broadcaster`在下面的 EventBroadcaster 中还会提到，它是真正负责事件处理的组件。    
```golang
type recorderImpl struct {
	scheme *runtime.Scheme
	source v1.EventSource
	*watch.Broadcaster
	clock clock.Clock
}

// generateEvent 调用 recorder.Action 发送事件
func (recorder *recorderImpl) generateEvent(object runtime.Object, annotations map[string]string, timestamp metav1.Time, eventtype, reason, message string) {
	ref, err := ref.GetReference(recorder.scheme, object)
	if err != nil {
		klog.Errorf("Could not construct reference to: '%#v' due to: '%v'. Will not report event: '%v' '%v' '%v'", object, err, eventtype, reason, message)
		return
	}

	if !util.ValidateEventType(eventtype) {
		klog.Errorf("Unsupported event type: '%v'", eventtype)
		return
	}

	event := recorder.makeEvent(ref, annotations, eventtype, reason, message)
	event.Source = recorder.source

	go func() {
		// NOTE: events should be a non-blocking operation
		defer utilruntime.HandleCrash()
		recorder.Action(watch.Added, event)
	}()
}
func (recorder *recorderImpl) Event(object runtime.Object, eventtype, reason, message string) {
	recorder.generateEvent(object, nil, metav1.Now(), eventtype, reason, message)
}
func (recorder *recorderImpl) Eventf(object runtime.Object, eventtype, reason, messageFmt string, args ...interface{}) {
	recorder.Event(object, eventtype, reason, fmt.Sprintf(messageFmt, args...))
}
func (recorder *recorderImpl) PastEventf(object runtime.Object, timestamp metav1.Time, eventtype, reason, messageFmt string, args ...interface{}) {
	recorder.generateEvent(object, nil, timestamp, eventtype, reason, fmt.Sprintf(messageFmt, args...))
}
func (recorder *recorderImpl) AnnotatedEventf(object runtime.Object, annotations map[string]string, eventtype, reason, messageFmt string, args ...interface{}) {
	recorder.generateEvent(object, annotations, metav1.Now(), eventtype, reason, fmt.Sprintf(messageFmt, args...))
}

// ... ...
// Action distributes the given event among all watchers.
func (m *Broadcaster) Action(action EventType, obj runtime.Object) {
	m.incoming <- Event{action, obj}
}
```

### EventBroadcaster
eventBroadcasterImpl 是 `record.EventBroadcaster` 的具体实现，结构体定义如下，包含了一个`*watch.Broadcaster`，makeEventRecorder 中调用了 `eventBroadcaster.StartRecordingToSink` 方法，该方法又调用了 StartEventWatcher，进行 event 监听。    
```golang
type eventBroadcasterImpl struct {
	*watch.Broadcaster
	sleepDuration time.Duration
	options       CorrelatorOptions
}

// StartRecordingToSink starts sending events received from the specified eventBroadcaster to the given sink.
// The return value can be ignored or used to stop recording, if desired.
// TODO: make me an object with parameterizable queue length and retry interval
func (e *eventBroadcasterImpl) StartRecordingToSink(sink EventSink) watch.Interface {
	eventCorrelator := NewEventCorrelatorWithOptions(e.options)
	return e.StartEventWatcher(
		func(event *v1.Event) {
			recordToSink(sink, event, eventCorrelator, e.sleepDuration)
		})
}

// StartEventWatcher starts sending events received from this EventBroadcaster to the given event handler function.
// The return value can be ignored or used to stop recording, if desired.
func (e *eventBroadcasterImpl) StartEventWatcher(eventHandler func(*v1.Event)) watch.Interface {
	watcher := e.Watch()
	go func() {
		defer utilruntime.HandleCrash()
		for watchEvent := range watcher.ResultChan() {
			event, ok := watchEvent.Object.(*v1.Event)
			if !ok {
				// This is all local, so there's no reason this should
				// ever happen.
				continue
			}
			eventHandler(event)
		}
	}()
	return watcher
}
```

### watch.Broadcaster
根据上面的分析，recorder 通过调用`*watch.Broadcaster`的 Action 方法将 event 发送到 Broadcaster 的 incoming 队列完成发送，EventBroadcaster 的 StartRecordingToSink 方法，最终调用到了`*watch.Broadcaster`的 Watch 方法，对事件进行监听。可以看到在事件的传递中，`*watch.Broadcaster`是一个非常重要的部分，根据命名可以才到，它的作用就是对事件进行广播。那么 `*watch.Broadcaster` 是如何接收 recorder 发送的事件并广播给所有的 watcher 呢？    
`*watch.Broadcaster`定义在 apimachinery/pkg/watch/mux.go。下面贴出了结构体定义和初始化的方法。    
可以看到 incoming 队列是通过 `make(chan Event, incomingQueueLength)` 初始化，这是一个带缓存的通道，缓存大小为 incomingQueueLength，值固定为25。对 incomingQueueLength 的定义，代码里解释为*通常情况下传入的队列很少会阻塞，这里加上缓冲，是为了防止万一在一个很短的窗口内接收到事件导致Broadcaster无法及时处理*。还有一个重要的 map 类型 `watchers`，它用来存储已经注册进来的 watcher，当 incoming 队列中收到消息，会对 watchers 中所有的 broadcasterWatcher 进行广播，int64 类型的`nextWatcher`作为 map 中 watcher 的 key，每新增一个 watcher，nextWatcher 自增加一，并作为新增 watcher 的 id，同时可以看到为了防止并发产生异常，watcher 相关的操作都做了加锁操作，这就是`*watch.Broadcaster`广播的基本原理。具体的实现可以看下 Watch 方法的逻辑，EventBroadcaster 最终调用到 Watch 方法，Watch 方法创建一个 broadcasterWatcher 加入 watchers，并返回给调用方，调用方拿到 watcher 调用 `watcher.ResultChan()` 监听事件。    
到这里事件如何通过 Broadcaster 进行发送和监听就已经比较清晰了，还有一个问题，就是 Broadcaster 进行广播的动作，是在何时开始的呢？其实在 NewBroadcaster() 的时候，已经在最后执行了`go m.loop()`，loop() 方法中做的事情，就是从 incoming 队列中取出队列，并推送给所有的 watcher，代码也贴出在下面，可以自己看下方法中的具体逻辑。    
```golang
// Broadcaster distributes event notifications among any number of watchers. Every event
// is delivered to every watcher.
type Broadcaster struct {
	// TODO: see if this lock is needed now that new watchers go through
	// the incoming channel.
	lock sync.Mutex

	watchers     map[int64]*broadcasterWatcher
	nextWatcher  int64
	distributing sync.WaitGroup

	incoming chan Event

	// How large to make watcher's channel.
	watchQueueLength int
	// If one of the watch channels is full, don't wait for it to become empty.
	// Instead just deliver it to the watchers that do have space in their
	// channels and move on to the next event.
	// It's more fair to do this on a per-watcher basis than to do it on the
	// "incoming" channel, which would allow one slow watcher to prevent all
	// other watchers from getting new events.
	fullChannelBehavior FullChannelBehavior
}
// NewBroadcaster creates a new Broadcaster. queueLength is the maximum number of events to queue per watcher.
// It is guaranteed that events will be distributed in the order in which they occur,
// but the order in which a single event is distributed among all of the watchers is unspecified.
func NewBroadcaster(queueLength int, fullChannelBehavior FullChannelBehavior) *Broadcaster {
	m := &Broadcaster{
		watchers:            map[int64]*broadcasterWatcher{},
		incoming:            make(chan Event, incomingQueueLength),
		watchQueueLength:    queueLength,
		fullChannelBehavior: fullChannelBehavior,
	}
	m.distributing.Add(1)
	go m.loop()
	return m
}

// Action distributes the given event among all watchers.
func (m *Broadcaster) Action(action EventType, obj runtime.Object) {
	m.incoming <- Event{action, obj}
}

// watcher 的注册和维护
// Watch adds a new watcher to the list and returns an Interface for it.
// Note: new watchers will only receive new events. They won't get an entire history
// of previous events.
func (m *Broadcaster) Watch() Interface {
	var w *broadcasterWatcher
	m.blockQueue(func() {
		m.lock.Lock()
		defer m.lock.Unlock()
		id := m.nextWatcher
		m.nextWatcher++
		w = &broadcasterWatcher{
			result:  make(chan Event, m.watchQueueLength),
			stopped: make(chan struct{}),
			id:      id,
			m:       m,
		}
		m.watchers[id] = w
	})
	return w
}
// Execute f, blocking the incoming queue (and waiting for it to drain first).
// The purpose of this terrible hack is so that watchers added after an event
// won't ever see that event, and will always see any event after they are
// added.
func (b *Broadcaster) blockQueue(f func()) {
	var wg sync.WaitGroup
	wg.Add(1)
	b.incoming <- Event{
		Type: internalRunFunctionMarker,
		Object: functionFakeRuntimeObject(func() {
			defer wg.Done()
			f()
		}),
	}
	wg.Wait()
}

// 事件的广播
// loop receives from m.incoming and distributes to all watchers.
func (m *Broadcaster) loop() {
	// Deliberately not catching crashes here. Yes, bring down the process if there's a
	// bug in watch.Broadcaster.
	for event := range m.incoming {
		if event.Type == internalRunFunctionMarker {
			event.Object.(functionFakeRuntimeObject)()
			continue
		}
		m.distribute(event)
	}
	m.closeAll()
	m.distributing.Done()
}
// distribute sends event to all watchers. Blocking.
func (m *Broadcaster) distribute(event Event) {
	m.lock.Lock()
	defer m.lock.Unlock()
	if m.fullChannelBehavior == DropIfChannelFull {
		for _, w := range m.watchers {
			select {
			case w.result <- event:
			case <-w.stopped:
			default: // Don't block if the event can't be queued.
			}
		}
	} else {
		for _, w := range m.watchers {
			select {
			case w.result <- event:
			case <-w.stopped:
			}
		}
	}
}
```

### summary
通过从 kubelet 的 'BirthCry' 入手，分析了一个事件在 kubernetes 中的全部流程，同时其他组件的事件发送流程，也是大同小异，感兴趣的话可以自己选一个进行分析。另外，自己开发自定义的 controller 或其他自定义组件的时候，也可以尝试通过这一流程，将自己需要记录的事件，通过 kubernetes Event 的形式发送。    
