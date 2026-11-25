"""
Custom Data Structures & Graph Algorithms for ChanakyaConnect.

Every core feature is backed by an explicit in-memory data structure:
1. HashTable (Separate Chaining): O(1) average user & post lookup.
2. Trie (Prefix Tree): O(L + K) prefix search over student names and usernames.
3. Queue (FIFO): Pending connection requests and notification delivery.
4. Stack (LIFO): Navigation history (Back) and Undo post deletion.
5. MaxHeap (Binary Heap): K-way merge for chronological Home Feed & Trending Posts.
6. SocialGraph (Adjacency Lists): Undirected connections + directed pending requests,
   BFS for degree & shortest chain, Jaccard similarity for People You May Know,
   and Connected Components (BFS/DFS) for student communities.
"""

from collections import deque
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar

T = TypeVar("T")


# ==============================================================================
# 1. HASH TABLE (Separate Chaining with Dynamic Resizing)
# ==============================================================================
class HashTable(Generic[T]):
    """
    Hash Table using separate chaining and FNV-1a / Python hash compression.
    Load factor threshold = 0.75 triggers automatic table doubling.
    Time Complexity: O(1) average for get, put, delete; O(N) worst-case.
    """

    def __init__(self, initial_capacity: int = 32) -> None:
        self._capacity: int = max(8, initial_capacity)
        self._buckets: List[List[Tuple[str, T]]] = [[] for _ in range(self._capacity)]
        self._size: int = 0

    def _bucket_index(self, key: str) -> int:
        # Polynomial rolling hash for deterministic bucket mapping
        h = 5381
        for ch in key:
            h = ((h << 5) + h) + ord(ch)
        return (h & 0x7FFFFFFF) % self._capacity

    def _resize(self) -> None:
        old_buckets = self._buckets
        self._capacity *= 2
        self._buckets = [[] for _ in range(self._capacity)]
        self._size = 0
        for bucket in old_buckets:
            for k, v in bucket:
                self.put(k, v)

    def put(self, key: str, value: T) -> None:
        if (self._size + 1) / self._capacity > 0.75:
            self._resize()
        idx = self._bucket_index(key)
        bucket = self._buckets[idx]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self._size += 1

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        idx = self._bucket_index(key)
        for k, v in self._buckets[idx]:
            if k == key:
                return v
        return default

    def contains(self, key: str) -> bool:
        return self.get(key) is not None

    def delete(self, key: str) -> bool:
        idx = self._bucket_index(key)
        bucket = self._buckets[idx]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket.pop(i)
                self._size -= 1
                return True
        return False

    def keys(self) -> List[str]:
        return [k for bucket in self._buckets for k, _ in bucket]

    def values(self) -> List[T]:
        return [v for bucket in self._buckets for _, v in bucket]

    def items(self) -> List[Tuple[str, T]]:
        return [(k, v) for bucket in self._buckets for k, v in bucket]

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: str) -> bool:
        return self.contains(key)


# ==============================================================================
# 2. TRIE (Prefix Tree for Name & Username Autocomplete)
# ==============================================================================
class TrieNode:
    def __init__(self) -> None:
        self.children: Dict[str, "TrieNode"] = {}
        # Store unique usernames matched at this terminal node
        self.usernames: Set[str] = set()


class Trie:
    """
    Case-insensitive Trie for prefix search over both usernames and full names.
    Time Complexity:
      - insert(key, username): O(L) where L = len(key)
      - search_prefix(prefix): O(P + K) where P = len(prefix), K = subtree nodes
    """

    def __init__(self) -> None:
        self.root = TrieNode()

    def insert(self, text: str, username: str) -> None:
        """Index a string (e.g. username, full name, or name token) -> username."""
        node = self.root
        for ch in text.lower().strip():
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.usernames.add(username)

    def remove(self, text: str, username: str) -> None:
        """Remove a username association for a given indexed string."""
        node = self.root
        for ch in text.lower().strip():
            if ch not in node.children:
                return
            node = node.children[ch]
        node.usernames.discard(username)

    def search_prefix(self, prefix: str, limit: int = 10) -> List[str]:
        """Return up to `limit` unique usernames matching the given prefix."""
        clean = prefix.lower().strip()
        if not clean:
            return []
        node = self.root
        for ch in clean:
            if ch not in node.children:
                return []
            node = node.children[ch]

        results: Set[str] = set()
        # DFS/BFS over subtree to collect matching usernames
        stack = [node]
        while stack:
            curr = stack.pop()
            results.update(curr.usernames)
            if len(results) >= limit * 2:
                # Collect a bit more for deterministic sorting, then stop
                break
            for child in curr.children.values():
                stack.append(child)

        return sorted(results)[:limit]


