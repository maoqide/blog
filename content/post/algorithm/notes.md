---
title: "Notes"
author: "Maoqide"
# cover: "/images/cover.jpg"
tags: ["think"]
date: 2021-05-13T09:13:20+08:00
draft: true
---

数据结构与算法之美
<!--more-->

# 03
时间复杂度分析：    
1. 只关注循环执行次数最多的一段代码    
2. 加法法则：总复杂度等于量级最大的那段代码的复杂度    
3. 乘法法则：嵌套代码的复杂度等于嵌套内外代码复杂度的乘积    
   
常见时间复杂度：    
- O(1): 代码无循环/递归    
- O(logn)、O(nlogn): 归并排序、快速排序的时间复杂度都是 O(nlogn)    
- O(m+n)、O(m*n)    

# 05 数组
线性表数据结构。用一组连续存储空间，储存一组相同类型的数据。支持*随机访问* O(1)。    
低效插入和删除 O(n)，需要数据搬移。优化：删除操作延后(JVM垃圾回收算法)。    

# 06 链表
通过指针将一组零散的内存块串联在一起。    
分类：单链表、双向链表和循环链表    
时间复杂度：插入删除 O(1)，随机访问O(n)  
	单链表：插入删除时需要查找前驱节点 O(n)。
	双向链表：插入删除时查找前驱结点 O(1)。

经典算法题：    
- [ ] **链表代码实现**
- [ ] **单链表字符串回文判断**       
- [ ] **单链表反转**    
- [ ] **链表中环的检测**    
- [ ] **两个有序的链表合并**
- [ ] **删除链表倒数第 n 个结点**
- [ ] **求链表中间节点**


# 08 栈
后进先出，先进后出。入栈出栈 O(1)    
顺序栈：数组。动态扩容（动态扩容数组，数据搬移O(n)）    
链式栈：链表。    
应用场景：    
- 函数调用    
- 表达式求值（四则运算...）    
- 括号匹配    

经典算法题：    
- [ ] **ArrayStack 实现**
- [ ] **LinkedListStack 实现**  

# 09 队列
先进先出，后进后出。 入队出队O(1)
应用场景：    
- 生产者 - 消费者模型（阻塞队列）    
- 并发队列（线程安全）    
- 线程池/连接池    

- [ ] **数组实现(数据搬移)**
- [ ] **链表实现**
- [ ] **循环链表数组实现**

# 10 递归
	写递归代码的关键就是找到如何将大问题分解为小问题的规律，并且基于此写出递推公式，然后再推敲终止条件，最后将递推公式和终止条件翻译成代码。    

- 递归代码要警惕堆栈溢出（限制递归深度）    
- 递归代码要警惕重复计算（散列表保存计算结果）    

# 11/12/13/14 排序
### 冒泡排序（Bubble Sort）
时间复杂度：最好 O(n)，最坏 O(nˆ2)，平均 O(nˆ2)    
空间复杂度：O(1)，原地排序    
稳定性：稳定排序    

### 插入排序（Insertion Sort）
时间复杂度：最好 O(n)，最坏 O(nˆ2)，平均 O(nˆ2)    
空间复杂度：O(1)，原地排序    
稳定性：稳定排序    

### 选择排序（Selection Sort）
时间复杂度：最好 O(nˆ2)，最坏 O(nˆ2)，平均 O(nˆ2)    
空间复杂度：O(1)，原地排序    
稳定性：非稳定排序    

### 归并排序（Merge Sort）    
时间复杂度：最好 O(nlogn)，最坏 O(nlogn)，平均 O(nlogn)    
空间复杂度：O(nlogn)，非原地排序    
稳定性：稳定排序    

#### 实现：   
``` 
递推公式：    
mergeSort(p…r) = merge(mergeSort(p…q), mergeSort(q+1…r))
终止条件：
p >= r

merge()
```
总体原理：利用 merge() 函数合并两有序数组为新的有序数组，将原数组分割直至到达终止条件，递归调用 merge() 函数。    

```golang
// merge sort
func mergeSort(a []int) {
	mergeSortc(a, 0, len(a)-1)

}

func mergeSortc(a []int, start, end int) {
	if start >= end {
		return
	}
	mid := (start + end) / 2
	mergeSortc(a, start, mid)
	mergeSortc(a, mid+1, end)
	merge(a, start, mid, end)
}

func merge(a []int, start, mid, end int) {
	var tmp = make([]int, end-start+1, end-start+1)
	var i, j = start, mid + 1
	var k = 0
	for ; i <= mid && j <= end; k++ {
		if a[i] <= a[j] {
			tmp[k] = a[i]
			i++
		} else {
			tmp[k] = a[j]
			j++
		}
	}
	if i <= mid {
		for ; i <= mid; i++ {
			tmp[k] = a[i]
			k++
		}
	} else {
		// j <= end
		for ; j <= end; j++ {
			tmp[k] = a[j]
			k++
		}
	}
	copy(a[start:end+1], tmp)
}
```

### 快速排序（Quicksort）    
时间复杂度：最好 O(nlogn)，最坏 O(n^2)，平均 O(nlogn)    
空间复杂度：O(1)，原地排序    
稳定性：稳定排序    

#### 实现
```
递推公式：
quick_sort(p…r) = quick_sort(p…q-1) + quick_sort(q+1…r)

终止条件：
p >= r

partition
```
总体原理：随机指定数组中一个元素 pivot（一般可指定为数组最后一个元素）， 利用 partition() 函数对无序数组进行分区，小于 pivot 的分在 pivot 左边，大于 pivot 的分在 pivot 右边。递归调用 partition()，将分区后的 pivot 两边的数组分别再进行分区，直至达到终止条件。    
	原地分区，为了保证快速排序为原地排序，partition() 函数的时间复杂度要为 O(1)，所以分区时采用元素交换的方式，不申请额外的临时数组。

```golang
// quick sort
func quickSort(a []int) {
	qsort(a, 0, len(a)-1)
	return
}

func qsort(a []int, start, end int) {
	if start >= end {
		return
	}
	pivot := partition(a, start, end)
	qsort(a, start, pivot-1)
	qsort(a, pivot+1, end)

}

func partition(a []int, l, r int) int {
	pivotV := a[r]
	i := l
	for l < r {
		if a[l] < pivotV {
			a[i], a[l] = a[l], a[i]
			i++
		}
		l++
	}
	a[i], a[r] = a[r], a[i]
	return i
}
```
