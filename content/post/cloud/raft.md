---
title: "Raft"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["etcd", "raft", "distributed"]
date: 2021-03-22T09:37:09+08:00
# draft: false
---

Raft 是一个管理复制日志的分布式一致性算法，也是 ETCD 实现分布式一致性的基础，保证 ETCD 集群中各节点数据的强一致性。    
<!--more-->

## CAP 理论
一致性(Consistency): 每个读操作能够得到最新的写操作的结果或者一个错误。    
可用性(Availability): 每个请求都能够得到一个（非错误）的响应，但不保证它包含最新的写操作的结果。    
分区容忍性(Partition Tolerance): 即使任意适量的消息因为节点间网络的原因被丢弃（或延迟），系统仍能够持续运行。    
CAP 理论即：在一个分布式的数据存储系统中，不可能同时保证以上三者中的两者以上，即最多只能同时保证 CAP 的其中两个。    

## 复制状态机
一致性算法是在复制状态机的背景下提出的。在这种方式下，一组服务器上的状态机产生相同状态的副本，并且在一些机器宕机的情况下也能够继续运行。    
![https://raft.github.io/raft.pdf](/media/posts/cloud/raft/raft-state-machine.png)    
复制状态机通常基于复制日志来实现。如上图所示，每个节点存储一个包含一系列指令的日志，供状态机按照顺序执行。每个日志都包含相同顺序的相同指令，因此每个状态机都处理相同序列的指令，由于状态机是确定性的，所以每次处理都会产生相同的状态和同样顺序的输出。    
一致性算法的工作是保证复制日志的一致性。一个节点上的一致性模块通过客户端接收指令并添加到日志中，它和其他节点上的一致性模块通信，保证每一个日志都最终包含同样顺序的同样请求，即使一些节点发生宕机。一旦指令被正确的复制，每个节点的状态机会以日志的顺序执行，输出结果返回客户端。这样多个节点对外就表现为一个单一的可靠的状态机。    

## Raft
Raft 实现一致性的方式是，首先选举出一个强大的 leader，并将管理复制日志的全部职责给予 leader。leader 接收客户端的日志条目（log entries），复制到其他节点，并且在安全的时间告诉节点将 log entries 提交到状态机。leader 大大简化了复制日志的管理。例如，leader 可以决定新的条目放在日志的什么位置，而不用和其他节点协商；数据流都是从 leader 到 其他简单的形式。leader 有可能宕机或者和其他节点失联，这时会选举一个新的 leader。    
通过 leader 的方式，Raft 将一致性问题分解为三个相对对立的子问题：    

- 领导人选举（Leader election）：当 leader 宕机时一定要选出新的 leader。    
- 日志复制（Log replication）：leader 必须从客户端接收日志条目，并复制到集群中，强制其他节点和自己保持一致。    
- 安全性（Safety）：如果任一节点提交了一个日志条目到它的状态机，那么其他节点都不能再提交不同的指令到统一日志索引位置。为了保证这一安全性，Raft 在选举机制中引入了一个额外的限制。    

### Raft 基础
Raft 一致性算法的历史和其与其他一致性算法的对比，本文就不再探讨，网络上可以搜索到很多文章对此做出了很详细的说明，这里推荐一位优秀博主的文章[分布式一致性与共识算法-draveness](https://draveness.me/consensus/)，感兴趣的话可以自行搜索。    

这里详细描述一下 Raft 集群的整体运作。在 Raft 集群中，所有节点分为三种角色，领导人（leader），候选人（candidate），追随者（follower）。正常情况下，一个集群只有一个 leader，并且其他所有节点都为 follower。candidate 作用，是用来选出集群的 leader。Raft 集群允许集群出现故障的节点数为 n-1/2，因此一般建议节点数为奇数，通常建议 5 个节点，这样可以允许 2 个节点出现异常。    
Raft 将时间划分为可能为任意长度的任期(term)。`term` 是连续的整数，term 开始于一次选举，如果有 candidate 赢得选举，它将在这一任期内成为 leader，直到下一轮选举开始。若一个任期内，没有 candidate 获得多数选票（split vote）或者选举超时，那么此任期内没有 leader 产生，并会开始新的 term 和新一轮的选举。Raft 会保证在一个 term 内最多有一个 leader。下图为 Raft 论文中对 term 长度的示意图。    
![https://raft.github.io/raft.pdf](/media/posts/cloud/raft/raft-terms.png)    
Term 是 Raft 集群中的逻辑时钟，Raft 节点通过 term 判断接收到信息是否过期。在 Raft 集群中，不同节点对 term 切换的时间的感知可能是不同的，甚至有些情况下，一个节点可能会错过一个或多个 term。为了避免因此产生的数据不一致的情况，每个 Raft 节点在本地维护一个单调自增的 `currentTerm`，节点间通信时会交换双方 `currentTerm`。如果一个节点的 `currentTerm` 小于对方，就会更新自己的 `currentTerm`；如果 candidate 或者 leader 发现自己的 term 过期了，那么它会立即转换为 follower 状态；当节点发现接收到的请求携带了过期 term，那么它会拒绝此请求。    
Raft 节点之间使用 RPC 进行通信，基本的一致性算法只需要两种 RPC 请求类型，即：RequestVote RPC 和 AppendEntries RPC。RequestVote RPC 在选举阶段由 candidate 发出，向所有其他节点请求选票；AppendEntries RPC 由 leader 发出，向其他节点同步 log entries，另外空的 AppendEntries RPC 为 leader 向其他节点发送心跳。为了提高性能，节点的 RPC 请求会并发进行，如果没有接收到请求，会进行重试。    
![https://raft.github.io/raft.pdf](/media/posts/cloud/raft/raft-impl.png)    

### leader 选举
![](/media/posts/cloud/raft/raft-leader-election.png)    
Raft 使用心跳机制来触发选举，当一个节点启动时，角色为 follower，只要从 leader 或 candidate 接收到一个有效的 RPC 请求，节点就会保持 follower 状态。Leader 会周期性的发送心跳（空的 AppendEntries RPC）给所有 follower 来维持 leader 身份。如果 follower 在一定时间内（electionTimeout）没有收到消息，就会认为当前集群中没有存活的 leader，并且开始新一轮的选举。    
新一轮选举，follower 会自增本地的 `currentTerm` 并转换为 candidate 角色。接着它会将选票投给自己，并向其他所有节点发送 RequestVote RPC 请求，节点保持 candidate 状态直到以下三种情况出现：    
1. 本节点赢得选举，当选 leader 并向其他所有节点发送心跳，以避免产生新一轮选举    
2. 本节点接收到其他节点（leader）的 AppendEntries RPC，如果 RPC 中包含的 term >= currentTerm，节点接受其为 leader 并转换为 follower，否则拒绝此 RPC 并保持 candidate 身份。    
3. 一段时间内（electionTimeout）没有节点当选（split vote），即可能同一时间有多个 candidate 并且选票数相同，那么每个 candidate 都将会超时，自增本地的 `currentTerm` 并且发起新一轮选举。    

同任期内赢得多数节点选票的 candidate 会当选 leader。每个节点一次选举内最多只能偷一次选票，并且基本遵循先来先得的原则（另外 Raft 还有另外的限制，以保证 leader 节点拥有最全的数据）。    
上述第三种情况，理论上有可能无限重复，导致集群不停的进行选举无法产生 leader。Raft 使用了一个巧妙而且非常简单的方式解决这个问题，使用随机的 electionTimeout。节点每次选举都使用一个时间段内（如 150-300ms）随机的 electionTimeout 值，这样就极大的避免了几个 candidate 同时超时的可能。    
最后，为了保证 Raft 集群的稳定，不出现频繁的不必要选举和 leader 切换，Raft 集群应满足以下要求：    

> broadcastTime << electionTimeout << MTBF

`broadcastTime` 为集群中一个节点并发向其他所有节点发送 RPC 并收到响应的平均时间；    `electionTimeout` 即上面提到的节点选举超时时间；`MTBF` 即 "Mean Time Between Failure"，平均故障间隔时间，指一个节点两个故障间的间隔时间。    
broadcastTime 和 MTBF 都依赖于物理因素，一般来说，`broadcastTime` 应为 0.5-20ms，由此 `electionTimeout` 应在 10-500ms 间，`MTBF` 通常为几个月或更长的时间，相对很容易满足。    

### 日志复制和提交
一旦 leader 被选举，它就开始接收客户端请求。每个客户端请求包含一个需要被复制状态机执行的指令。leader 将该指令追加进日志，并并行发出 AppendEntries RPCs 给每个节点复制该日志条目。当该条目被 *安全的复制* 后（复制到大多数节点），leader 会提交该条目到状态机执行并返回客户端执行的结果。如果 follower 出现宕机、运行慢或者网络丢包等，leader 会不停重试 AppendEntries RPCs （即使已经返回客户端请求）直到所有 follower 都最终存储所有的日志条目。    
![https://raft.github.io/raft.pdf](/media/posts/cloud/raft/raft-log.png)    
日志的结构如上图，日志由条目（entries）组成，每个日志条目保存了状态机指令和 leader 接收到该指令时的任期数（term number）。任期数的作用是检查日志是否一致。每个日志条目还包含了一个整数的日志索引，标识它在日志中的位置。    
leader 决定何时将日志条目提交到状态机，可被 leader 安全提交到状态机的日志为*已提交* （committed）。Raft 保证已提交的条目是不可变的，并且会被所有状态机执行。    

> 当**创建该日志条目的 leader** 将其复制到大多数节点，该条目即可被视为已提交，并且同时会提交该 leader 日志中在此条目之前的所有日志条目，包括前任 leader 创建的条目。    

上面这句话非常重要，它定义了 Raft 中日志提交的机制，并且保证已提交的日志不会被覆盖或更改。从中可以看出，leader 提交日志条目的标准是，可以被 leader 安全的提交到状态机，这要满足两个条件：该日志条目是被当前 leader 创建 及 被当前 leader 复制到多数节点。否则，即使已被复制到多数节点，此日志条目也有可能不是已提交的状态，它可能是由前一任 leader 创建，再由当前 leader 复制到了多数节点。只有当前 leader 创建了新的条目并将此条目复制到多数节点后，前面的日志条目才会跟随新的条目的提交而被一同提交。**Raft 不会通过计数副本数（是否同步到多数节点）来提交之前任期的日志条目，只有当前任期内的日志条目才会通过这种方式来提交**。下图描述了这一场景：    
![](/media/posts/cloud/raft/raft-commit.png)    

leader 会持续追踪已提交的最大的日志索引，并将该索引包含到后面的 AppendEntries RPCs 中（leaderCommit）。一旦 follower 发现一个日志条目被提交了，它就会将该条目提交到状态机（按照日志的顺序）。    
Raft 的日志维持着一下两个特性：    

- 如果在不同的日志中的两个条目拥有相同的索引和任期号，那么他们存储了相同的指令。    
- 如果在不同的日志中的两个条目拥有相同的索引和任期号，那么他们之前的所有日志条目也全部相同。    

第一个特性源于 leader 一个任期内在一个给定的日志索引中，最多只会创建一个日志条目，并且日志条目从不会更改索引。第二个特性由 AppendEntries 的一个简单的一致性检查来保证。当发送 AppendEntries RPC 时，leader 会将新的日志条目的前一条目 的索引和任期号包含在请求内，如果 follower 没有找到同一任期同一索引的相同条目，就会拒绝该请求。    
Raft 算法中，leader 处理不一致的方式是强制 follower 复制自己的日志，即 follower 上有冲突的日志条目会被直接覆盖。为了是 follower 日志和自己一致，leader 必须找到双方最近的一条一致的日志条目，删掉 follower 日志中这条之后所有的条目，并将自己这条之后的所有日志条目发送给 follower。以上所有都是在 ppendEntries RPCs 的一致性检查中完成的。leader 为每个 follower 维护一个 `nextIndex`，表示下一个将要发送给此 follower 的日志条目的索引。当 leader 最初当选时，它会先初始化所有 follower 的 `nextIndex` 为自身日志中最后一个条目的索引值加 1。如果 follower 的日志和 leader 不一致，AppendEntries RPC 的一致性检查就会失败并被拒绝，被拒绝后，leader 会减小 `nextIndex` 的值并进行重试，直到最终某个 `nextIndex` leader 和 follower 的日志一致，这时 AppendEntries RPC 成功，并用 leader 的日志覆盖 follower 上冲突的条目。只要 AppendEntries RPC 是成功的，follower 的日志就会和 leader 保持一致，并一直保持直到整个任期结束。    

### 安全性
目前为止以上的机制，并没有保证 Raft 中每个状态机按照相同序列执行相同的指令。举例来说，一个 follower 可能在 leader 提交某些日志条目时不可用，后面又可能被选为 leader，此时之前被提交的条目可能会被覆盖。这导致不同状态机执行的指令并不相同。    
Raft 通过在 leader 选举时添加额外的约束来完善算法，这个约束保证任一任期的 leader 一定包含了所有之前任期提交过的日志。这个约束使得提交的规则更加清晰，也避免了上面提到的问题。    
在任何基于领导人的一致性算法中，leader 都必须存储所有的已提交的日志条目。在一些算法中，某个节点即使一开始没有包含所有已提交条目也能够当选 leader，他们包含额外的机制找出缺失的条目并将其传送给 leader，这一过程在选举过程中或选举之后很快进行，但是这会导致额外的复杂性。Raft 采用了一个更简单的方式，它在选举时，就保证新选举的 leader 包含所有已提交的条目，无需额外的传输条目到新的 leader。这意味着日志条目的传输方向只有一条，从 leader 到 follower，并且 leader 上的 log 从不会被覆盖。    
Raft 通过投票的过程，阻止不包含全部已提交条目的候选人赢得选举。candidate 想要赢得选举，必须要联系集群中大多数的节点，这意味着每个已提交的条目都在这些节点中的至少一个上存在。如果 candidate 的日志任一其他节点相比，至少同样新，那么它一定持有所有已提交的日志。RequestVote RPC 实现了这一限制，请求中包含了 candidate 的 log 的信息，**如果被请求投票的节点的日志比 candidate 还要新，那么它会拒绝投票**。    
Raft 通过比较最后一个日志条目的 index 和 term 来**判断两个日志谁更新**。如果两个日志最后一个条目 term 不同，那么 term 更大的日志更新；如果 term 相同，那么日志更长（可理解为 index 更大）的那个更新。    

## 日志压缩和快照

## 集群成员（配置）变更

## Reference
- [Raft 论文原文](https://raft.github.io/raft.pdf)    
- [CAP 维基百科](https://en.wikipedia.org/wiki/CAP_theorem)    
- [分布式一致性与共识算法-draveness](https://draveness.me/consensus/)    
