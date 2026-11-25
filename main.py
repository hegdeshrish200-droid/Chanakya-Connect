"""
Standalone Desktop GUI Application for ChanakyaConnect (Tkinter).

Uses Python's built-in `tkinter` (no extra dependencies) and invokes the exact
same `ChanakyaConnectEngine` as the FastAPI web app and Console CLI.

Run with:
    python gui/main.py
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.engine import ChanakyaConnectEngine


class ChanakyaConnectGUI(tk.Tk):
    """Native desktop window for ChanakyaConnect."""

    def __init__(self) -> None:
        super().__init__()
        self.title("ChanakyaConnect — Student Network")
        self.geometry("1040x700")
        self.minsize(900, 620)
        self.configure(bg="#f3f5f8")

        data_path = os.path.join(PROJECT_ROOT, "data", "network_data.json")
        self.engine = ChanakyaConnectEngine(storage_path=data_path)
        self.current_user: Optional[str] = None
        self.current_token: Optional[str] = None

        self._configure_styles()
        self.container = tk.Frame(self, bg="#f3f5f8")
        self.container.pack(fill="both", expand=True)

        self.show_auth_screen()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background="#f3f5f8")
        style.configure("TNotebook.Tab", padding=(14, 6), font=("Segoe UI", 10, "bold"))

    def _clear_container(self) -> None:
        for w in self.container.winfo_children():
            w.destroy()

    # ==================================================================
    # AUTH SCREEN (Login & Sign Up)
    # ==================================================================
    def show_auth_screen(self) -> None:
        self._clear_container()
        card = tk.Frame(self.container, bg="#ffffff", bd=1, relief="solid", padx=28, pady=24)
        card.place(relx=0.5, rely=0.5, anchor="center", width=430)

        tk.Label(card, text="ChanakyaConnect", font=("Segoe UI", 20, "bold"), fg="#1a56db", bg="#ffffff").pack(anchor="w")
        tk.Label(card, text="Chanakya University Student Network", font=("Segoe UI", 10), fg="#6b7280", bg="#ffffff").pack(anchor="w", pady=(0, 14))

        nb = ttk.Notebook(card)
        nb.pack(fill="both", expand=True)

        # Login Tab
        login_tab = tk.Frame(nb, bg="#ffffff", pady=12)
        nb.add(login_tab, text="Log In")

        tk.Label(login_tab, text="Username", bg="#ffffff", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        login_user = tk.Entry(login_tab, font=("Segoe UI", 10))
        login_user.pack(fill="x", pady=(2, 10))

        tk.Label(login_tab, text="Password", bg="#ffffff", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        login_pass = tk.Entry(login_tab, show="*", font=("Segoe UI", 10))
        login_pass.pack(fill="x", pady=(2, 12))

        def handle_login() -> None:
            u = login_user.get().strip()
            p = login_pass.get()
            ok, msg, tok = self.engine.login(u, p)
            if not ok or tok is None:
                messagebox.showerror("Login Failed", msg)
                return
            self.current_user = u.lower()
            self.current_token = tok
            self.engine.push_navigation(self.current_user, "Home Feed")
            self.show_main_screen()

        tk.Button(
            login_tab, text="Log In", bg="#1a56db", fg="#ffffff",
            font=("Segoe UI", 10, "bold"), relief="flat", pady=7, command=handle_login
        ).pack(fill="x")
        tk.Label(
            login_tab,
            text="Demo accounts (password: pass1234):\nshrish, ananya, rohan, meera, vikram, kavya",
            bg="#ffffff", fg="#6b7280", font=("Segoe UI", 8), justify="left"
        ).pack(anchor="w", pady=(10, 0))

        # Sign Up Tab
        su_tab = tk.Frame(nb, bg="#ffffff", pady=10)
        nb.add(su_tab, text="Sign Up")

        fields = {}
        for label, key, show in [
            ("Username", "username", ""),
            ("Password (min 4 chars)", "password", "*"),
            ("Full Name", "name", ""),
            ("Programme (e.g., B.Tech CSAI)", "programme", ""),
            ("Year (1-4)", "year", ""),
            ("Short Bio", "bio", ""),
            ("Skills (comma-separated)", "skills", ""),
        ]:
            tk.Label(su_tab, text=label, bg="#ffffff", font=("Segoe UI", 8, "bold")).pack(anchor="w")
            ent = tk.Entry(su_tab, show=show, font=("Segoe UI", 9))
            ent.pack(fill="x", pady=(1, 5))
            fields[key] = ent

        def handle_signup() -> None:
            try:
                year_val = int(fields["year"].get().strip() or "1")
            except ValueError:
                messagebox.showerror("Invalid Input", "Year must be a number (1-4).")
                return
            skills = [s.strip() for s in fields["skills"].get().split(",") if s.strip()]
            ok, msg = self.engine.signup(
                fields["username"].get(),
                fields["password"].get(),
                fields["name"].get(),
                fields["programme"].get(),
                year_val,
                fields["bio"].get(),
                skills,
            )
            if not ok:
                messagebox.showerror("Sign Up Failed", msg)
                return
            messagebox.showinfo("Account Created", msg + " You can now log in.")
            nb.select(0)

        tk.Button(
            su_tab, text="Create Account", bg="#059669", fg="#ffffff",
            font=("Segoe UI", 10, "bold"), relief="flat", pady=6, command=handle_signup
        ).pack(fill="x", pady=(6, 0))

    # ==================================================================
    # MAIN APPLICATION WINDOW
    # ==================================================================
    def show_main_screen(self) -> None:
        assert self.current_user is not None
        self._clear_container()

        # Top Bar
        topbar = tk.Frame(self.container, bg="#ffffff", bd=1, relief="solid", padx=16, pady=10)
        topbar.pack(fill="x")

        tk.Label(topbar, text="ChanakyaConnect", font=("Segoe UI", 14, "bold"), fg="#1a56db", bg="#ffffff").pack(side="left")
        tk.Label(topbar, text=f"  @{self.current_user}", font=("Segoe UI", 10), fg="#6b7280", bg="#ffffff").pack(side="left")

        # Trie Prefix Search Bar
        search_frame = tk.Frame(topbar, bg="#ffffff")
        search_frame.pack(side="left", padx=24)
        tk.Label(search_frame, text="Search (Trie):", bg="#ffffff", font=("Segoe UI", 9)).pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=28, font=("Segoe UI", 10))
        search_entry.pack(side="left", padx=6)
        tk.Button(search_frame, text="Find", command=self.run_trie_search, relief="groove").pack(side="left")

        # Right-side actions
        tk.Button(topbar, text="Log Out", fg="#dc2626", command=self.handle_logout, relief="groove").pack(side="right", padx=4)
        self.notif_btn = tk.Button(topbar, text="Alerts (0)", command=self.open_notifications_dialog, relief="groove")
        self.notif_btn.pack(side="right", padx=4)
        tk.Button(topbar, text="← Back (Stack)", command=self.handle_back, relief="groove").pack(side="right", padx=4)

        # Notebook Tabs
        self.notebook = ttk.Notebook(self.container)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=12)

        self.feed_tab = tk.Frame(self.notebook, bg="#f3f5f8")
        self.network_tab = tk.Frame(self.notebook, bg="#f3f5f8")
        self.profile_tab = tk.Frame(self.notebook, bg="#f3f5f8")

        self.notebook.add(self.feed_tab, text="Feed & Posts")
        self.notebook.add(self.network_tab, text="Network & Graph")
        self.notebook.add(self.profile_tab, text="My Profile")

        self._build_feed_tab()
        self._build_network_tab()
        self._build_profile_tab()
        self.refresh_all()

    def handle_logout(self) -> None:
        if self.current_token:
            self.engine.logout(self.current_token)
        self.current_user = None
        self.current_token = None
        self.show_auth_screen()

    def handle_back(self) -> None:
        assert self.current_user is not None
        prev = self.engine.pop_navigation(self.current_user)
        messagebox.showinfo("Navigation Stack", f"Popped view: {prev}" if prev else "Navigation stack is empty.")

    def refresh_all(self) -> None:
        if not self.current_user:
            return
        notifs = self.engine.get_notifications(self.current_user)
        unread = sum(1 for n in notifs if not n["is_read"])
        self.notif_btn.config(text=f"Alerts ({unread})")
        self.refresh_feed()
        self.refresh_network()
        self.refresh_profile()

    # ------------------------------------------------------------------
    # TRIE SEARCH POPUP
    # ------------------------------------------------------------------
    def run_trie_search(self) -> None:
        prefix = self.search_var.get().strip()
        if not prefix:
            messagebox.showinfo("Trie Search", "Type a name or username prefix first.")
            return
        results = self.engine.search_users(prefix, limit=15)
        win = tk.Toplevel(self)
        win.title(f"Trie Search Results for '{prefix}'")
        win.geometry("460x340")

        lb = tk.Listbox(win, font=("Segoe UI", 10))
        lb.pack(fill="both", expand=True, padx=12, pady=10)
        for u in results:
            lb.insert("end", f"@{u['username']} — {u['name']} ({u['programme']}, Yr {u['year']})")
        if not results:
            lb.insert("end", "No matching students found.")

        def connect_selected() -> None:
            sel = lb.curselection()
            if not sel or not results:
                return
            target = results[sel[0]]["username"]
            assert self.current_user is not None
            _, msg = self.engine.send_connection_request(self.current_user, target)
            messagebox.showinfo("Connection Request", msg)
            self.refresh_network()

        tk.Button(win, text="Send Connection Request to Selected", bg="#1a56db", fg="#ffffff", command=connect_selected).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # NOTIFICATIONS QUEUE DIALOG
    # ------------------------------------------------------------------
    def open_notifications_dialog(self) -> None:
        assert self.current_user is not None
        notifs = self.engine.get_notifications(self.current_user)
        win = tk.Toplevel(self)
        win.title("Notifications (FIFO Queue)")
        win.geometry("460x340")

        lb = tk.Listbox(win, font=("Segoe UI", 10))
        lb.pack(fill="both", expand=True, padx=12, pady=10)
        for n in notifs:
            tag = "READ" if n["is_read"] else "NEW"
            lb.insert("end", f"[{tag}] {n['message']}")
        if not notifs:
            lb.insert("end", "No notifications.")

        def mark_read() -> None:
            assert self.current_user is not None
            self.engine.mark_all_notifications_read(self.current_user)
            self.refresh_all()
            win.destroy()

        tk.Button(win, text="Mark All Read", command=mark_read).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # TAB 1: FEED & POSTS (MaxHeap + Comment Tree + Undo Stack)
    # ------------------------------------------------------------------
    def _build_feed_tab(self) -> None:
        top = tk.Frame(self.feed_tab, bg="#ffffff", bd=1, relief="solid", padx=12, pady=10)
        top.pack(fill="x", pady=(8, 8))

        tk.Label(top, text="Share a Project or Technical Idea", font=("Segoe UI", 10, "bold"), bg="#ffffff").pack(anchor="w")
        self.post_text = tk.Text(top, height=3, font=("Segoe UI", 10))
        self.post_text.pack(fill="x", pady=6)

        btn_row = tk.Frame(top, bg="#ffffff")
        btn_row.pack(fill="x")
        tk.Label(btn_row, text="Optional Image URL:", bg="#ffffff", font=("Segoe UI", 9)).pack(side="left")
        self.post_img_entry = tk.Entry(btn_row, width=32, font=("Segoe UI", 9))
        self.post_img_entry.pack(side="left", padx=6)
        tk.Button(btn_row, text="Publish Post", bg="#1a56db", fg="#ffffff", font=("Segoe UI", 9, "bold"), command=self.publish_post).pack(side="right")
        tk.Button(btn_row, text="Undo Delete (Stack)", command=self.undo_delete_post).pack(side="right", padx=6)

        # Feed mode selector
        mode_bar = tk.Frame(self.feed_tab, bg="#f3f5f8")
        mode_bar.pack(fill="x", pady=(0, 6))
        self.feed_mode = tk.StringVar(value="home")
        for label, val in [("Home Feed (MaxHeap)", "home"), ("Trending (MaxHeap)", "trending"), ("My Posts", "mine")]:
            tk.Radiobutton(
                mode_bar, text=label, variable=self.feed_mode, value=val,
                bg="#f3f5f8", font=("Segoe UI", 9, "bold"), command=self.refresh_feed
            ).pack(side="left", padx=6)

        # Posts listbox + detail/actions
        split = tk.PanedWindow(self.feed_tab, orient="horizontal", bg="#f3f5f8")
        split.pack(fill="both", expand=True)

        self.posts_listbox = tk.Listbox(split, font=("Segoe UI", 10), width=42)
        self.posts_listbox.bind("<<ListboxSelect>>", self.on_post_select)
        split.add(self.posts_listbox)

        detail_frame = tk.Frame(split, bg="#ffffff", bd=1, relief="solid", padx=12, pady=10)
        split.add(detail_frame)

        self.post_detail_text = tk.Text(detail_frame, state="disabled", wrap="word", font=("Segoe UI", 10), bg="#ffffff", relief="flat")
        self.post_detail_text.pack(fill="both", expand=True)

        act_row = tk.Frame(detail_frame, bg="#ffffff")
        act_row.pack(fill="x", pady=(8, 0))
        tk.Button(act_row, text="Like / Unlike", command=self.like_selected_post).pack(side="left", padx=2)
        tk.Button(act_row, text="Add Comment", command=self.comment_selected_post).pack(side="left", padx=2)
        tk.Button(act_row, text="Reply to Comment", command=self.reply_selected_post).pack(side="left", padx=2)
        tk.Button(act_row, text="Delete My Post", fg="#dc2626", command=self.delete_selected_post).pack(side="right", padx=2)

        self.displayed_posts = []

    def publish_post(self) -> None:
        assert self.current_user is not None
        content = self.post_text.get("1.0", "end").strip()
        img = self.post_img_entry.get().strip() or None
        ok, msg, _ = self.engine.create_post(self.current_user, content, img)
        if not ok:
            messagebox.showerror("Post Error", msg)
            return
        self.post_text.delete("1.0", "end")
        self.post_img_entry.delete(0, "end")
        self.refresh_feed()

    def undo_delete_post(self) -> None:
        assert self.current_user is not None
        _, msg, _ = self.engine.undo_delete_post(self.current_user)
        messagebox.showinfo("Undo Stack", msg)
        self.refresh_feed()

    def refresh_feed(self) -> None:
        assert self.current_user is not None
        mode = self.feed_mode.get()
        if mode == "home":
            self.displayed_posts = self.engine.get_home_feed(self.current_user)
        elif mode == "trending":
            self.displayed_posts = self.engine.get_trending_posts(self.current_user)
        else:
            self.displayed_posts = self.engine.get_user_posts(self.current_user)

        self.posts_listbox.delete(0, "end")
        for p in self.displayed_posts:
            preview = p["content"][:42].replace("\n", " ")
            self.posts_listbox.insert("end", f"@{p['author']}: {preview}...")
        self._render_post_detail(None)

    def _get_selected_post(self) -> Optional[dict]:
        sel = self.posts_listbox.curselection()
        if not sel or sel[0] >= len(self.displayed_posts):
            return None
        return self.displayed_posts[sel[0]]

    def on_post_select(self, _event=None) -> None:
        self._render_post_detail(self._get_selected_post())

    def _format_comments(self, comments: list, indent: int = 0) -> str:
        lines = []
        for c in comments:
            pad = "  " * indent
            lines.append(f"{pad}↳ [{c['comment_id']}] @{c['author']}: {c['text']}")
            if c.get("replies"):
                lines.append(self._format_comments(c["replies"], indent + 1))
        return "\n".join(lines)

    def _render_post_detail(self, post: Optional[dict]) -> None:
        self.post_detail_text.config(state="normal")
        self.post_detail_text.delete("1.0", "end")
        if post is None:
            self.post_detail_text.insert("end", "Select a post on the left to view details, likes, and nested comments.")
        else:
            header = f"{post.get('author_name', post['author'])} (@{post['author']}) · {post.get('author_programme', '')}\n"
            header += f"Post ID: {post['post_id']} | Likes: {post['like_count']} | Comments: {post['comment_count']}\n"
            if post.get("trending_score"):
                header += f"Trending Score: {post['trending_score']}\n"
            header += "-" * 50 + "\n\n"
            body = post["content"] + "\n"
            if post.get("image_url"):
                body += f"\n[Image URL: {post['image_url']}]\n"
            comments_str = self._format_comments(post.get("comments", []))
            if comments_str:
                body += "\n--- Comments (Tree) ---\n" + comments_str
            self.post_detail_text.insert("end", header + body)
        self.post_detail_text.config(state="disabled")

    def like_selected_post(self) -> None:
        assert self.current_user is not None
        p = self._get_selected_post()
        if not p:
            return
        self.engine.toggle_like(self.current_user, p["post_id"])
        self.refresh_feed()

    def comment_selected_post(self) -> None:
        assert self.current_user is not None
        p = self._get_selected_post()
        if not p:
            return
        text = simpledialog.askstring("Add Comment", "Write your comment:")
        if text:
            self.engine.add_comment(self.current_user, p["post_id"], text)
            self.refresh_feed()

    def reply_selected_post(self) -> None:
        assert self.current_user is not None
        p = self._get_selected_post()
        if not p:
            return
        parent_id = simpledialog.askstring("Reply to Comment", "Enter parent Comment ID (shown in brackets):")
        if not parent_id:
            return
        text = simpledialog.askstring("Reply", "Write your reply:")
        if text:
            ok, msg, _ = self.engine.add_comment(self.current_user, p["post_id"], text, parent_comment_id=parent_id.strip())
            if not ok:
                messagebox.showerror("Reply Error", msg)
            self.refresh_feed()

    def delete_selected_post(self) -> None:
        assert self.current_user is not None
        p = self._get_selected_post()
        if not p:
            return
        ok, msg = self.engine.delete_post(self.current_user, p["post_id"])
        messagebox.showinfo("Delete Post", msg)
        if ok:
            self.refresh_feed()

    # ------------------------------------------------------------------
    # TAB 2: NETWORK & GRAPH (Adjacency Lists, BFS, Jaccard, Communities)
    # ------------------------------------------------------------------
    def _build_network_tab(self) -> None:
        grid = tk.Frame(self.network_tab, bg="#f3f5f8")
        grid.pack(fill="both", expand=True, pady=8)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)

        # Panel 1: Connections & Mutuals
        p1 = tk.LabelFrame(grid, text="Your Connections (Adjacency List)", bg="#ffffff", padx=10, pady=8)
        p1.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.conn_lb = tk.Listbox(p1, font=("Segoe UI", 9))
        self.conn_lb.pack(fill="both", expand=True)
        b1 = tk.Frame(p1, bg="#ffffff")
        b1.pack(fill="x", pady=(6, 0))
        tk.Button(b1, text="Remove", fg="#dc2626", command=self.remove_selected_conn).pack(side="left", padx=2)
        tk.Button(b1, text="Mutuals", command=self.show_mutuals).pack(side="left", padx=2)

        # Panel 2: Pending Requests (Queue)
        p2 = tk.LabelFrame(grid, text="Pending Requests (FIFO Queue)", bg="#ffffff", padx=10, pady=8)
        p2.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        self.pend_lb = tk.Listbox(p2, font=("Segoe UI", 9))
        self.pend_lb.pack(fill="both", expand=True)
        b2 = tk.Frame(p2, bg="#ffffff")
        b2.pack(fill="x", pady=(6, 0))
        tk.Button(b2, text="Accept", bg="#059669", fg="#ffffff", command=self.accept_selected_req).pack(side="left", padx=2)
        tk.Button(b2, text="Reject", fg="#dc2626", command=self.reject_selected_req).pack(side="left", padx=2)
        tk.Button(b2, text="Cancel Outgoing", command=self.cancel_selected_req).pack(side="left", padx=2)

        # Panel 3: People You May Know (Jaccard)
        p3 = tk.LabelFrame(grid, text="People You May Know (Jaccard Similarity)", bg="#ffffff", padx=10, pady=8)
        p3.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self.sugg_lb = tk.Listbox(p3, font=("Segoe UI", 9))
        self.sugg_lb.pack(fill="both", expand=True)
        tk.Button(p3, text="Send Request to Selected", bg="#1a56db", fg="#ffffff", command=self.connect_suggestion).pack(anchor="w", pady=(6, 0))

        # Panel 4: BFS Shortest Chain & Communities
        p4 = tk.LabelFrame(grid, text="BFS Shortest Chain & Communities", bg="#ffffff", padx=10, pady=8)
        p4.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)
        bfs_row = tk.Frame(p4, bg="#ffffff")
        bfs_row.pack(fill="x")
        tk.Label(bfs_row, text="Target:", bg="#ffffff").pack(side="left")
        self.bfs_target = tk.Entry(bfs_row, width=18)
        self.bfs_target.pack(side="left", padx=6)
        tk.Button(bfs_row, text="Find BFS Path", bg="#1a56db", fg="#ffffff", command=self.find_bfs_path).pack(side="left")
        self.bfs_result_lbl = tk.Label(p4, text="", bg="#ffffff", fg="#111827", wraplength=400, justify="left")
        self.bfs_result_lbl.pack(anchor="w", pady=6)

        tk.Label(p4, text="Communities (Connected Components):", bg="#ffffff", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.comm_lb = tk.Listbox(p4, font=("Segoe UI", 9), height=6)
        self.comm_lb.pack(fill="both", expand=True, pady=(4, 0))

        self._conn_data = []
        self._pend_items = []
        self._sugg_data = []

    def refresh_network(self) -> None:
        assert self.current_user is not None
        self._conn_data = self.engine.get_connections(self.current_user)
        self.conn_lb.delete(0, "end")
        for c in self._conn_data:
            self.conn_lb.insert("end", f"@{c['username']} — {c['name']} ({c['programme']})")

        pending = self.engine.get_pending_requests(self.current_user)
        self._pend_items = []
        self.pend_lb.delete(0, "end")
        for u in pending["incoming"]:
            self._pend_items.append(("in", u["username"]))
            self.pend_lb.insert("end", f"[INCOMING] @{u['username']} ({u['name']})")
        for u in pending["outgoing"]:
            self._pend_items.append(("out", u["username"]))
            self.pend_lb.insert("end", f"[OUTGOING] @{u['username']} ({u['name']})")

        self._sugg_data = self.engine.get_people_you_may_know(self.current_user)
        self.sugg_lb.delete(0, "end")
        for s in self._sugg_data:
            self.sugg_lb.insert("end", f"@{s['username']} ({s['name']}) | Jaccard: {s['jaccard_score']} | {s['mutual_count']} mutuals")

        self.comm_lb.delete(0, "end")
        for i, comm in enumerate(self.engine.get_communities(), 1):
            members = ", ".join(f"@{m['username']}" for m in comm)
            self.comm_lb.insert("end", f"Group {i} ({len(comm)}): {members}")

    def remove_selected_conn(self) -> None:
        sel = self.conn_lb.curselection()
        if not sel:
            return
        assert self.current_user is not None
        target = self._conn_data[sel[0]]["username"]
        _, msg = self.engine.remove_connection(self.current_user, target)
        messagebox.showinfo("Connection", msg)
        self.refresh_network()

    def show_mutuals(self) -> None:
        assert self.current_user is not None
        target = simpledialog.askstring("Mutual Connections", "Enter another student's username:")
        if not target:
            return
        muts = self.engine.get_mutual_connections(self.current_user, target.strip())
        names = ", ".join(f"@{m['username']}" for m in muts) or "None"
        messagebox.showinfo("Mutual Connections", f"Mutuals with @{target}: {names}")

    def accept_selected_req(self) -> None:
        sel = self.pend_lb.curselection()
        if not sel:
            return
        kind, uname = self._pend_items[sel[0]]
        if kind != "in":
            messagebox.showinfo("Pending", "Select an [INCOMING] request to accept.")
            return
        assert self.current_user is not None
        _, msg = self.engine.accept_connection_request(self.current_user, uname)
        messagebox.showinfo("Request", msg)
        self.refresh_all()

    def reject_selected_req(self) -> None:
        sel = self.pend_lb.curselection()
        if not sel:
            return
        kind, uname = self._pend_items[sel[0]]
        if kind != "in":
            return
        assert self.current_user is not None
        _, msg = self.engine.reject_connection_request(self.current_user, uname)
        messagebox.showinfo("Request", msg)
        self.refresh_network()

    def cancel_selected_req(self) -> None:
        sel = self.pend_lb.curselection()
        if not sel:
            return
        kind, uname = self._pend_items[sel[0]]
        if kind != "out":
            messagebox.showinfo("Pending", "Select an [OUTGOING] request to cancel.")
            return
        assert self.current_user is not None
        _, msg = self.engine.cancel_connection_request(self.current_user, uname)
        messagebox.showinfo("Request", msg)
        self.refresh_network()

    def connect_suggestion(self) -> None:
        sel = self.sugg_lb.curselection()
        if not sel:
            return
        assert self.current_user is not None
        target = self._sugg_data[sel[0]]["username"]
        _, msg = self.engine.send_connection_request(self.current_user, target)
        messagebox.showinfo("Connect", msg)
        self.refresh_network()

    def find_bfs_path(self) -> None:
        assert self.current_user is not None
        target = self.bfs_target.get().strip().lower()
        if not target:
            return
        deg, path = self.engine.get_connection_degree_and_path(self.current_user, target)
        if deg is None:
            self.bfs_result_lbl.config(text=f"No connection path found to @{target}.")
        else:
            chain = " -> ".join(f"@{u}" for u in path)
            self.bfs_result_lbl.config(text=f"Degree: {deg} | Shortest Chain: {chain}")

    # ------------------------------------------------------------------
    # TAB 3: PROFILE
    # ------------------------------------------------------------------
    def _build_profile_tab(self) -> None:
        card = tk.Frame(self.profile_tab, bg="#ffffff", bd=1, relief="solid", padx=20, pady=16)
        card.pack(fill="both", expand=True, pady=8)

        self.prof_header = tk.Label(card, text="", font=("Segoe UI", 14, "bold"), bg="#ffffff")
        self.prof_header.pack(anchor="w")
        self.prof_sub = tk.Label(card, text="", font=("Segoe UI", 10), fg="#6b7280", bg="#ffffff")
        self.prof_sub.pack(anchor="w", pady=(2, 14))

        tk.Label(card, text="Bio", bg="#ffffff", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.prof_bio = tk.Entry(card, font=("Segoe UI", 10))
        self.prof_bio.pack(fill="x", pady=(2, 10))

        tk.Label(card, text="Skills (comma-separated)", bg="#ffffff", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.prof_skills = tk.Entry(card, font=("Segoe UI", 10))
        self.prof_skills.pack(fill="x", pady=(2, 14))

        tk.Button(card, text="Save Profile Changes", bg="#1a56db", fg="#ffffff", font=("Segoe UI", 10, "bold"), command=self.save_profile).pack(anchor="w")

    def refresh_profile(self) -> None:
        assert self.current_user is not None
        p = self.engine.get_profile(self.current_user)
        if not p:
            return
        self.prof_header.config(text=f"{p['name']} (@{p['username']})")
        self.prof_sub.config(text=f"{p['programme']} · Year {p['year']} · {p['connection_count']} connections · {p['post_count']} posts")
        self.prof_bio.delete(0, "end")
        self.prof_bio.insert(0, p.get("bio", ""))
        self.prof_skills.delete(0, "end")
        self.prof_skills.insert(0, ", ".join(p.get("skills", [])))

    def save_profile(self) -> None:
        assert self.current_user is not None
        bio = self.prof_bio.get().strip()
        skills = [s.strip() for s in self.prof_skills.get().split(",") if s.strip()]
        ok, msg = self.engine.update_profile(self.current_user, bio=bio, skills=skills)
        messagebox.showinfo("Profile", msg)
        if ok:
            self.refresh_profile()


if __name__ == "__main__":
    app = ChanakyaConnectGUI()
    app.mainloop()
