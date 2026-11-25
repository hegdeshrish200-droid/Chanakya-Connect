"""
FastAPI Web Interface & REST API for ChanakyaConnect.

Exposes the decoupled `ChanakyaConnectEngine` over HTTP JSON endpoints
and serves the responsive web frontend.
Run with:
    uvicorn web.app:app --reload
"""

import base64
import os
import uuid
from typing import List, Optional

from fastapi import Body, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.engine import ChanakyaConnectEngine

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "network_data.json")
INDEX_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="ChanakyaConnect", description="Chanakya University Student Networking App")
engine = ChanakyaConnectEngine(storage_path=DATA_PATH)


# ------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------
class SignupRequest(BaseModel):
    username: str
    password: str
    name: str
    programme: str
    year: int
    bio: str = ""
    skills: List[str] = []
    profile_pic: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    programme: Optional[str] = None
    year: Optional[int] = None
    bio: Optional[str] = None
    skills: Optional[List[str]] = None
    profile_pic: Optional[str] = None
    resume_url: Optional[str] = None


class PostCreateRequest(BaseModel):
    content: str
    image_url: Optional[str] = None
    media_type: Optional[str] = None


class MediaUploadRequest(BaseModel):
    filename: str
    data_url: str


class CommentCreateRequest(BaseModel):
    text: str
    parent_comment_id: Optional[str] = None


class JobCreateRequest(BaseModel):
    title: str
    company: str
    location: str = "Bangalore"
    job_type: str = "Internship"
    description: str = ""
    required_skills: List[str] = []


class MessageCreateRequest(BaseModel):
    text: str


class EndorseRequest(BaseModel):
    skill: str


class JobApplyRequest(BaseModel):
    resume_url: Optional[str] = None


class JobDecisionRequest(BaseModel):
    applicant: str
    decision: str


# ------------------------------------------------------------------
# Auth Helper
# ------------------------------------------------------------------
def require_user(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    username = engine.get_user_by_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return username


# ------------------------------------------------------------------
# Web Frontend Route
# ------------------------------------------------------------------
@app.get("/")
def home_page():
    return FileResponse(INDEX_HTML, media_type="text/html", headers={"Cache-Control": "no-store"})


@app.get("/uploads/{filename}")
def serve_upload(filename: str):
    safe_name = os.path.basename(filename)
    path = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Media not found")
    return FileResponse(path)


@app.post("/api/upload-media")
def api_upload_media(body: MediaUploadRequest, authorization: Optional[str] = Header(default=None)):
    require_user(authorization)
    if "," not in body.data_url or not body.data_url.startswith("data:"):
        raise HTTPException(status_code=400, detail="Invalid media payload")
    header, b64_data = body.data_url.split(",", 1)
    mime = header[5:].split(";")[0].lower()
    if mime.startswith("video/"):
        media_type = "video"
    elif mime.startswith("image/"):
        media_type = "image"
    elif mime in (
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        media_type = "document"
    else:
        raise HTTPException(status_code=400, detail="Supported files: images, videos, PDF, DOC/DOCX")
    ext = os.path.splitext(body.filename)[1].lower()
    if not ext:
        ext = "." + mime.split("/")[-1].split("+")[0]
    safe_filename = f"{uuid.uuid4().hex[:12]}{ext}"
    out_path = os.path.join(UPLOAD_DIR, safe_filename)
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64_data))
    return {"url": f"/uploads/{safe_filename}", "media_type": media_type}