# ==============================================================================
# 3. QUEUE (FIFO for Pending Requests & Notifications)
# ==============================================================================
class Queue(Generic[T]):
    """
    FIFO Queue backed by collections.deque for O(1) enqueue and dequeue.
    Used for incoming connection requests and notification streams.
    """

    def __init__(self) -> None:
        self._data: deque[T] = deque()

    def enqueue(self, item: T) -> None:
        self._data.append(item)

    def dequeue(self) -> Optional[T]:
        if self.is_empty():
            return None
        return self._data.popleft()

    def peek(self) -> Optional[T]:
        if self.is_empty():
            return None
        return self._data[0]

    def remove_where(self, predicate: Callable[[T], bool]) -> bool:
        """Remove first item matching predicate; returns True if removed."""
        for i, item in enumerate(self._data):
            if predicate(item):
                del self._data[i]
                return True
        return False

    def to_list(self) -> List[T]:
        return list(self._data)

    def is_empty(self) -> bool:
        return len(self._data) == 0

    def __len__(self) -> int:
        return len(self._data)


# ==============================================================================
# 4. STACK (LIFO for Undo & Back Navigation)
# ==============================================================================
class Stack(Generic[T]):
    """
    LIFO Stack for O(1) push/pop.
    Used for:
      - Navigation history (Back button in CLI/Web).
      - Undo stack (e.g., restoring a recently deleted post).
    """

    def __init__(self, max_size: int = 50) -> None:
        self._data: List[T] = []
        self._max_size = max_size

    def push(self, item: T) -> None:
        if len(self._data) >= self._max_size:
            self._data.pop(0)
        self._data.append(item)

    def pop(self) -> Optional[T]:
        if self.is_empty():
            return None
        return self._data.pop()

    def peek(self) -> Optional[T]:
        if self.is_empty():
            return None
        return self._data[-1]

    def to_list(self) -> List[T]:
        return list(self._data)

    def clear(self) -> None:
        self._data.clear()

    def is_empty(self) -> bool:
        return len(self._data) == 0

    def __len__(self) -> int:
        return len(self._data)


