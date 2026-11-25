# ChanakyaConnect — Design & DSA Report

**Course:** Data Structures and Algorithms (III Semester B.Tech., 2026–27)  
**Institution:** School of Engineering, Chanakya University, Bangalore  
**Project:** Student Networking Application (`ChanakyaConnect`)

---

## 1. Problem Statement & Graph Model
ChanakyaConnect models the university student network as a graph $G(V, E)$:
- **Vertices ($V$):** Registered students (`User` nodes with profile picture, programme, year, bio, skills, and endorsements).
- **Undirected Edges ($E$):** Accepted mutual connections stored in **adjacency lists** (`SocialGraph.adj`). Self-edges and duplicate edges are strictly prevented.
- **Directed Pending Edges:** Connection requests from sender to receiver stored in per-receiver **FIFO Queues** (`incoming_requests`) and per-sender sets (`outgoing_requests`) until accepted, rejected, or cancelled.

## 2. System Architecture
The system enforces a strict three-layer separation:
1. **Core Engine (`core/`):** Holds all in-memory data structures and executes every graph, search, feed, job-matching, and recommendation algorithm in Python memory.
2. **Persistence (`storage/json_store.py`):** Stores raw serialized entities (`users`, `connections`, `pending_requests`, `posts`, `notifications`, `jobs`, `messages`) in `data/network_data.json` using atomic file replacement (`os.replace`).
3. **Interfaces (`web/` & `cli/`):** Both the FastAPI web frontend and the terminal menu CLI invoke the exact same `ChanakyaConnectEngine` API.

## 3. Data Structures & Algorithms Used

| Feature | Data Structure / Algorithm | Justification & Complexity |
| :--- | :--- | :--- |
| **User, Post, Job & DM Lookup** | Custom `HashTable` (Separate Chaining, load factor 0.75) | $O(1)$ average-case lookup, insertion, and deletion by `username`, `post_id`, `job_id`, or DM thread key. |
| **Authentication** | `hashlib.pbkdf2_hmac` (SHA-256 + 16-byte random salt) | Passwords are never stored in plain text; verified via constant-time `hmac.compare_digest`. |
| **Prefix Search** | `Trie` (Case-insensitive Prefix Tree) | Indexes usernames, full names, and name tokens for $O(P + K)$ autocomplete suggestions as you type. |
| **Network Storage** | Adjacency Lists (`Dict[str, Set[str]]`) | $O(V + E)$ space; $O(1)$ average edge lookup and fast set intersection for mutual connections. |
| **Degree & Shortest Chain** | Breadth-First Search (`BFS` using `Queue`) | Guarantees shortest unweighted path in $O(V + E)$ time to compute 1st/2nd/3rd degree and connection chain. |
| **People You May Know** | Jaccard Similarity $J(u, v) = \frac{\|N(u) \cap N(v)\|}{\|N(u) \cup N(v)\|}$ | Ranks unconnected students by neighborhood overlap. |
| **Pending Requests & Alerts** | Custom `Queue` (FIFO via `collections.deque`) | $O(1)$ enqueue/dequeue for incoming connection requests, likes, comments, DMs, and job application updates. |
| **Home Feed Merge** | Custom `MaxHeap` (K-way Merge) | Merges connections' time-ordered post lists newest-first in $O(N \log C)$ time ($C$ = connections). |
| **Trending Posts & Job Match** | Custom `MaxHeap` (Priority Queue) | Ranks trending posts by engagement/recency and ranks jobs by skill-overlap percentage + recency. |
| **Nested Comments** | N-ary `CommentNode` Tree | Supports arbitrary-depth replies; traversed and counted via DFS. |
| **Undo & Back Navigation** | Custom `Stack` (LIFO) | $O(1)$ push/pop for restoring recently deleted posts and navigating back across views. |
| **Student Communities** | BFS Connected Components | Discovers closely connected student clusters in $O(V + E)$ time. |

## 4. Enhancements Implemented
- **Image & Video Posts + Profile Pictures:** Local media upload (`/api/upload-media`) and playback (`<img>` / `<video>`), plus circular profile avatars.
- **Jobs & Internships Board:** Post roles, filter by skill/title, apply, and **Accept / Reject** applicants with live status tracking and notifications.
- **Direct Messaging & Skill Endorsements:** 1-on-1 messaging threads stored in `HashTable` and `+1` skill endorsements on student profiles.

## 5. Verification Summary
- Automated `unittest` suite (`tests/test_engine.py`, 7 tests) verifies `HashTable` resizing, `Trie` prefix matching, `Queue`/`Stack`/`MaxHeap` invariants, `SocialGraph` BFS/Jaccard/communities, nested comment trees, undo-delete stacks, Jobs/DMs/Endorsements, password hashing, and restart persistence.
