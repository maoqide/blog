---
title: "24 Swap Nodes in Pairs"
date: 2019-11-23T21:55:13+08:00
draft: true
---

https://leetcode.com/problems/swap-nodes-in-pairs/    
![](/media/posts/exercise/24-swap-nodes-in-pairs.jpg)    

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

// func swapPairs(head *ListNode) *ListNode {
//     newH := &ListNode{}
//     newH.Next = head
//     cur := head
//     prev := newH
    
//     for cur != nil && cur.Next != nil {
//         prev.Next = cur.Next
//         temp := cur.Next.Next
//         cur.Next.Next = cur
//         cur.Next = temp
//         prev = cur
//         cur = temp
//     }
    
//     return newH.Next
// } 


func swapPairs(head *ListNode) *ListNode {
    if head == nil || head.Next == nil {
        return head
    }
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
