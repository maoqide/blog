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
一个 event 在 kubernetes 中的完整历程
====
从 Kubelet 的 BirthCry 开始    
----

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
kubernetes 几乎每个组件都会发送事件信息，以 kubelet 为例，当 kubelet 启动时，会调用一个 BirthCry 方法，此方法会发送一个事件，方法命名非常形象，代表 kubelet 在启动。那么这个事件是如何发出的呢？    
通过源码阅读，发现发送事件通过`Kubelet.recorder`，该类实现了`record.EventRecorder`接口，接口具体定义在 `client-go/tools/record/event.go`中，主要定义了如下发送事件的几个方法。    
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
可以看到此方法先 New 了一个 `record.EventBroadcaster`，再通过 eventBroadcaster 生成一个 `record.EventRecorder`，这里 NewRecorder 时指定了该 recorder 发送的 Event 事件中的来源，即 Component 和 Host，StartLogging 和 StartRecordingToSink 都是 eventBroadcaster 的方法，会调用 StartEventWatcher，接受发送过来的事件信息，并调用 eventHandler 方法对事件进行处理，具体过程下面会分析，这里 StartLogging 主要用于 klog 记录日志，StartRecordingToSink 会对事件进行聚合并存储。    
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
`record.EventRecorder`接口的定义已经在上面贴出来了，这里看一下 kubelet 中使用的 recorder 的具体实现。上面说到 kubelet 调用 makeEventRecorder New 出了一个`record.EventRecorder `实例并赋值给了`kubeDeps.Recorder`，这就是 kubelet中使用的 recorder， 具体的实现为私有类`recorderImpl`，定义在`client-go/tools/record/event.go`。
私有方法 generateEvent 负责发送事件，执行 recorder.Action 将 event 加入 Broadcaster 的 incoming 队列，实现消息发送，这里 Action 是 recorder 结构体中包含的`*watch.Broadcaster`定义的方法， incoming 也是其中定义的一个带缓存的 channel。这个`*watch.Broadcaster`在下面的 EventBroadcaster 中还会提到，它是负责事件广播的组件。    
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
eventBroadcasterImpl 是 `record.EventBroadcaster` 的具体实现，结构体定义如下，包含了一个`*watch.Broadcaster`，kubelet 中 makeEventRecorder 中调用了 `eventBroadcaster.StartRecordingToSink` 方法，该方法又调用了 StartEventWatcher，进行 event 监听。    
*event aggregator*
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
根据上面的分析，recorder 通过调用`*watch.Broadcaster`的 Action 方法将 event 发送到 Broadcaster 的 incoming 队列完成发送，EventBroadcaster 的 StartRecordingToSink 方法，最终调用到了`*watch.Broadcaster`的 Watch 方法，对事件进行监听。可以看到在事件的传递中，`*watch.Broadcaster`是一个非常重要的部分，根据命名可以猜到，它的作用就是对事件进行广播。那么 `*watch.Broadcaster` 是如何接收 recorder 发送的事件并广播给所有的 watcher 呢？    
`*watch.Broadcaster`定义在`apimachinery/pkg/watch/mux.go`。下面贴出了结构体定义和初始化的方法。    
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

