"""Core data models for ChanakyaConnect."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import uuid


@dataclass
class User:
    """Represents a student node in the social network graph."""
    username: str
    password_hash: str
    password_salt: str
    name: str
    programme: str  # e.g., "B.Tech CSAI", "B.Tech EVE", "B.Tech EECS"
    year: int       # e.g., 1, 2, 3, 4
    bio: str = ""
    skills: List[str] = field(default_factory=list)
    profile_pic: Optional[str] = None
    resume_url: Optional[str] = None
    endorsements: Dict[str, List[str]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_public_dict(self) -> dict:
        """Return user profile without sensitive auth fields."""
        return {
            "username": self.username,
            "name": self.name,
            "programme": self.programme,
            "year": self.year,
            "bio": self.bio,
            "skills": list(self.skills),
            "profile_pic": self.profile_pic,
            "resume_url": self.resume_url,
            "endorsements": {k: list(v) for k, v in self.endorsements.items()},
            "created_at": self.created_at,
        }

    def to_storage_dict(self) -> dict:
        """Serialize full user record for persistence."""
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "password_salt": self.password_salt,
            "name": self.name,
            "programme": self.programme,
            "year": self.year,
            "bio": self.bio,
            "skills": list(self.skills),
            "profile_pic": self.profile_pic,
            "resume_url": self.resume_url,
            "endorsements": {k: list(v) for k, v in self.endorsements.items()},
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            password_salt=data["password_salt"],
            name=data["name"],
            programme=data["programme"],
            year=int(data["year"]),
            bio=data.get("bio", ""),
            skills=list(data.get("skills", [])),
            profile_pic=data.get("profile_pic"),
            resume_url=data.get("resume_url"),
            endorsements={k: list(v) for k, v in data.get("endorsements", {}).items()},
            created_at=float(data.get("created_at", time.time())),
        )


@dataclass
class CommentNode:
    """
    Tree node representing a comment or a nested reply on a post.
    Each post holds a list of top-level CommentNodes, and each CommentNode
    holds a list of child CommentNodes (forming an N-ary comment tree).
    """
    comment_id: str
    author: str
    text: str
    created_at: float = field(default_factory=time.time)
    replies: List["CommentNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "comment_id": self.comment_id,
            "author": self.author,
            "text": self.text,
            "created_at": self.created_at,
            "replies": [r.to_dict() for r in self.replies],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CommentNode":
        return cls(
            comment_id=data["comment_id"],
            author=data["author"],
            text=data["text"],
            created_at=float(data.get("created_at", time.time())),
            replies=[cls.from_dict(r) for r in data.get("replies", [])],
        )


@dataclass
class Post:
    """Represents a project or technical idea post (text + optional image)."""
    post_id: str
    author: str
    content: str
    image_url: Optional[str] = None
    media_type: Optional[str] = None  # "image" or "video"
    created_at: float = field(default_factory=time.time)
    likes: List[str] = field(default_factory=list)
    comments: List[CommentNode] = field(default_factory=list)

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())[:8]

    def total_comment_count(self) -> int:
        """Count all comments and nested replies via DFS traversal."""
        def _count(nodes: List[CommentNode]) -> int:
            total = 0
            for node in nodes:
                total += 1 + _count(node.replies)
            return total
        return _count(self.comments)

    def to_dict(self) -> dict:
        return {
            "post_id": self.post_id,
            "author": self.author,
            "content": self.content,
            "image_url": self.image_url,
            "media_type": self.media_type,
            "created_at": self.created_at,
            "likes": list(self.likes),
            "comments": [c.to_dict() for c in self.comments],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Post":
        return cls(
            post_id=data["post_id"],
            author=data["author"],
            content=data["content"],
            image_url=data.get("image_url"),
            media_type=data.get("media_type"),
            created_at=float(data.get("created_at", time.time())),
            likes=list(data.get("likes", [])),
            comments=[CommentNode.from_dict(c) for c in data.get("comments", [])],
        )


@dataclass
class Notification:
    """Represents an alert queued for a user (connection request, like, comment)."""
    notif_id: str
    recipient: str
    notif_type: str  # "connection_request", "connection_accepted", "like", "comment"
    message: str
    actor: str
    created_at: float = field(default_factory=time.time)
    is_read: bool = False

    def to_dict(self) -> dict:
        return {
            "notif_id": self.notif_id,
            "recipient": self.recipient,
            "notif_type": self.notif_type,
            "message": self.message,
            "actor": self.actor,
            "created_at": self.created_at,
            "is_read": self.is_read,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Notification":
        return cls(
            notif_id=data["notif_id"],
            recipient=data["recipient"],
            notif_type=data["notif_type"],
            message=data["message"],
            actor=data["actor"],
            created_at=float(data.get("created_at", time.time())),
            is_read=bool(data.get("is_read", False)),
        )


@dataclass
class JobPosting:
    """Represents an internship, research role, or job posting."""
    job_id: str
    posted_by: str
    title: str
    company: str
    location: str
    job_type: str  # e.g., "Internship", "Full-Time", "Research"
    description: str
    required_skills: List[str] = field(default_factory=list)
    applicants: List[str] = field(default_factory=list)
    application_statuses: Dict[str, str] = field(default_factory=dict)
    application_resumes: Dict[str, Optional[str]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())[:8]

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "posted_by": self.posted_by,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "job_type": self.job_type,
            "description": self.description,
            "required_skills": list(self.required_skills),
            "applicants": list(self.applicants),
            "application_statuses": dict(self.application_statuses),
            "application_resumes": dict(self.application_resumes),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobPosting":
        return cls(
            job_id=data["job_id"],
            posted_by=data["posted_by"],
            title=data["title"],
            company=data["company"],
            location=data.get("location", "Bangalore"),
            job_type=data.get("job_type", "Internship"),
            description=data.get("description", ""),
            required_skills=list(data.get("required_skills", [])),
            applicants=list(data.get("applicants", [])),
            application_statuses=dict(data.get("application_statuses", {})),
            application_resumes=dict(data.get("application_resumes", {})),
            created_at=float(data.get("created_at", time.time())),
        )


@dataclass
class DirectMessage:
    """Represents a 1-on-1 message between two users."""
    msg_id: str
    sender: str
    receiver: str
    text: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "text": self.text,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DirectMessage":
        return cls(
            msg_id=data["msg_id"],
            sender=data["sender"],
            receiver=data["receiver"],
            text=data["text"],
            created_at=float(data.get("created_at", time.time())),
        )