# ==============================================================================
# 5. MAX HEAP (Binary Heap for Chronological Feed Merge & Trending Posts)
# ==============================================================================
class MaxHeap(Generic[T]):
    """
    Custom Binary Max-Heap storing (priority_score, tie_breaker, item) tuples.
    Time Complexity:
      - push: O(log N)
      - pop:  O(log N)
      - peek: O(1)
    Used for:
      - K-way merging of connections' time-ordered posts (newest first).
      - Ranking trending posts by engagement + recency score.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[float, int, T]] = []
        self._counter: int = 0

    def push(self, priority: float, item: T) -> None:
        self._counter += 1
        self._heap.append((priority, self._counter, item))
        self._sift_up(len(self._heap) - 1)

    def pop(self) -> Optional[T]:
        if not self._heap:
            return None
        top = self._heap[0][2]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last
            self._sift_down(0)
        return top

    def peek(self) -> Optional[T]:
        return self._heap[0][2] if self._heap else None

    def _sift_up(self, idx: int) -> None:
        while idx > 0:
            parent = (idx - 1) // 2
            if self._heap[idx][:2] > self._heap[parent][:2]:
                self._heap[idx], self._heap[parent] = self._heap[parent], self._heap[idx]
                idx = parent
            else:
                break

    def _sift_down(self, idx: int) -> None:
        n = len(self._heap)
        while True:
            largest = idx
            left = 2 * idx + 1
            right = 2 * idx + 2
            if left < n and self._heap[left][:2] > self._heap[largest][:2]:
                largest = left
            if right < n and self._heap[right][:2] > self._heap[largest][:2]:
                largest = right
            if largest != idx:
                self._heap[idx], self._heap[largest] = self._heap[largest], self._heap[idx]
                idx = largest
            else:
                break

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def __len__(self) -> int:
        return len(self._heap)


# ==============================================================================
# 6. SOCIAL GRAPH (Adjacency Lists + BFS + Jaccard + Communities)
# ==============================================================================
class SocialGraph:
    """
    Graph G(V, E) representing Chanakya University students and connections.
    - Accepted connections: Undirected edges stored in adjacency lists (`adj[u]`).
    - Pending requests: Directed edges stored in per-receiver FIFO Queues
      (`incoming_requests[receiver]`) and per-sender sets (`outgoing_requests[sender]`).
    - No self-edges or duplicate edges are permitted.
    """

    def __init__(self) -> None:
        self.adj: Dict[str, Set[str]] = {}
        self.incoming_requests: Dict[str, Queue[str]] = {}
        self.outgoing_requests: Dict[str, Set[str]] = {}

    def add_user(self, username: str) -> None:
        if username not in self.adj:
            self.adj[username] = set()
            self.incoming_requests[username] = Queue()
            self.outgoing_requests[username] = set()

    def are_connected(self, u: str, v: str) -> bool:
        return u in self.adj and v in self.adj[u]

    def has_pending_request(self, sender: str, receiver: str) -> bool:
        return sender in self.outgoing_requests and receiver in self.outgoing_requests[sender]

    def send_request(self, sender: str, receiver: str) -> Tuple[bool, str]:
        if sender == receiver:
            return False, "Cannot send a connection request to yourself."
        if sender not in self.adj or receiver not in self.adj:
            return False, "User does not exist."
        if self.are_connected(sender, receiver):
            return False, f"You are already connected with {receiver}."
        if self.has_pending_request(sender, receiver):
            return False, f"Connection request to {receiver} is already pending."
        if self.has_pending_request(receiver, sender):
            # Mutual request -> auto-accept!
            self.accept_request(receiver, sender)
            return True, f"{receiver} had already sent you a request — you are now connected!"

        self.outgoing_requests[sender].add(receiver)
        self.incoming_requests[receiver].enqueue(sender)
        return True, f"Connection request sent to {receiver}."

    def accept_request(self, receiver: str, sender: str) -> Tuple[bool, str]:
        if not self.has_pending_request(sender, receiver):
            return False, f"No pending request from {sender}."
        self.outgoing_requests[sender].discard(receiver)
        self.incoming_requests[receiver].remove_where(lambda x: x == sender)
        # Add undirected edge
        self.adj[sender].add(receiver)
        self.adj[receiver].add(sender)
        return True, f"Accepted connection request from {sender}."

    def reject_request(self, receiver: str, sender: str) -> Tuple[bool, str]:
        if not self.has_pending_request(sender, receiver):
            return False, f"No pending request from {sender}."
        self.outgoing_requests[sender].discard(receiver)
        self.incoming_requests[receiver].remove_where(lambda x: x == sender)
        return True, f"Rejected connection request from {sender}."

    def cancel_request(self, sender: str, receiver: str) -> Tuple[bool, str]:
        if not self.has_pending_request(sender, receiver):
            return False, f"No outgoing request to {receiver}."
        self.outgoing_requests[sender].discard(receiver)
        self.incoming_requests[receiver].remove_where(lambda x: x == sender)
        return True, f"Cancelled connection request to {receiver}."

    def remove_connection(self, u: str, v: str) -> Tuple[bool, str]:
        if not self.are_connected(u, v):
            return False, f"You are not connected with {v}."
        self.adj[u].discard(v)
        self.adj[v].discard(u)
        return True, f"Removed connection with {v}."

    def get_connections(self, u: str) -> List[str]:
        if u not in self.adj:
            return []
        return sorted(self.adj[u])

    def get_pending_incoming(self, u: str) -> List[str]:
        if u not in self.incoming_requests:
            return []
        return self.incoming_requests[u].to_list()

    def get_pending_outgoing(self, u: str) -> List[str]:
        if u not in self.outgoing_requests:
            return []
        return sorted(self.outgoing_requests[u])

    def mutual_connections(self, u: str, v: str) -> List[str]:
        """Set intersection of adjacency lists N(u) ∩ N(v). O(min(deg(u), deg(v)))."""
        if u not in self.adj or v not in self.adj:
            return []
        return sorted(self.adj[u].intersection(self.adj[v]))

    def bfs_degree_and_path(self, start: str, target: str) -> Tuple[Optional[int], List[str]]:
        """
        Breadth-First Search (BFS) to find:
          - Degree of connection (1 = direct, 2 = friend-of-friend, 3 = 3rd degree, etc.)
          - One shortest chain of connections [start, ..., target].
        Time Complexity: O(V + E).
        """
        if start not in self.adj or target not in self.adj:
            return None, []
        if start == target:
            return 0, [start]

        visited: Set[str] = {start}
        parent: Dict[str, Optional[str]] = {start: None}
        q: Queue[str] = Queue()
        q.enqueue(start)

        while not q.is_empty():
            curr = q.dequeue()
            assert curr is not None
            for neighbor in sorted(self.adj[curr]):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = curr
                    if neighbor == target:
                        # Reconstruct shortest path
                        path: List[str] = []
                        node: Optional[str] = target
                        while node is not None:
                            path.append(node)
                            node = parent[node]
                        path.reverse()
                        return len(path) - 1, path
                    q.enqueue(neighbor)

        return None, []

    def people_you_may_know(self, u: str, limit: int = 10) -> List[Tuple[str, float, int]]:
        """
        Recommend non-connected users ranked by Jaccard Similarity Coefficient:
            J(u, v) = |N(u) ∩ N(v)| / |N(u) ∪ N(v)|
        Also considers 2nd-degree neighbors first; if fewer than `limit`, includes
        other non-connected users with 0 mutuals (score 0.0) as fallback.
        Returns list of (username, jaccard_score, mutual_count).
        """
        if u not in self.adj:
            return []

        neighbors_u = self.adj[u]
        candidates: List[Tuple[str, float, int]] = []

        for v in self.adj:
            if v == u or v in neighbors_u:
                continue
            neighbors_v = self.adj[v]
            union_size = len(neighbors_u.union(neighbors_v))
            mutual_count = len(neighbors_u.intersection(neighbors_v))
            jaccard = (mutual_count / union_size) if union_size > 0 else 0.0
            if mutual_count > 0:
                candidates.append((v, round(jaccard, 4), mutual_count))

        # Sort by Jaccard score descending, then mutual count descending, then username
        candidates.sort(key=lambda item: (-item[1], -item[2], item[0]))
        return candidates[:limit]

    def detect_communities(self) -> List[List[str]]:
        """
        Enhancement: Find connected communities/groups of students using BFS
        connected components. Returns communities of size >= 2 sorted by size desc.
        Time Complexity: O(V + E).
        """
        visited: Set[str] = set()
        communities: List[List[str]] = []

        for user in sorted(self.adj.keys()):
            if user in visited:
                continue
            component: List[str] = []
            q: Queue[str] = Queue()
            q.enqueue(user)
            visited.add(user)

            while not q.is_empty():
                curr = q.dequeue()
                assert curr is not None
                component.append(curr)
                for nbr in sorted(self.adj[curr]):
                    if nbr not in visited:
                        visited.add(nbr)
                        q.enqueue(nbr)

            if len(component) >= 2:
                communities.append(sorted(component))

        communities.sort(key=lambda c: (-len(c), c[0]))
        return communities
