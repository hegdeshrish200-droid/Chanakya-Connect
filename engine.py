"""
ChanakyaConnect Core Engine.

Completely decoupled from any UI (Console CLI or FastAPI Web UI).
Both interfaces invoke the exact same methods on `ChanakyaConnectEngine`.
"""

import hashlib
import hmac
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.data_structures import (
    HashTable,
    MaxHeap,
    Queue,
    SocialGraph,
    Stack,
    Trie,
)
from core.models import CommentNode, DirectMessage, JobPosting, Notification, Post, User
from storage.json_store import JsonStorage


class ChanakyaConnectEngine:
    """Main in-memory DSA engine for Chanakya University's student network."""

    def __init__(self, storage_path: str = "data/network_data.json") -> None:
        self.storage = JsonStorage(storage_path)

        # In-memory Data Structures
        self.users: HashTable[User] = HashTable()
        self.posts_by_id: HashTable[Post] = HashTable()
        self.user_posts: HashTable[List[Post]] = HashTable()
        self.search_trie: Trie = Trie()
        self.graph: SocialGraph = SocialGraph()
        self.notifications: HashTable[Queue[Notification]] = HashTable()

        # Per-user Stacks for Undo (deleted posts) and Back Navigation
        self.undo_delete_stacks: HashTable[Stack[Post]] = HashTable()
        self.nav_stacks: HashTable[Stack[str]] = HashTable()

        # Jobs & Direct Messages stored in HashTables
        self.jobs_by_id: HashTable[JobPosting] = HashTable()
        self.dm_threads: HashTable[List[DirectMessage]] = HashTable()

        # Active sessions (token -> username) in HashTable
        self.sessions: HashTable[str] = HashTable()

        self.load_from_storage()

    # ------------------------------------------------------------------
    # Password Hashing (PBKDF2-HMAC-SHA256 with per-user random salt)
    # ------------------------------------------------------------------
    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        if salt is None:
            salt = os.urandom(16).hex()
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            100_000,
        )
        return dk.hex(), salt

    @staticmethod
    def _verify_password(password: str, expected_hash: str, salt: str) -> bool:
        actual_hash, _ = ChanakyaConnectEngine._hash_password(password, salt)
        return hmac.compare_digest(actual_hash, expected_hash)

    # ------------------------------------------------------------------
    # Indexing & Initialization Helpers
    # ------------------------------------------------------------------
    def _index_user_in_trie(self, user: User) -> None:
        self.search_trie.insert(user.username, user.username)
        self.search_trie.insert(user.name, user.username)
        for token in user.name.split():
            if token:
                self.search_trie.insert(token, user.username)

    def _remove_user_from_trie(self, user: User) -> None:
        self.search_trie.remove(user.username, user.username)
        self.search_trie.remove(user.name, user.username)
        for token in user.name.split():
            if token:
                self.search_trie.remove(token, user.username)

    def _ensure_user_structures(self, username: str) -> None:
        self.graph.add_user(username)
        if not self.user_posts.contains(username):
            self.user_posts.put(username, [])
        if not self.notifications.contains(username):
            self.notifications.put(username, Queue())
        if not self.undo_delete_stacks.contains(username):
            self.undo_delete_stacks.put(username, Stack())
        if not self.nav_stacks.contains(username):
            self.nav_stacks.put(username, Stack())

    def _push_notification(
        self, recipient: str, notif_type: str, actor: str, message: str
    ) -> None:
        if not self.notifications.contains(recipient):
            self.notifications.put(recipient, Queue())
        q = self.notifications.get(recipient)
        assert q is not None
        q.enqueue(
            Notification(
                notif_id=str(uuid.uuid4())[:8],
                recipient=recipient,
                notif_type=notif_type,
                message=message,
                actor=actor,
            )
        )

    # ------------------------------------------------------------------
    # Persistence (Load & Save raw state only)
    # ------------------------------------------------------------------
    def load_from_storage(self) -> None:
        data = self.storage.load()

        for u_dict in data.get("users", []):
            user = User.from_dict(u_dict)
            self.users.put(user.username, user)
            self._ensure_user_structures(user.username)
            self._index_user_in_trie(user)

        for pair in data.get("connections", []):
            if len(pair) == 2:
                u, v = pair[0], pair[1]
                if self.users.contains(u) and self.users.contains(v) and u != v:
                    self.graph.adj[u].add(v)
                    self.graph.adj[v].add(u)

        for req in data.get("pending_requests", []):
            sender, receiver = req.get("sender"), req.get("receiver")
            if (
                sender
                and receiver
                and self.users.contains(sender)
                and self.users.contains(receiver)
                and not self.graph.are_connected(sender, receiver)
            ):
                if not self.graph.has_pending_request(sender, receiver):
                    self.graph.outgoing_requests[sender].add(receiver)
                    self.graph.incoming_requests[receiver].enqueue(sender)

        for p_dict in data.get("posts", []):
            post = Post.from_dict(p_dict)
            if self.users.contains(post.author):
                self.posts_by_id.put(post.post_id, post)
                posts_list = self.user_posts.get(post.author)
                if posts_list is not None:
                    posts_list.append(post)

        # Keep each user's posts sorted newest-first for K-way heap merge
        for username in self.user_posts.keys():
            plist = self.user_posts.get(username)
            if plist is not None:
                plist.sort(key=lambda p: p.created_at, reverse=True)

        for username, notif_list in data.get("notifications", {}).items():
            if self.users.contains(username):
                q = self.notifications.get(username)
                if q is not None:
                    for n_dict in notif_list:
                        q.enqueue(Notification.from_dict(n_dict))

        for j_dict in data.get("jobs", []):
            job = JobPosting.from_dict(j_dict)
            if self.users.contains(job.posted_by):
                self.jobs_by_id.put(job.job_id, job)

        for thread_key, msg_list in data.get("messages", {}).items():
            self.dm_threads.put(thread_key, [DirectMessage.from_dict(m) for m in msg_list])

    def save_to_storage(self) -> None:
        # Serialize undirected edges once (u < v)
        edges: List[List[str]] = []
        seen_edges = set()
        for u, nbrs in self.graph.adj.items():
            for v in nbrs:
                edge = tuple(sorted((u, v)))
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    edges.append([edge[0], edge[1]])

        pending: List[Dict[str, str]] = []
        for receiver, q in self.graph.incoming_requests.items():
            for sender in q.to_list():
                pending.append({"sender": sender, "receiver": receiver})

        notif_dict: Dict[str, List[dict]] = {}
        for username, q in self.notifications.items():
            notif_dict[username] = [n.to_dict() for n in q.to_list()]

        state = {
            "users": [u.to_storage_dict() for u in self.users.values()],
            "connections": edges,
            "pending_requests": pending,
            "posts": [p.to_dict() for p in self.posts_by_id.values()],
            "notifications": notif_dict,
            "jobs": [j.to_dict() for j in self.jobs_by_id.values()],
            "messages": {k: [m.to_dict() for m in v] for k, v in self.dm_threads.items()},
        }
        self.storage.save(state)

    # ------------------------------------------------------------------
    # Part 1: Accounts & Profiles
    # ------------------------------------------------------------------
    def signup(
        self,
        username: str,
        password: str,
        name: str,
        programme: str,
        year: int,
        bio: str = "",
        skills: Optional[List[str]] = None,
        profile_pic: Optional[str] = None,
    ) -> Tuple[bool, str]:
        username = username.strip().lower()
        if not username or " " in username:
            return False, "Username must be non-empty and contain no spaces."
        if len(password) < 4:
            return False, "Password must be at least 4 characters long."
        if self.users.contains(username):
            return False, f"Username '{username}' is already taken."

        pw_hash, salt = self._hash_password(password)
        user = User(
            username=username,
            password_hash=pw_hash,
            password_salt=salt,
            name=name.strip(),
            programme=programme.strip(),
            year=int(year),
            bio=bio.strip(),
            skills=[s.strip() for s in (skills or []) if s.strip()],
            profile_pic=profile_pic.strip() if profile_pic and profile_pic.strip() else None,
        )
        self.users.put(username, user)
        self._ensure_user_structures(username)
        self._index_user_in_trie(user)
        self.save_to_storage()
        return True, f"Account '{username}' created successfully."

    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[str]]:
        username = username.strip().lower()
        user = self.users.get(username)
        if user is None or not self._verify_password(password, user.password_hash, user.password_salt):
            return False, "Invalid username or password.", None
        token = str(uuid.uuid4())
        self.sessions.put(token, username)
        return True, f"Welcome back, {user.name}!", token

    def logout(self, token: str) -> bool:
        return self.sessions.delete(token)

    def get_user_by_token(self, token: str) -> Optional[str]:
        return self.sessions.get(token)

    def get_profile(self, username: str) -> Optional[dict]:
        user = self.users.get(username.strip().lower())
        if user is None:
            return None
        profile = user.to_public_dict()
        profile["connection_count"] = len(self.graph.get_connections(user.username))
        profile["post_count"] = len(self.user_posts.get(user.username) or [])
        return profile

    def update_profile(
        self,
        username: str,
        name: Optional[str] = None,
        programme: Optional[str] = None,
        year: Optional[int] = None,
        bio: Optional[str] = None,
        skills: Optional[List[str]] = None,
        profile_pic: Optional[str] = None,
        resume_url: Optional[str] = None,
    ) -> Tuple[bool, str]:
        user = self.users.get(username.strip().lower())
        if user is None:
            return False, "User not found."
        if name is not None and name.strip():
            self._remove_user_from_trie(user)
            user.name = name.strip()
            self._index_user_in_trie(user)
        if programme is not None:
            user.programme = programme.strip()
        if year is not None:
            user.year = int(year)
        if bio is not None:
            user.bio = bio.strip()
        if skills is not None:
            user.skills = [s.strip() for s in skills if s.strip()]
        if profile_pic is not None:
            user.profile_pic = profile_pic.strip() or None
        if resume_url is not None:
            user.resume_url = resume_url.strip() or None
        self.save_to_storage()
        return True, "Profile updated successfully."

    # ------------------------------------------------------------------
    # Part 2: Connections & Graph Algorithms
    # ------------------------------------------------------------------
    def send_connection_request(self, sender: str, receiver: str) -> Tuple[bool, str]:
        sender, receiver = sender.lower(), receiver.lower()
        ok, msg = self.graph.send_request(sender, receiver)
        if ok:
            if self.graph.are_connected(sender, receiver):
                self._push_notification(
                    receiver, "connection_accepted", sender, f"{sender} accepted your connection request!"
                )
            else:
                self._push_notification(
                    receiver, "connection_request", sender, f"{sender} sent you a connection request."
                )
            self.save_to_storage()
        return ok, msg

    def accept_connection_request(self, receiver: str, sender: str) -> Tuple[bool, str]:
        receiver, sender = receiver.lower(), sender.lower()
        ok, msg = self.graph.accept_request(receiver, sender)
        if ok:
            self._push_notification(
                sender, "connection_accepted", receiver, f"{receiver} accepted your connection request!"
            )
            self.save_to_storage()
        return ok, msg

    def reject_connection_request(self, receiver: str, sender: str) -> Tuple[bool, str]:
        ok, msg = self.graph.reject_request(receiver.lower(), sender.lower())
        if ok:
            self.save_to_storage()
        return ok, msg

    def cancel_connection_request(self, sender: str, receiver: str) -> Tuple[bool, str]:
        ok, msg = self.graph.cancel_request(sender.lower(), receiver.lower())
        if ok:
            self.save_to_storage()
        return ok, msg

    def remove_connection(self, u: str, v: str) -> Tuple[bool, str]:
        ok, msg = self.graph.remove_connection(u.lower(), v.lower())
        if ok:
            self.save_to_storage()
        return ok, msg

    def get_connections(self, username: str) -> List[dict]:
        usernames = self.graph.get_connections(username.lower())
        return [p for u in usernames if (p := self.get_profile(u)) is not None]

    def get_pending_requests(self, username: str) -> Dict[str, List[dict]]:
        u = username.lower()
        incoming = [p for s in self.graph.get_pending_incoming(u) if (p := self.get_profile(s)) is not None]
        outgoing = [p for r in self.graph.get_pending_outgoing(u) if (p := self.get_profile(r)) is not None]
        return {"incoming": incoming, "outgoing": outgoing}

    def get_mutual_connections(self, u: str, v: str) -> List[dict]:
        mutuals = self.graph.mutual_connections(u.lower(), v.lower())
        return [p for m in mutuals if (p := self.get_profile(m)) is not None]

    def get_people_you_may_know(self, username: str, limit: int = 10) -> List[dict]:
        recs = self.graph.people_you_may_know(username.lower(), limit=limit)
        result = []
        for candidate, jaccard, mutual_count in recs:
            profile = self.get_profile(candidate)
            if profile:
                profile["jaccard_score"] = jaccard
                profile["mutual_count"] = mutual_count
                profile["mutuals"] = self.graph.mutual_connections(username.lower(), candidate)
                result.append(profile)
        return result

    def get_connection_degree_and_path(
        self, start: str, target: str
    ) -> Tuple[Optional[int], List[str]]:
        return self.graph.bfs_degree_and_path(start.lower(), target.lower())

    def get_communities(self) -> List[List[dict]]:
        raw_comms = self.graph.detect_communities()
        result = []
        for comm in raw_comms:
            profiles = [p for u in comm if (p := self.get_profile(u)) is not None]
            if profiles:
                result.append(profiles)
        return result

    # ------------------------------------------------------------------
    # Part 3: Posts, Feed (MaxHeap), Likes, Nested Comments (Tree), Undo (Stack)
    # ------------------------------------------------------------------
    def create_post(
        self,
        author: str,
        content: str,
        image_url: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[dict]]:
        author = author.lower()
        if not self.users.contains(author):
            return False, "User does not exist.", None
        if not content.strip() and not image_url:
            return False, "Post cannot be empty.", None

        clean_url = image_url.strip() if image_url and image_url.strip() else None
        inferred_type = media_type
        if clean_url and not inferred_type:
            lower = clean_url.lower().split("?")[0]
            inferred_type = "video" if lower.endswith((".mp4", ".webm", ".mov", ".ogg")) else "image"
        post = Post(
            post_id=Post.new_id(),
            author=author,
            content=content.strip(),
            image_url=clean_url,
            media_type=inferred_type,
        )
        self.posts_by_id.put(post.post_id, post)
        plist = self.user_posts.get(author)
        assert plist is not None
        plist.insert(0, post)
        self.save_to_storage()
        return True, "Post published!", self._serialize_post(post)

    def delete_post(self, username: str, post_id: str) -> Tuple[bool, str]:
        username = username.lower()
        post = self.posts_by_id.get(post_id)
        if post is None:
            return False, "Post not found."
        if post.author != username:
            return False, "You can only delete your own posts."

        self.posts_by_id.delete(post_id)
        plist = self.user_posts.get(username)
        if plist is not None:
            self.user_posts.put(username, [p for p in plist if p.post_id != post_id])

        # Push onto user's Undo Stack so they can restore it!
        undo_stack = self.undo_delete_stacks.get(username)
        if undo_stack is not None:
            undo_stack.push(post)

        self.save_to_storage()
        return True, f"Post {post_id} deleted (you can Undo this action)."

    def undo_delete_post(self, username: str) -> Tuple[bool, str, Optional[dict]]:
        username = username.lower()
        undo_stack = self.undo_delete_stacks.get(username)
        if undo_stack is None or undo_stack.is_empty():
            return False, "Nothing to undo.", None
        post = undo_stack.pop()
        assert post is not None
        self.posts_by_id.put(post.post_id, post)
        plist = self.user_posts.get(username)
        assert plist is not None
        plist.append(post)
        plist.sort(key=lambda p: p.created_at, reverse=True)
        self.save_to_storage()
        return True, f"Restored post {post.post_id}.", self._serialize_post(post)

    def get_user_posts(self, username: str) -> List[dict]:
        plist = self.user_posts.get(username.lower()) or []
        return [self._serialize_post(p) for p in plist]

    def get_home_feed(self, username: str, limit: int = 30) -> List[dict]:
        """
        Merge posts from all connections using a MaxHeap (newest first).
        Implements K-way merge over each connection's time-ordered post list.
        """
        connections = self.graph.get_connections(username.lower())
        heap: MaxHeap[Tuple[str, int, Post]] = MaxHeap()

        for conn in connections:
            plist = self.user_posts.get(conn) or []
            if plist:
                first_post = plist[0]
                heap.push(first_post.created_at, (conn, 0, first_post))

        feed: List[dict] = []
        while not heap.is_empty() and len(feed) < limit:
            item = heap.pop()
            assert item is not None
            conn, idx, post = item
            feed.append(self._serialize_post(post))
            plist = self.user_posts.get(conn) or []
            next_idx = idx + 1
            if next_idx < len(plist):
                next_post = plist[next_idx]
                heap.push(next_post.created_at, (conn, next_idx, next_post))

        return feed

    def get_trending_posts(self, username: str, limit: int = 10) -> List[dict]:
        """
        Enhancement: Rank posts among connections using a MaxHeap scored by
        engagement (likes * 2 + comments * 3) + recency decay.
        """
        connections = self.graph.get_connections(username.lower())
        now = time.time()
        heap: MaxHeap[Tuple[float, Post]] = MaxHeap()

        for conn in connections:
            for post in self.user_posts.get(conn) or []:
                engagement = len(post.likes) * 2 + post.total_comment_count() * 3
                age_hours = max(1.0, (now - post.created_at) / 3600.0)
                score = (engagement + 1.0) / (age_hours ** 0.5)
                heap.push(score, (score, post))

        trending: List[dict] = []
        while not heap.is_empty() and len(trending) < limit:
            item = heap.pop()
            assert item is not None
            score, post = item
            serialized = self._serialize_post(post)
            serialized["trending_score"] = round(score, 2)
            trending.append(serialized)
        return trending

    def toggle_like(self, username: str, post_id: str) -> Tuple[bool, str, bool]:
        username = username.lower()
        post = self.posts_by_id.get(post_id)
        if post is None:
            return False, "Post not found.", False
        if username in post.likes:
            post.likes.remove(username)
            self.save_to_storage()
            return True, "Unliked post.", False
        post.likes.append(username)
        if post.author != username:
            self._push_notification(
                post.author, "like", username, f"{username} liked your post ({post_id})."
            )
        self.save_to_storage()
        return True, "Liked post!", True

    def add_comment(
        self,
        username: str,
        post_id: str,
        text: str,
        parent_comment_id: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[dict]]:
        username = username.lower()
        post = self.posts_by_id.get(post_id)
        if post is None:
            return False, "Post not found.", None
        if not text.strip():
            return False, "Comment cannot be empty.", None

        new_comment = CommentNode(
            comment_id=str(uuid.uuid4())[:8],
            author=username,
            text=text.strip(),
        )

        if parent_comment_id:
            # DFS search in CommentNode tree to find parent comment
            parent = self._find_comment_node(post.comments, parent_comment_id)
            if parent is None:
                return False, "Parent comment not found.", None
            parent.replies.append(new_comment)
        else:
            post.comments.append(new_comment)

        if post.author != username:
            self._push_notification(
                post.author, "comment", username, f"{username} commented on your post ({post_id})."
            )
        self.save_to_storage()
        return True, "Comment added.", new_comment.to_dict()

    def _find_comment_node(
        self, nodes: List[CommentNode], target_id: str
    ) -> Optional[CommentNode]:
        for node in nodes:
            if node.comment_id == target_id:
                return node
            found = self._find_comment_node(node.replies, target_id)
            if found is not None:
                return found
        return None

    def _serialize_post(self, post: Post) -> dict:
        d = post.to_dict()
        author_user = self.users.get(post.author)
        d["author_name"] = author_user.name if author_user else post.author
        d["author_programme"] = author_user.programme if author_user else ""
        d["author_profile_pic"] = author_user.profile_pic if author_user else None
        d["like_count"] = len(post.likes)
        d["comment_count"] = post.total_comment_count()
        return d

    # ------------------------------------------------------------------
    # Part 4: Search (Trie Prefix Search)
    # ------------------------------------------------------------------
    def search_users(self, prefix: str, limit: int = 10) -> List[dict]:
        matched_usernames = self.search_trie.search_prefix(prefix, limit=limit)
        return [p for u in matched_usernames if (p := self.get_profile(u)) is not None]

    # ------------------------------------------------------------------
    # Notifications (Queue) & Navigation History (Stack)
    # ------------------------------------------------------------------
    def get_notifications(self, username: str) -> List[dict]:
        q = self.notifications.get(username.lower())
        if q is None:
            return []
        # Return newest first for display while keeping FIFO queue internally
        return [n.to_dict() for n in reversed(q.to_list())]

    def pop_oldest_notification(self, username: str) -> Optional[dict]:
        q = self.notifications.get(username.lower())
        if q is None or q.is_empty():
            return None
        n = q.dequeue()
        self.save_to_storage()
        return n.to_dict() if n else None

    def mark_all_notifications_read(self, username: str) -> int:
        q = self.notifications.get(username.lower())
        if q is None:
            return 0
        count = 0
        for n in q.to_list():
            if not n.is_read:
                n.is_read = True
                count += 1
        if count > 0:
            self.save_to_storage()
        return count

    def push_navigation(self, username: str, view_name: str) -> None:
        st = self.nav_stacks.get(username.lower())
        if st is not None:
            st.push(view_name)

    def pop_navigation(self, username: str) -> Optional[str]:
        st = self.nav_stacks.get(username.lower())
        if st is None or st.is_empty():
            return None
        return st.pop()

    def get_network_stats(self) -> Dict[str, Any]:
        edge_count = sum(len(nbrs) for nbrs in self.graph.adj.values()) // 2
        return {
            "total_users": len(self.users),
            "total_connections": edge_count,
            "total_posts": len(self.posts_by_id),
            "communities_count": len(self.graph.detect_communities()),
        }

    # ------------------------------------------------------------------
    # LinkedIn Features: Skill Endorsements, Jobs Board (MaxHeap), Messaging
    # ------------------------------------------------------------------
    def endorse_skill(self, endorser: str, target: str, skill: str) -> Tuple[bool, str]:
        endorser, target = endorser.lower(), target.lower()
        if endorser == target:
            return False, "You cannot endorse your own skill."
        user = self.users.get(target)
        if user is None:
            return False, "User not found."
        clean_skill = skill.strip()
        if not clean_skill:
            return False, "Skill cannot be empty."
        endorsers = user.endorsements.setdefault(clean_skill, [])
        if endorser in endorsers:
            endorsers.remove(endorser)
            self.save_to_storage()
            return True, f"Removed endorsement for {clean_skill}."
        endorsers.append(endorser)
        self._push_notification(
            target, "endorsement", endorser, f"{endorser} endorsed your skill: {clean_skill}."
        )
        self.save_to_storage()
        return True, f"Endorsed {target} for {clean_skill}!"

    def create_job(
        self,
        posted_by: str,
        title: str,
        company: str,
        location: str,
        job_type: str,
        description: str,
        required_skills: Optional[List[str]] = None,
    ) -> Tuple[bool, str, Optional[dict]]:
        posted_by = posted_by.lower()
        if not self.users.contains(posted_by):
            return False, "User does not exist.", None
        if not title.strip() or not company.strip():
            return False, "Job title and company are required.", None
        job = JobPosting(
            job_id=JobPosting.new_id(),
            posted_by=posted_by,
            title=title.strip(),
            company=company.strip(),
            location=location.strip() or "Bangalore",
            job_type=job_type.strip() or "Internship",
            description=description.strip(),
            required_skills=[s.strip() for s in (required_skills or []) if s.strip()],
        )
        self.jobs_by_id.put(job.job_id, job)
        self.save_to_storage()
        return True, "Job posted!", self._serialize_job(job, posted_by)

    def get_jobs_for_user(self, username: str, query: str = "") -> List[dict]:
        """Rank jobs using MaxHeap by skill match percentage + recency."""
        username = username.lower()
        user = self.users.get(username)
        user_skills = {s.lower() for s in (user.skills if user else [])}
        q_clean = query.strip().lower()
        heap: MaxHeap[Tuple[float, JobPosting]] = MaxHeap()

        for job in self.jobs_by_id.values():
            if q_clean:
                hay = f"{job.title} {job.company} {job.location} {' '.join(job.required_skills)}".lower()
                if q_clean not in hay:
                    continue
            req = {s.lower() for s in job.required_skills}
            match_pct = (len(user_skills.intersection(req)) / len(req)) if req else 0.0
            score = match_pct * 1000.0 + (job.created_at / 1e10)
            heap.push(score, (round(match_pct * 100, 1), job))

        results: List[dict] = []
        while not heap.is_empty():
            item = heap.pop()
            assert item is not None
            pct, job = item
            d = self._serialize_job(job, username)
            d["skill_match_pct"] = pct
            results.append(d)
        return results

    def apply_to_job(self, username: str, job_id: str, resume_url: Optional[str] = None) -> Tuple[bool, str]:
        username = username.lower()
        job = self.jobs_by_id.get(job_id)
        if job is None:
            return False, "Job not found."
        if username in job.applicants:
            return False, "You have already applied to this job."
        user = self.users.get(username)
        final_resume = (resume_url.strip() if resume_url and resume_url.strip() else None) or (user.resume_url if user else None)
        job.applicants.append(username)
        job.application_statuses[username] = "pending"
        if final_resume:
            job.application_resumes[username] = final_resume
        if job.posted_by != username:
            self._push_notification(
                job.posted_by,
                "job_application",
                username,
                f"{username} applied for {job.title} at {job.company}.",
            )
        self.save_to_storage()
        return True, f"Applied to {job.title} at {job.company}!"

    def respond_to_job_application(
        self, poster: str, job_id: str, applicant: str, decision: str
    ) -> Tuple[bool, str]:
        poster, applicant = poster.lower(), applicant.lower()
        decision = decision.strip().lower()
        if decision not in ("accepted", "rejected"):
            return False, "Decision must be 'accepted' or 'rejected'."
        job = self.jobs_by_id.get(job_id)
        if job is None:
            return False, "Job not found."
        if job.posted_by != poster:
            return False, "Only the job poster can review applications."
        if applicant not in job.applicants:
            return False, f"@{applicant} has not applied to this job."
        job.application_statuses[applicant] = decision
        self._push_notification(
            applicant,
            f"job_{decision}",
            poster,
            f"@{poster} {decision} your application for {job.title} at {job.company}!",
        )
        self.save_to_storage()
        return True, f"Application from @{applicant} marked as {decision}."

    def delete_job(self, username: str, job_id: str) -> Tuple[bool, str]:
        username = username.lower()
        job = self.jobs_by_id.get(job_id)
        if job is None:
            return False, "Job not found."
        if job.posted_by != username:
            return False, "Only the job poster can delete this job."
        self.jobs_by_id.delete(job_id)
        self.save_to_storage()
        return True, "Job posting removed."

    def _serialize_job(self, job: JobPosting, viewer: str) -> dict:
        d = job.to_dict()
        poster = self.users.get(job.posted_by)
        d["poster_name"] = poster.name if poster else job.posted_by
        d["applicant_count"] = len(job.applicants)
        d["has_applied"] = viewer in job.applicants
        d["my_status"] = job.application_statuses.get(viewer, "pending") if viewer in job.applicants else None
        if job.posted_by == viewer:
            details = []
            for app_u in job.applicants:
                u_obj = self.users.get(app_u)
                details.append({
                    "username": app_u,
                    "name": u_obj.name if u_obj else app_u,
                    "programme": u_obj.programme if u_obj else "",
                    "year": u_obj.year if u_obj else "",
                    "status": job.application_statuses.get(app_u, "pending"),
                    "resume_url": job.application_resumes.get(app_u) or (u_obj.resume_url if u_obj else None),
                    "skills": u_obj.skills if u_obj else [],
                    "bio": u_obj.bio if u_obj else "",
                })
            d["applicant_details"] = details
        else:
            d["applicant_details"] = []
        return d

    @staticmethod
    def _thread_key(u1: str, u2: str) -> str:
        a, b = sorted((u1.lower(), u2.lower()))
        return f"{a}|{b}"

    def send_message(self, sender: str, receiver: str, text: str) -> Tuple[bool, str, Optional[dict]]:
        sender, receiver = sender.lower(), receiver.lower()
        if sender == receiver:
            return False, "Cannot message yourself.", None
        if not self.users.contains(sender) or not self.users.contains(receiver):
            return False, "User does not exist.", None
        if not text.strip():
            return False, "Message cannot be empty.", None
        key = self._thread_key(sender, receiver)
        thread = self.dm_threads.get(key)
        if thread is None:
            thread = []
            self.dm_threads.put(key, thread)
        msg = DirectMessage(
            msg_id=str(uuid.uuid4())[:8],
            sender=sender,
            receiver=receiver,
            text=text.strip(),
        )
        thread.append(msg)
        self._push_notification(
            receiver, "message", sender, f"New message from {sender}: {msg.text[:40]}"
        )
        self.save_to_storage()
        return True, "Message sent.", msg.to_dict()

    def get_messages(self, u1: str, u2: str) -> List[dict]:
        key = self._thread_key(u1, u2)
        thread = self.dm_threads.get(key) or []
        return [m.to_dict() for m in thread]

    def get_conversations(self, username: str) -> List[dict]:
        u = username.lower()
        peers = []
        for key, thread in self.dm_threads.items():
            if not thread:
                continue
            a, b = key.split("|", 1)
            if u in (a, b):
                peer = b if a == u else a
                prof = self.get_profile(peer)
                if prof:
                    prof["last_message"] = thread[-1].text
                    prof["last_time"] = thread[-1].created_at
                    peers.append(prof)
        peers.sort(key=lambda x: -x["last_time"])
        return peers
