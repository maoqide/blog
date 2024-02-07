---
title: "24 Swap Nodes in Pairs"
date: 2019-11-23T21:55:13+08:00
draft: true
---

## 24-swap-nodes-in-pairs
https://leetcode.com/problems/swap-nodes-in-pairs/    
![](/media/posts/exercise/24-swap-nodes-in-pairs.jpg)    

    Given a linked list, swap every two adjacent nodes and return its head.
    You may not modify the values in the list's nodes, only nodes itself may be changed.

    Example:
    Given 1->2->3->4, you should return the list as 2->1->4->3.

```golang
/**
 * Definition for singly-linked list.
 * type ListNode struct {
 *     Val int
 *     Next *ListNode
 * }
 */
// func swapPairs(head *ListNode) *ListNode {
//     if head == nil || head.Next == nil {
//         return head
//     }
//     res := head.Next
//     prev := head
//     cur := head
//     index := 1
//     for cur != nil {
//         nxt := cur.Next
//         if index%2 != 0 {
//             if cur.Next == nil || cur.Next.Next == nil {
//                 cur.Next = nil
//             } else if cur.Next.Next.Next == nil {
//                 cur.Next = cur.Next.Next
//             } else {
//                 cur.Next = cur.Next.Next.Next
//             }
//         } else {
//             cur.Next = prev
//         }
//         index++
//         prev = cur
//         cur = nxt
//     }
//     return res
// }

func swapPairs(head *ListNode) *ListNode {
    if head == nil || head.Next == nil {
        return head
    }
    // new head must be second node of listNode.
    newH := head.Next
    cur := head
    prev := newH
    for cur != nil && cur.Next != nil{
        temp := cur.Next.Next
        prev.Next =cur.Next
        cur.Next.Next = cur
        cur.Next = temp
        prev = cur
        cur = temp
    }
    return newH
}
```

## 141-linked-list-cycle
https://leetcode.com/problems/linked-list-cycle/     
快慢指针，若成环则一定会相遇。       

```
Given a linked list, determine if it has a cycle in it.
To represent a cycle in the given linked list, we use an integer pos which represents the position (0-indexed) in the linked list where tail connects to. If pos is -1, then there is no cycle in the linked list.


Example 1:
Input: head = [3,2,0,-4], pos = 1
Output: true
Explanation: There is a cycle in the linked list, where tail connects to the second node.

Example 2:
Input: head = [1,2], pos = 0
Output: true
Explanation: There is a cycle in the linked list, where tail connects to the first node.

Example 3:
Input: head = [1], pos = -1
Output: false
Explanation: There is no cycle in the linked list.
```

```golang
/**
 * Definition for singly-linked list.
 * type ListNode struct {
 *     Val int
 *     Next *ListNode
 * }
 */
 func hasCycle(head *ListNode) bool {
    if head == nil || head.Next == nil {
        return false
    }
    curSlow := head
    curFast := head.Next
    // curFast is always ahead of curSlow so only need to judge curFast
    for curFast != nil && curFast.Next != nil {
        if curSlow.Next == curFast.Next {
            return true
        }
        curSlow = curSlow.Next
        curFast = curFast.Next.Next
    }
    return false
}
```

## 142-linked-list-cycle-ii

https://leetcode.com/problems/linked-list-cycle-ii/    
快慢指针    

```
Given a linked list, return the node where the cycle begins. If there is no cycle, return null.
To represent a cycle in the given linked list, we use an integer pos which represents the position (0-indexed) in the linked list where tail connects to. If pos is -1, then there is no cycle in the linked list.
Note: Do not modify the linked list.


Example 1:
Input: head = [3,2,0,-4], pos = 1
Output: tail connects to node index 1
Explanation: There is a cycle in the linked list, where tail connects to the second node.

Example 2:
Input: head = [1,2], pos = 0
Output: tail connects to node index 0
Explanation: There is a cycle in the linked list, where tail connects to the first node.


Example 3:
Input: head = [1], pos = -1
Output: no cycle
Explanation: There is no cycle in the linked list.
```

```golang
/**
 * Definition for singly-linked list.
 * type ListNode struct {
 *     Val int
 *     Next *ListNode
 * }
 */
// func detectCycle(head *ListNode) *ListNode {
//     if head == nil {
//         return nil
//     }
//     cur := head
//     m := make(map[*ListNode]bool)
//     for cur != nil {
//         if _, ok := m[cur]; ok {
//             return cur
//         }
//         m[cur] = true
//         cur = cur.Next
//     }
//     return nil
// }

func detectCycle(head *ListNode) *ListNode {
    if head == nil {
        return nil
    }
    slow, fast := head, head
    for fast.Next != nil && fast.Next.Next != nil {
        slow = slow.Next
        fast = fast.Next.Next
        if slow == fast {
            break
        }
    }
    if fast.Next == nil || fast.Next.Next == nil {
        return nil
    }

    cur := head
    for cur != slow {
        cur = cur.Next
        slow = slow.Next
    }
    return slow
}
```