### EventSink
分析完一个事件在 kubernetes 中的发送和接收流程，还有最后一个问题，event 最终是如何存储到 ETCD 中，以什么形式存储到 ETCD 中的呢？再深一层追踪代码，可以发现一个 EventSink 的 interface，这个就是 kubernetes 提供的存储 Event 的接口，定义如下。    
```golang
// EventSink knows how to store events (client.Client implements it.)
// EventSink must respect the namespace that will be embedded in 'event'.
// It is assumed that EventSink will return the same sorts of errors as
// pkg/client's REST client.
type EventSink interface {
	Create(event *v1.Event) (*v1.Event, error)
	Update(event *v1.Event) (*v1.Event, error)
	Patch(oldEvent *v1.Event, data []byte) (*v1.Event, error)
}
```
`record.EventBroadcaster`的`StartRecordingToSink(sink EventSink) watch.Interface{}`方法，接收一个 EventSink 类型作为参数，这里回到 kubelet，看到 kubelet 初始化时在 makeEventRecorder 方法中调用这样调用`eventBroadcaster.StartRecordingToSink(&v1core.EventSinkImpl{Interface: kubeDeps.EventClient.Events("")})`，
传入的 EventSinkImpl，kubernetes 1.17 版本中结构体定义的注释中写了 TODO，后面要将所有 client 都移到 clientset 中。再往深层追踪，传入的`kubeDeps.EventClient.Events("")`，`kubeDeps.EventClient`初始化方法为`kubeDeps.EventClient, err = v1core.NewForConfig(&eventClientConfig)`，熟悉 kubernetes sdk 的可以看出来，这里创建的`corev1.CoreV1Client`，就是 clientset 中的客户端，
CoreV1Client.Event("") 返回的就是针对 Event 这一资源操作的 REST Client，封装了对 Event 增删改查的操作。由此可以看出，EventSink 其实就是连接 recorder 和底层存储的中间层，所以存入 ETCD 的操作，自然是 EventSink 来执行，甚至，如果你想将 kubernetes 的 event 存入其他数据库，只要封装一个对应的客户端，并实现 EventSink 的方法，就可以做到。    
```golang
// TODO: This is a temporary arrangement and will be removed once all clients are moved to use the clientset.
type EventSinkImpl struct {
	Interface EventInterface
}
func (e *EventSinkImpl) Create(event *v1.Event) (*v1.Event, error) {
	return e.Interface.CreateWithEventNamespace(event)
}
func (e *EventSinkImpl) Update(event *v1.Event) (*v1.Event, error) {
	return e.Interface.UpdateWithEventNamespace(event)
}
func (e *EventSinkImpl) Patch(event *v1.Event, data []byte) (*v1.Event, error) {
	return e.Interface.PatchWithEventNamespace(event, data)
}
```

### EventCorrelator
此时再回头看一下 StartRecordingToSink 方法。    
```golang
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

func recordToSink(sink EventSink, event *v1.Event, eventCorrelator *EventCorrelator, sleepDuration time.Duration) {
	// Make a copy before modification, because there could be multiple listeners.
	// Events are safe to copy like this.
	eventCopy := *event
	event = &eventCopy
	result, err := eventCorrelator.EventCorrelate(event)
	if err != nil {
		utilruntime.HandleError(err)
	}
	if result.Skip {
		return
	}
	tries := 0
	for {
		if recordEvent(sink, result.Event, result.Patch, result.Event.Count > 1, eventCorrelator) {
			break
		}
		tries++
		if tries >= maxTriesPerEvent {
			klog.Errorf("Unable to write event '%#v' (retry limit exceeded!)", event)
			break
		}
		// Randomize the first sleep so that various clients won't all be
		// synced up if the master goes down.
		if tries == 1 {
			time.Sleep(time.Duration(float64(sleepDuration) * rand.Float64()))
		} else {
			time.Sleep(sleepDuration)
		}
	}
}

// recordEvent attempts to write event to a sink. It returns true if the event
// was successfully recorded or discarded, false if it should be retried.
// If updateExistingEvent is false, it creates a new event, otherwise it updates
// existing event.
func recordEvent(sink EventSink, event *v1.Event, patch []byte, updateExistingEvent bool, eventCorrelator *EventCorrelator) bool {
	var newEvent *v1.Event
	var err error
	if updateExistingEvent {
		newEvent, err = sink.Patch(event, patch)
	}
	// Update can fail because the event may have been removed and it no longer exists.
	if !updateExistingEvent || (updateExistingEvent && util.IsKeyNotFoundError(err)) {
		// Making sure that ResourceVersion is empty on creation
		event.ResourceVersion = ""
		newEvent, err = sink.Create(event)
	}
	if err == nil {
		// we need to update our event correlator with the server returned state to handle name/resourceversion
		eventCorrelator.UpdateState(newEvent)
		return true
	}

	// If we can't contact the server, then hold everything while we keep trying.
	// Otherwise, something about the event is malformed and we should abandon it.
	switch err.(type) {
	case *restclient.RequestConstructionError:
		// We will construct the request the same next time, so don't keep trying.
		klog.Errorf("Unable to construct event '%#v': '%v' (will not retry!)", event, err)
		return true
	case *errors.StatusError:
		if errors.IsAlreadyExists(err) {
			klog.V(5).Infof("Server rejected event '%#v': '%v' (will not retry!)", event, err)
		} else {
			klog.Errorf("Server rejected event '%#v': '%v' (will not retry!)", event, err)
		}
		return true
	case *errors.UnexpectedObjectError:
		// We don't expect this; it implies the server's response didn't match a
		// known pattern. Go ahead and retry.
	default:
		// This case includes actual http transport errors. Go ahead and retry.
	}
	klog.Errorf("Unable to write event: '%v' (may retry after sleeping)", err)
	return false
}
```

