"""
Console-based Menu Application for ChanakyaConnect.

Uses the exact same `ChanakyaConnectEngine` as the FastAPI web frontend,
demonstrating clean separation of the core DSA engine from the UI layer.
Run with:
    python3 cli/main.py
"""

import os
import sys
from getpass import getpass
from typing import Optional

# Ensure project root is on sys.path when invoked directly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.engine import ChanakyaConnectEngine


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_comment_tree(comments: list, indent: int = 0) -> None:
    for c in comments:
        pad = "  " * indent
        print(f"{pad}↳ [{c['comment_id']}] @{c['author']}: {c['text']}")
        if c.get("replies"):
            print_comment_tree(c["replies"], indent + 1)


def print_post(p: dict) -> None:
    print(f"\n[{p['post_id']}] @{p['author']} ({p.get('author_name', '')} | {p.get('author_programme', '')})")
    print(f"  {p['content']}")
    if p.get("image_url"):
        print(f"  [Image: {p['image_url']}]")
    print(f"  Likes: {p['like_count']} | Comments: {p['comment_count']}")
    if p.get("comments"):
        print_comment_tree(p["comments"], indent=1)


def main() -> None:
    data_path = os.path.join(PROJECT_ROOT, "data", "network_data.json")
    engine = ChanakyaConnectEngine(storage_path=data_path)
    current_user: Optional[str] = None
    current_token: Optional[str] = None

    while True:
        if current_user is None:
            print_header("ChanakyaConnect — Student Network (CLI)")
            stats = engine.get_network_stats()
            print(f"Network: {stats['total_users']} students | {stats['total_connections']} connections | {stats['total_posts']} posts")
            print("1. Sign Up")
            print("2. Log In")
            print("0. Exit")
            choice = input("Choose an option: ").strip()

            if choice == "1":
                username = input("Username: ").strip()
                password = getpass("Password (min 4 chars): ")
                name = input("Full Name: ").strip()
                programme = input("Programme (e.g., B.Tech CSAI): ").strip()
                year_str = input("Year (1-4): ").strip()
                bio = input("Short Bio: ").strip()
                skills_raw = input("Skills (comma-separated): ").strip()
                skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
                try:
                    year = int(year_str)
                except ValueError:
                    print("Invalid year.")
                    continue
                ok, msg = engine.signup(username, password, name, programme, year, bio, skills)
                print(msg)

            elif choice == "2":
                username = input("Username: ").strip()
                password = getpass("Password: ")
                ok, msg, token = engine.login(username, password)
                print(msg)
                if ok and token:
                    current_user = username.strip().lower()
                    current_token = token
                    engine.push_navigation(current_user, "Home")

            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid choice.")
        else:
            print_header(f"ChanakyaConnect — Logged in as @{current_user}")
            print("1. View Home Feed (MaxHeap)")
            print("2. View Trending Posts (MaxHeap)")
            print("3. Create Post")
            print("4. Delete / Undo Delete Post (Stack)")
            print("5. Like or Comment on a Post (Comment Tree)")
            print("6. Search Users by Prefix (Trie)")
            print("7. Connections, Pending Requests & Mutuals")
            print("8. People You May Know (Jaccard Similarity)")
            print("9. Degree of Connection & Shortest Chain (BFS)")
            print("10. View Communities (Connected Components)")
            print("11. Notifications (Queue)")
            print("12. View / Edit My Profile")
            print("13. Back (Navigation Stack)")
            print("0. Log Out")
            choice = input("Choose an option: ").strip()

            if choice == "1":
                engine.push_navigation(current_user, "Home Feed")
                feed = engine.get_home_feed(current_user)
                if not feed:
                    print("Your feed is empty. Connect with classmates to see their posts!")
                for p in feed:
                    print_post(p)

            elif choice == "2":
                engine.push_navigation(current_user, "Trending")
                trending = engine.get_trending_posts(current_user)
                if not trending:
                    print("No trending posts from connections yet.")
                for p in trending:
                    print(f"[Score: {p.get('trending_score')}]", end="")
                    print_post(p)

            elif choice == "3":
                content = input("Write about your project or technical idea: ").strip()
                img = input("Optional image URL (press Enter to skip): ").strip() or None
                ok, msg, _ = engine.create_post(current_user, content, img)
                print(msg)

            elif choice == "4":
                sub = input("(d)elete a post or (u)ndo last delete? ").strip().lower()
                if sub == "d":
                    my_posts = engine.get_user_posts(current_user)
                    for p in my_posts:
                        print_post(p)
                    pid = input("Enter Post ID to delete: ").strip()
                    _, msg = engine.delete_post(current_user, pid)
                    print(msg)
                elif sub == "u":
                    _, msg, _ = engine.undo_delete_post(current_user)
                    print(msg)

            elif choice == "5":
                pid = input("Enter Post ID: ").strip()
                act = input("(l)ike/unlike or (c)omment? ").strip().lower()
                if act == "l":
                    _, msg, _ = engine.toggle_like(current_user, pid)
                    print(msg)
                elif act == "c":
                    text = input("Comment text: ").strip()
                    parent = input("Reply to Comment ID (Enter for top-level): ").strip() or None
                    _, msg, _ = engine.add_comment(current_user, pid, text, parent)
                    print(msg)

            elif choice == "6":
                prefix = input("Enter name or username prefix: ").strip()
                matches = engine.search_users(prefix)
                if not matches:
                    print("No users found.")
                for u in matches:
                    print(f"  @{u['username']} — {u['name']} ({u['programme']}, Year {u['year']})")

            elif choice == "7":
                print("\n--- Your Connections ---")
                for c in engine.get_connections(current_user):
                    print(f"  @{c['username']} ({c['name']})")
                pending = engine.get_pending_requests(current_user)
                print("\n--- Incoming Requests ---")
                for req in pending["incoming"]:
                    print(f"  @{req['username']} ({req['name']})")
                print("\n--- Outgoing Requests ---")
                for req in pending["outgoing"]:
                    print(f"  @{req['username']} ({req['name']})")

                print("\nActions: (s)end, (a)ccept, (r)eject, (c)ancel, (x)remove, (m)utuals, Enter=back")
                act = input("Action: ").strip().lower()
                if act in {"s", "a", "r", "c", "x", "m"}:
                    target = input("Target username: ").strip()
                    if act == "s":
                        print(engine.send_connection_request(current_user, target)[1])
                    elif act == "a":
                        print(engine.accept_connection_request(current_user, target)[1])
                    elif act == "r":
                        print(engine.reject_connection_request(current_user, target)[1])
                    elif act == "c":
                        print(engine.cancel_connection_request(current_user, target)[1])
                    elif act == "x":
                        print(engine.remove_connection(current_user, target)[1])
                    elif act == "m":
                        muts = engine.get_mutual_connections(current_user, target)
                        print(f"Mutual connections ({len(muts)}):", ", ".join(f"@{m['username']}" for m in muts) or "None")

            elif choice == "8":
                recs = engine.get_people_you_may_know(current_user)
                if not recs:
                    print("No suggestions yet (connect with someone first!).")
                for r in recs:
                    print(f"  @{r['username']} — {r['name']} | Jaccard: {r['jaccard_score']} | Mutuals: {r['mutual_count']}")

            elif choice == "9":
                target = input("Enter target username: ").strip()
                deg, path = engine.get_connection_degree_and_path(current_user, target)
                if deg is None:
                    print(f"No connection path between @{current_user} and @{target}.")
                else:
                    print(f"Degree: {deg} | Shortest Chain: {' -> '.join('@' + u for u in path)}")

            elif choice == "10":
                comms = engine.get_communities()
                for idx, comm in enumerate(comms, 1):
                    members = ", ".join(f"@{m['username']}" for m in comm)
                    print(f"  Community {idx} ({len(comm)} students): {members}")

            elif choice == "11":
                notifs = engine.get_notifications(current_user)
                if not notifs:
                    print("No notifications.")
                for n in notifs:
                    status = "READ" if n["is_read"] else "NEW"
                    print(f"  [{status}] {n['message']}")
                engine.mark_all_notifications_read(current_user)

            elif choice == "12":
                prof = engine.get_profile(current_user)
                if prof:
                    print(f"Name: {prof['name']} | {prof['programme']} Year {prof['year']}")
                    print(f"Bio: {prof['bio']}")
                    print(f"Skills: {', '.join(prof['skills'])}")
                if input("Edit profile? (y/n): ").strip().lower() == "y":
                    bio = input("New bio (Enter to keep): ").strip() or None
                    skills_raw = input("New skills comma-separated (Enter to keep): ").strip()
                    skills = [s.strip() for s in skills_raw.split(",") if s.strip()] if skills_raw else None
                    print(engine.update_profile(current_user, bio=bio, skills=skills)[1])

            elif choice == "13":
                prev = engine.pop_navigation(current_user)
                print(f"Popped navigation stack: {prev or 'Stack empty'}")

            elif choice == "0":
                if current_token:
                    engine.logout(current_token)
                current_user = None
                current_token = None
                print("Logged out.")


if __name__ == "__main__":
    main()