# ------------------------------------------------------------------
# Part 1: Accounts & Profiles
# ------------------------------------------------------------------
@app.post("/api/auth/signup")
def api_signup(body: SignupRequest):
    ok, msg = engine.signup(
        username=body.username,
        password=body.password,
        name=body.name,
        programme=body.programme,
        year=body.year,
        bio=body.bio,
        skills=body.skills,
        profile_pic=body.profile_pic,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/api/auth/login")
def api_login(body: LoginRequest):
    ok, msg, token = engine.login(body.username, body.password)
    if not ok or token is None:
        raise HTTPException(status_code=401, detail=msg)
    profile = engine.get_profile(body.username)
    return {"message": msg, "token": token, "user": profile}


@app.post("/api/auth/logout")
def api_logout(authorization: Optional[str] = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        engine.logout(authorization.split(" ", 1)[1].strip())
    return {"message": "Logged out"}


@app.get("/api/users/{username}")
def api_get_profile(username: str, authorization: Optional[str] = Header(default=None)):
    viewer = require_user(authorization)
    profile = engine.get_profile(username)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    degree, path = engine.get_connection_degree_and_path(viewer, username)
    mutuals = engine.get_mutual_connections(viewer, username) if viewer != username.lower() else []
    posts = engine.get_user_posts(username)
    return {
        "profile": profile,
        "degree": degree,
        "shortest_chain": path,
        "mutual_connections": mutuals,
        "is_connected": engine.graph.are_connected(viewer, username.lower()),
        "has_outgoing_request": engine.graph.has_pending_request(viewer, username.lower()),
        "has_incoming_request": engine.graph.has_pending_request(username.lower(), viewer),
        "posts": posts,
    }


@app.put("/api/profile")
def api_update_profile(body: ProfileUpdateRequest, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg = engine.update_profile(
        username=username,
        name=body.name,
        programme=body.programme,
        year=body.year,
        bio=body.bio,
        skills=body.skills,
        profile_pic=body.profile_pic,
        resume_url=body.resume_url,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "user": engine.get_profile(username)}


# ------------------------------------------------------------------
# Part 2: Connections & Graph Features
# ------------------------------------------------------------------
@app.get("/api/connections")
def api_connections(authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    return {
        "connections": engine.get_connections(username),
        "pending": engine.get_pending_requests(username),
        "suggestions": engine.get_people_you_may_know(username),
        "communities": engine.get_communities(),
    }


@app.post("/api/connections/request/{target}")
def api_send_request(target: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg = engine.send_connection_request(username, target)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/api/connections/accept/{sender}")
def api_accept_request(sender: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg = engine.accept_connection_request(username, sender)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/api/connections/reject/{sender}")
def api_reject_request(sender: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg = engine.reject_connection_request(username, sender)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/api/connections/cancel/{target}")
def api_cancel_request(target: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg = engine.cancel_connection_request(username, target)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.delete("/api/connections/{target}")
def api_remove_connection(target: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg = engine.remove_connection(username, target)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.get("/api/connections/path/{target}")
def api_connection_path(target: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    if not engine.users.contains(target.lower()):
        raise HTTPException(status_code=404, detail="Target user not found")
    degree, path = engine.get_connection_degree_and_path(username, target)
    mutuals = engine.get_mutual_connections(username, target)
    return {"degree": degree, "path": path, "mutuals": mutuals}


# ------------------------------------------------------------------
# Part 3: Posts, Feed, Trending, Likes, Comments, Undo
# ------------------------------------------------------------------
@app.get("/api/feed")
def api_feed(authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    return {
        "feed": engine.get_home_feed(username),
        "trending": engine.get_trending_posts(username),
        "my_posts": engine.get_user_posts(username),
    }


@app.post("/api/posts")
def api_create_post(body: PostCreateRequest, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg, post = engine.create_post(username, body.content, body.image_url, body.media_type)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "post": post}


@app.delete("/api/posts/{post_id}")
def api_delete_post(post_id: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg = engine.delete_post(username, post_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/api/posts/undo-delete")
def api_undo_delete(authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg, post = engine.undo_delete_post(username)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "post": post}


@app.post("/api/posts/{post_id}/like")
def api_toggle_like(post_id: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg, liked = engine.toggle_like(username, post_id)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"message": msg, "liked": liked}


@app.post("/api/posts/{post_id}/comments")
def api_add_comment(
    post_id: str,
    body: CommentCreateRequest,
    authorization: Optional[str] = Header(default=None),
):
    username = require_user(authorization)
    ok, msg, comment = engine.add_comment(username, post_id, body.text, body.parent_comment_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "comment": comment}


# ------------------------------------------------------------------
# Part 4: Trie Prefix Search & Notifications & Stats
# ------------------------------------------------------------------
@app.get("/api/search")
def api_search(
    q: str = Query(..., min_length=1),
    authorization: Optional[str] = Header(default=None),
):
    require_user(authorization)
    return {"results": engine.search_users(q, limit=10)}


@app.get("/api/notifications")
def api_notifications(authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    return {"notifications": engine.get_notifications(username)}


@app.post("/api/notifications/read-all")
def api_read_notifications(authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    count = engine.mark_all_notifications_read(username)
    return {"marked_read": count}


@app.get("/api/stats")
def api_stats():
    return engine.get_network_stats()

# ------------------------------------------------------------------
# LinkedIn Features: Jobs, Direct Messaging, Skill Endorsements
# ------------------------------------------------------------------
@app.post("/api/users/{username}/endorse")
def api_endorse(username: str, body: EndorseRequest, authorization: Optional[str] = Header(default=None)):
    actor = require_user(authorization)
    ok, msg = engine.endorse_skill(actor, username, body.skill)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.get("/api/jobs")
def api_list_jobs(q: str = "", authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    return {"jobs": engine.get_jobs_for_user(username, query=q)}


@app.post("/api/jobs")
def api_create_job(body: JobCreateRequest, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg, job = engine.create_job(
        posted_by=username,
        title=body.title,
        company=body.company,
        location=body.location,
        job_type=body.job_type,
        description=body.description,
        required_skills=body.required_skills,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "job": job}


@app.post("/api/jobs/{job_id}/apply")
def api_apply_job(
    job_id: str,
    body: Optional[JobApplyRequest] = Body(default=None),
    authorization: Optional[str] = Header(default=None),
):
    username = require_user(authorization)
    ok, msg = engine.apply_to_job(username, job_id, body.resume_url if body else None)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.delete("/api/jobs/{job_id}")
def api_delete_job(job_id: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg = engine.delete_job(username, job_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.post("/api/jobs/{job_id}/respond")
def api_respond_job(
    job_id: str,
    body: JobDecisionRequest,
    authorization: Optional[str] = Header(default=None),
):
    username = require_user(authorization)
    ok, msg = engine.respond_to_job_application(username, job_id, body.applicant, body.decision)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.get("/api/messages")
def api_conversations(authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    return {
        "conversations": engine.get_conversations(username),
        "connections": engine.get_connections(username),
    }


@app.get("/api/messages/{peer}")
def api_get_messages(peer: str, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    return {"messages": engine.get_messages(username, peer), "peer": engine.get_profile(peer)}


@app.post("/api/messages/{peer}")
def api_send_message(peer: str, body: MessageCreateRequest, authorization: Optional[str] = Header(default=None)):
    username = require_user(authorization)
    ok, msg, dm = engine.send_message(username, peer, body.text)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "dm": dm}