#### NewEventCorrelator
在 StartEventWatcher 中传入的处理方法为 recordToSink，也就是说，当 watcher 接收到一个事件，会通过调用 recordToSink 进行处理。这里有一个新的结构体 EventCorrelator，顾名思义，它负责事件记录时的关联，作用主要是事件的过滤、聚合和计数。它有一个关键成员 aggregator，它用来对传入的事件进行聚合。关于 EventCorrelator 关联事件的具体规则，可以通过 populateDefaults 方法看到它的默认参数配置。具体每个参数的作用，后面再具体分析。    
```golang
// EventCorrelator 初始化
// EventCorrelator processes all incoming events and performs analysis to avoid overwhelming the system.  It can filter all
// incoming events to see if the event should be filtered from further processing.  It can aggregate similar events that occur
// frequently to protect the system from spamming events that are difficult for users to distinguish.  It performs de-duplication
// to ensure events that are observed multiple times are compacted into a single event with increasing counts.
type EventCorrelator struct {
	// the function to filter the event
	filterFunc EventFilterFunc
	// the object that performs event aggregation
	aggregator *EventAggregator
	// the object that observes events as they come through
	logger *eventLogger
}
// EventAggregator identifies similar events and aggregates them into a single event
type EventAggregator struct {
	sync.RWMutex

	// The cache that manages aggregation state
	cache *lru.Cache

	// The function that groups events for aggregation
	keyFunc EventAggregatorKeyFunc

	// The function that generates a message for an aggregate event
	messageFunc EventAggregatorMessageFunc

	// The maximum number of events in the specified interval before aggregation occurs
	maxEvents uint

	// The amount of time in seconds that must transpire since the last occurrence of a similar event before it's considered new
	maxIntervalInSeconds uint

	// clock is used to allow for testing over a time interval
	clock clock.Clock
}

// EventAggregatorByReasonFunc aggregates events by exact match on event.Source, event.InvolvedObject, event.Type and event.Reason
func EventAggregatorByReasonFunc(event *v1.Event) (string, string) {
	return strings.Join([]string{
		event.Source.Component,
		event.Source.Host,
		event.InvolvedObject.Kind,
		event.InvolvedObject.Namespace,
		event.InvolvedObject.Name,
		string(event.InvolvedObject.UID),
		event.InvolvedObject.APIVersion,
		event.Type,
		event.Reason,
	},
		""), event.Message
}
// EventAggregratorByReasonMessageFunc returns an aggregate message by prefixing the incoming message
func EventAggregatorByReasonMessageFunc(event *v1.Event) string {
	return "(combined from similar events): " + event.Message
}

// NewEventCorrelator returns an EventCorrelator configured with default values.
//
// The EventCorrelator is responsible for event filtering, aggregating, and counting
// prior to interacting with the API server to record the event.
//
// The default behavior is as follows:
//   * Aggregation is performed if a similar event is recorded 10 times in a
//     in a 10 minute rolling interval.  A similar event is an event that varies only by
//     the Event.Message field.  Rather than recording the precise event, aggregation
//     will create a new event whose message reports that it has combined events with
//     the same reason.
//   * Events are incrementally counted if the exact same event is encountered multiple
//     times.
//   * A source may burst 25 events about an object, but has a refill rate budget
//     per object of 1 event every 5 minutes to control long-tail of spam.
func NewEventCorrelator(clock clock.Clock) *EventCorrelator {
	cacheSize := maxLruCacheEntries
	spamFilter := NewEventSourceObjectSpamFilter(cacheSize, defaultSpamBurst, defaultSpamQPS, clock)
	return &EventCorrelator{
		filterFunc: spamFilter.Filter,
		aggregator: NewEventAggregator(
			cacheSize,
			EventAggregatorByReasonFunc,
			EventAggregatorByReasonMessageFunc,
			defaultAggregateMaxEvents,
			defaultAggregateIntervalInSeconds,
			clock),

		logger: newEventLogger(cacheSize, clock),
	}
}
func NewEventCorrelatorWithOptions(options CorrelatorOptions) *EventCorrelator {
	optionsWithDefaults := populateDefaults(options)
	spamFilter := NewEventSourceObjectSpamFilter(optionsWithDefaults.LRUCacheSize,
		optionsWithDefaults.BurstSize, optionsWithDefaults.QPS, optionsWithDefaults.Clock)
	return &EventCorrelator{
		filterFunc: spamFilter.Filter,
		aggregator: NewEventAggregator(
			optionsWithDefaults.LRUCacheSize,
			optionsWithDefaults.KeyFunc,
			optionsWithDefaults.MessageFunc,
			optionsWithDefaults.MaxEvents,
			optionsWithDefaults.MaxIntervalInSeconds,
			optionsWithDefaults.Clock),
		logger: newEventLogger(optionsWithDefaults.LRUCacheSize, optionsWithDefaults.Clock),
	}
}
// populateDefaults populates the zero value options with defaults
func populateDefaults(options CorrelatorOptions) CorrelatorOptions {
	if options.LRUCacheSize == 0 {
		// maxLruCacheEntries = 4096
		options.LRUCacheSize = maxLruCacheEntries
	}
	if options.BurstSize == 0 {
		// by default, allow a source to send 25 events about an object
		// but control the refill rate to 1 new event every 5 minutes
		// this helps control the long-tail of events for things that are always
		// unhealthy. defaultSpamBurst = 25
		// defaultSpamQPS   = 1. / 300.
		options.BurstSize = defaultSpamBurst
	}
	if options.QPS == 0 {
		options.QPS = defaultSpamQPS
	}
	if options.KeyFunc == nil {
		options.KeyFunc = EventAggregatorByReasonFunc
	}
	if options.MessageFunc == nil {
		options.MessageFunc = EventAggregatorByReasonMessageFunc
	}
	if options.MaxEvents == 0 {
		// if we see the same event that varies only by message
		// more than 10 times in a 10 minute period, aggregate the event.
		// defaultAggregateMaxEvents         = 10
		// defaultAggregateIntervalInSeconds = 600
		options.MaxEvents = defaultAggregateMaxEvents
	}
	if options.MaxIntervalInSeconds == 0 {
		options.MaxIntervalInSeconds = defaultAggregateIntervalInSeconds
	}
	if options.Clock == nil {
		options.Clock = clock.RealClock{}
	}
	return options
}
```

