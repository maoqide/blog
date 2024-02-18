---
title: "Bfs and Dfs"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["algorithm", "tree", "bfs", "dfs"]
date: 2020-03-28T11:23:38+08:00
---

golang 深度优先搜索和广度优先搜索。    
<!--more-->

深度优先和广度优先原理都很简单，这里不写原理，只写代码实现。    

## BFS(广度优先搜索)
BFS 从根结点逐层搜索，简单的说，是从根节点开始，沿着树的宽度遍历树的节点。如果所有节点均被访问，则算法中止。    
```golang
// BFS 伪代码
func BFS(root *Node) {
	if root == nil {
		return
	}
	// 队列，用来存储已被访问但子节点尚未被访问的节点。
	var queue []*Node
	// 记录已被访问的节点，避免重复访问
	var visited = make(map[*Node]bool)
	queue = append(queue, root)
	for len(queue) > 0 {
		//从队首取出节点并在 visited 中记录
		node := queue[0]
		visited[node] = true

		// do something
		// 进行对 node 的处理
		println(node.Value())
		handle(node)

		// append all children nodes not in visited
		// for example, node.Left and node.Right for binary tree
		// 遍历该 node 所有子节点，将未被访问过的节点加入queue队列队尾
		// 如二叉树要依次调用 node.Left 和 node.Right 获取子节点
		for _, child := range node.Children() {
			if _, ok := visited[child]; !ok {
				queue = append(queue, child)
			}
		}
		// 此时该 node 子节点已全部被加入queue，将该node移除queue
		queue = queue[1:]
	}
	return
}
```

## DFS(深度优先搜索)
DFS 沿着树的深度遍历树的节点，尽可能深的搜索树的分支。当节点v的所在边都己被探寻过，搜索将回溯到发现节点v的那条边的起始节点。这一过程一直进行到已发现从源节点可达的所有节点为止。通常使用递归实现。    
```golang
// DFS 伪代码
func DFS(root *Node) {
	// 记录已被访问的节点，避免重复访问
	var visited = make(map[*Node]bool)
	// 由于要在递归函数间传递，visited 需要传指针
	dfs(root, &visited)
}

func dfs(root *Node, visited *map[*Node]bool) {
	if root == nil {
		return
	}
	// 记录当前节点为已访问
	(*visited)[root] = true
	
	// do something
	// 进行对 node 的处理
	println(node.Value())
	handle(node)

	// recursive dfs children nodes not in visited
	// 递归dfs访问未被访问子节点
	// 如二叉树要依次递归调用 dfs(node.Left, visited) 和 dfs(node.Right, visited)
	for _, child := range node.Children() {
		//
		if _, ok := (*visited)[child]; !ok {
			dfs(child, visited)
		}
	}
}

```