#### EventCorrelate
EventCorrelator 的关键方法是 EventCorrelate，它接收一个新的 Event 事件，并返回一个 EventCorrelateResult，代表关联后的结果。EventCorrelate 中首先执行了`c.aggregator.EventAggregate(newEvent)`方法进行事件聚合，它根据上面初始化 EventCorrelator 时的配置，检查是否已经有和传入的事件类似的事件。    

```golang
// EventCorrelateResult is the result of a Correlate
type EventCorrelateResult struct {
	// the event after correlation
	Event *v1.Event
	// if provided, perform a strategic patch when updating the record on the server
	Patch []byte
	// if true, do no further processing of the event
	Skip bool
}
// aggregateRecord holds data used to perform aggregation decisions
type aggregateRecord struct {
	// we track the number of unique local keys we have seen in the aggregate set to know when to actually aggregate
	// if the size of this set exceeds the max, we know we need to aggregate
	localKeys sets.String
	// The last time at which the aggregate was recorded
	lastTimestamp metav1.Time
}

// EventCorrelate filters, aggregates, counts, and de-duplicates all incoming events
func (c *EventCorrelator) EventCorrelate(newEvent *v1.Event) (*EventCorrelateResult, error) {
	if newEvent == nil {
		return nil, fmt.Errorf("event is nil")
	}
	aggregateEvent, ckey := c.aggregator.EventAggregate(newEvent)
	observedEvent, patch, err := c.logger.eventObserve(aggregateEvent, ckey)
	if c.filterFunc(observedEvent) {
		return &EventCorrelateResult{Skip: true}, nil
	}
	return &EventCorrelateResult{Event: observedEvent, Patch: patch}, err
}
```
这里具体梳理一下 EventAggregate 方法的流程。    
1. 首先，基于 event 事件的属性构建 key。    
	通过 getEventKey 方法基于 Event 的`的source`, `involvedObject`, `reason`, `message`的值构建一个该事件的唯一 key 作为 eventKey，然后通过`EventAggregator.keyFunc`生成aggregateKey 和 localKey，这里的 keyfunc 就是 NewEventCorrelator 传入的 keyFunc，即 EventAggregatorByReasonFunc，它基于 Event 的`event.Source`, `event.InvolvedObject`, `event.Type` 和 `event.Reason`的值构建 key，返回的 key 作为 aggregateKey，event.Message 作为 localKey。    
2. 接着，通过 aggregateKey 从 cache 中获取缓存的 record ，或新建一个 record。    
	e.cache 是一个 LRU 缓存，这里存储的值的类型是 aggregateRecord，取出值后，若该记录的时间即 aggregateRecord.lastTimestamp 距当前超过了 maxIntervalInSeconds（默认600s），那么该缓存无效。若缓存无效或缓存未空，则新建一个新的 record。   
3. 将第一步构建出的 localKey 加入 上一步得到的 record 的 localKeys，并更新缓存。这里 localKeys 为字符串集合，localKey即为 event.message，所以 c.cache 中实际上保存了同一 aggregateKey 下的事件的 message。    
4. 返回 event 和 cache key。    
	若当前 record 的`record.localKeys`的长度小于 maxEvents（默认10），即同一 aggregateKey 下的 localKeys 数量没达到最大阈值，这代表以 event.reason 维度做聚合产生的事件数没达到需要做关联聚合的阈值，那么此时不需对该事件进行聚合，直接返回传入的 event 不做需改，并直接以 eventKey 作为 cache key 返回，可以回顾一下第一步中生成 eventKey 的方法，是以完整的 reason 和 message 拼接成的 key。
	否则的话，当`record.localKeys`长度大于maxEvents，说明此时在一段时间内同一 reason 产生的事件较多，这时会先从 localKeys 中删除最老的值（PopAny）以保证长度不会大于maxEvents，并对事件进行聚合，组装一个新的事件返回，并以 aggregateKey 作为 cache key 返回。    

```golang
// EventAggregate checks if a similar event has been seen according to the
// aggregation configuration (max events, max interval, etc) and returns:
//
// - The (potentially modified) event that should be created
// - The cache key for the event, for correlation purposes. This will be set to
//   the full key for normal events, and to the result of
//   EventAggregatorMessageFunc for aggregate events.
func (e *EventAggregator) EventAggregate(newEvent *v1.Event) (*v1.Event, string) {
	now := metav1.NewTime(e.clock.Now())
	var record aggregateRecord
	// eventKey is the full cache key for this event
	eventKey := getEventKey(newEvent)
	// aggregateKey is for the aggregate event, if one is needed.
	aggregateKey, localKey := e.keyFunc(newEvent)

	// Do we have a record of similar events in our cache?
	e.Lock()
	defer e.Unlock()
	value, found := e.cache.Get(aggregateKey)
	if found {
		record = value.(aggregateRecord)
	}

	// Is the previous record too old? If so, make a fresh one. Note: if we didn't
	// find a similar record, its lastTimestamp will be the zero value, so we
	// create a new one in that case.
	maxInterval := time.Duration(e.maxIntervalInSeconds) * time.Second
	interval := now.Time.Sub(record.lastTimestamp.Time)
	if interval > maxInterval {
		record = aggregateRecord{localKeys: sets.NewString()}
	}

	// Write the new event into the aggregation record and put it on the cache
	record.localKeys.Insert(localKey)
	record.lastTimestamp = now
	e.cache.Add(aggregateKey, record)

	// If we are not yet over the threshold for unique events, don't correlate them
	if uint(record.localKeys.Len()) < e.maxEvents {
		return newEvent, eventKey
	}

	// do not grow our local key set any larger than max
	record.localKeys.PopAny()

	// create a new aggregate event, and return the aggregateKey as the cache key
	// (so that it can be overwritten.)
	eventCopy := &v1.Event{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%v.%x", newEvent.InvolvedObject.Name, now.UnixNano()),
			Namespace: newEvent.Namespace,
		},
		Count:          1,
		FirstTimestamp: now,
		InvolvedObject: newEvent.InvolvedObject,
		LastTimestamp:  now,
		Message:        e.messageFunc(newEvent),
		Type:           newEvent.Type,
		Reason:         newEvent.Reason,
		Source:         newEvent.Source,
	}
	return eventCopy, aggregateKey
}

// getEventKey builds unique event key based on source, involvedObject, reason, message
func getEventKey(event *v1.Event) string {
	return strings.Join([]string{
		event.Source.Component,
		event.Source.Host,
		event.InvolvedObject.Kind,
		event.InvolvedObject.Namespace,
		event.InvolvedObject.Name,
		event.InvolvedObject.FieldPath,
		string(event.InvolvedObject.UID),
		event.InvolvedObject.APIVersion,
		event.Type,
		event.Reason,
		event.Message,
	},
		"")
}
```

继续来看 EventCorrelate 方法，执行完 EventAggregate 并获取到聚合后（可能被更改）的事件和 cache key 之后，调用`c.logger.eventObserve(aggregateEvent, ckey)`进行事件记录，更新缓存。    
同样梳理下 eventObserve 的流程。    
1. 首先，通过 EventAggregate 返回的cache key 调用`e.lastEventObservationFromCache(key)`查询 cache，注意这个 cache 和 EventAggregate 中的 cache 并不是同一个，EventAggregate 中的 cache 是`EventAggregator.cache`即 EventAggregator 结构体中定义，而 eventObserve 的是`EventCorrelator.logger.cache`，是在 EventCorrelator 中定义。存的值也不是同一类型，这里保存的是 eventLog。    
2. 如果缓存不为空，那么要对事件 count 加一，并进行 merge 生成 patch。    
3. 最后将事件的 eventLog 加入缓存。    
   
```golang
// eventObserve records an event, or updates an existing one if key is a cache hit
func (e *eventLogger)eventObserve(newEvent *v1.Event, key string) (*v1.Event, []byte, error) {
	var (
		patch []byte
		err   error
	)
	eventCopy := *newEvent
	event := &eventCopy

	e.Lock()
	defer e.Unlock()

	// Check if there is an existing event we should update
	lastObservation := e.lastEventObservationFromCache(key)

	// If we found a result, prepare a patch
	if lastObservation.count > 0 {
		// update the event based on the last observation so patch will work as desired
		event.Name = lastObservation.name
		event.ResourceVersion = lastObservation.resourceVersion
		event.FirstTimestamp = lastObservation.firstTimestamp
		event.Count = int32(lastObservation.count) + 1

		eventCopy2 := *event
		eventCopy2.Count = 0
		eventCopy2.LastTimestamp = metav1.NewTime(time.Unix(0, 0))
		eventCopy2.Message = ""

		newData, _ := json.Marshal(event)
		oldData, _ := json.Marshal(eventCopy2)
		patch, err = strategicpatch.CreateTwoWayMergePatch(oldData, newData, event)
	}

	// record our new observation
	e.cache.Add(
		key,
		eventLog{
			count:           uint(event.Count),
			firstTimestamp:  event.FirstTimestamp,
			name:            event.Name,
			resourceVersion: event.ResourceVersion,
		},
	)
	return event, patch, err
}
```
比较一下 EventAggregate 和 eventObserve 方法，大致流程都是会根据 Event 来搜索缓存，根据缓存是否存在来决定操作。但是在这里面，两类缓存的作用是不同的，EventAggregate 中的缓存，是为了对事件进行聚合，将相同 reason 的事件进行关联。而 eventObserve 是为了事件最终的存储，为将要存储的 event 保存 FirstTimestamp 和进行计数，并据此生成 patch bytes，最后由 EventSink 进行 Patch 操作。    

#### SpamFilter
最后，在 EventCorrelate 中，还会调用一下 filterFunc，即过滤方法，判断是不是要跳过这个事件，不进行记录。具体调用的方法是 `EventSourceObjectSpamFilter.Filter`。Filter 同样维护了一个缓存，生成 key 的方法是 getSpamKey，它只基于`event.Source`和`event.InvolvedObject`来构建，缓存中存储的值为 spamRecord，它包含一个`flowcontrol.RateLimiter`对象，顾名思义，这是一个流量限制器，用途就是限流，具体实现在`client-go/util/flowcontrol/throttle.go`，这里不多做分析，有兴趣的同学可以自己看一下。    
简单解释一下，kubernetes 中实现的`flowcontrol.RateLimiter`基于 token bucket(即令牌桶)算法来完成限流。该算法原理是系统会以一个恒定的速度往桶里放入令牌，而如果请求需要被处理，则需要先从桶里获取一个令牌，当桶里没有令牌可取时，则拒绝服务。这里 NewTokenBucketRateLimiterWithClock 时，桶中的令牌的最大数量是`brust`，往桶中放入令牌的速率是`qps`，初始化时会向桶中放入`brust`个令牌。`TryAccept()`会尝试去桶中获取令牌，能过获取到则返回 true，反之返回 false。    
在 Filter 方法中，如果调用`record.rateLimiter.TryAccept()`返回了 false，说明此时 ratelimiter 不能立即获取到令牌，那么就 skip 事件。    
NewTokenBucketRateLimiterWithClock 时相应的配置，也是在 NewEventCorrelator 时传入的参数(defaultSpamBurst、defaultSpamQPS)。     
```golang
// getSpamKey builds unique event key based on source, involvedObject
func getSpamKey(event *v1.Event) string {
	return strings.Join([]string{
		event.Source.Component,
		event.Source.Host,
		event.InvolvedObject.Kind,
		event.InvolvedObject.Namespace,
		event.InvolvedObject.Name,
		string(event.InvolvedObject.UID),
		event.InvolvedObject.APIVersion,
	},
		"")
}

// NewEventSourceObjectSpamFilter allows burst events from a source about an object with the specified qps refill.
func NewEventSourceObjectSpamFilter(lruCacheSize, burst int, qps float32, clock clock.Clock) *EventSourceObjectSpamFilter {
	return &EventSourceObjectSpamFilter{
		cache: lru.New(lruCacheSize),
		burst: burst,
		qps:   qps,
		clock: clock,
	}
}

// spamRecord holds data used to perform spam filtering decisions.
type spamRecord struct {
	// rateLimiter controls the rate of events about this object
	rateLimiter flowcontrol.RateLimiter
}

// Filter controls that a given source+object are not exceeding the allowed rate.
func (f *EventSourceObjectSpamFilter) Filter(event *v1.Event) bool {
	var record spamRecord

	// controls our cached information about this event (source+object)
	eventKey := getSpamKey(event)

	// do we have a record of similar events in our cache?
	f.Lock()
	defer f.Unlock()
	value, found := f.cache.Get(eventKey)
	if found {
		record = value.(spamRecord)
	}

	// verify we have a rate limiter for this record
	if record.rateLimiter == nil {
		record.rateLimiter = flowcontrol.NewTokenBucketRateLimiterWithClock(f.qps, f.burst, f.clock)
	}

	// ensure we have available rate
	filter := !record.rateLimiter.TryAccept()

	// update the cache
	f.cache.Add(eventKey, record)

	return filter
}
```
最终，经过这一系列处理，EventCorrelate 最终返回了 EventCorrelateResult 给调用者，并有调用者根据结果进行事件的最终记录，另外有一点需要注意，在最终更新/新建完事件后，调用者还要调用`eventCorrelator.UpdateState(newEvent)`来更新缓存的状态，这里更新的缓存是`EventCorrelator.logger.cache`，即 eventObserve 方法中记录的缓存。    
```golang
// EventCorrelateResult is the result of a Correlate
type EventCorrelateResult struct {
	// the event after correlation
	Event *v1.Event
	// if provided, perform a strategic patch when updating the record on the server
	Patch []byte
	// if true, do no further processing of the event
	Skip bool
}

// UpdateState based on the latest observed state from server
// 主要更新的事件的 name/resourceversion
func (c *EventCorrelator) UpdateState(event *v1.Event) {
	c.logger.updateState(event)
}
```

### summary
本文通过从 kubelet 的 'BirthCry' 入手，分析了一个事件在 kubernetes 中的全部流程，以及如何对事件进行关联、聚合和过滤，同时其他组件的事件发送流程，也是大同小异，感兴趣的话可以自己选一个进行分析。另外，自己开发自定义的 controller 或其他自定义组件的时候，也可以尝试通过这一流程，将自己需要记录的事件，通过 kubernetes Event 的形式发送。    
附：kubernetes 事件整体流程    
![](/media/posts/cloud/kubernetes-events/kubernetes-event.jpg)    