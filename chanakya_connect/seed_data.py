"""
Seed script to populate ChanakyaConnect with sample Chanakya University students,
connections, pending requests, project posts, likes, and nested comments.
Run with:
    python3 seed_data.py
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.engine import ChanakyaConnectEngine


def seed(storage_path: str) -> None:
    if os.path.exists(storage_path):
        os.remove(storage_path)

    engine = ChanakyaConnectEngine(storage_path=storage_path)

    students = [
        ("shrish", "pass1234", "Shrish Hegde", "B.Tech CSAI", 2, "Building drone flight controllers & AI systems.", ["Python", "C", "DSA", "RISC-V", "ESP32"]),
        ("ananya", "pass1234", "Ananya Rao", "B.Tech CSAI", 2, "ML & computer vision enthusiast.", ["Python", "PyTorch", "OpenCV", "DSA"]),
        ("rohan", "pass1234", "Rohan Kulkarni", "B.Tech EECS", 2, "Embedded systems & robotics builder.", ["C++", "ROS2", "Arduino", "PCB Design"]),
        ("meera", "pass1234", "Meera Nair", "B.Tech EVE", 3, "VLSI & FPGA verification student.", ["Verilog", "SystemVerilog", "Python", "Digital Logic"]),
        ("vikram", "pass1234", "Vikramaditya Joshi", "B.Tech CSAI", 3, "Backend systems & distributed databases.", ["Go", "Python", "FastAPI", "PostgreSQL"]),
        ("kavya", "pass1234", "Kavya Sharma", "B.Tech EECS", 1, "Exploring competitive programming and web dev.", ["Python", "JavaScript", "HTML/CSS"]),
    ]

    for u, pw, name, prog, yr, bio, skills in students:
        engine.signup(u, pw, name, prog, yr, bio, skills)

    # Create connections (undirected edges)
    pairs = [
        ("shrish", "ananya"),
        ("shrish", "rohan"),
        ("ananya", "vikram"),
        ("rohan", "meera"),
        ("vikram", "meera"),
    ]
    for a, b in pairs:
        engine.send_connection_request(a, b)
        engine.accept_connection_request(b, a)

    # Pending request
    engine.send_connection_request("kavya", "shrish")

    # Posts
    _, _, p1 = engine.create_post("ananya", "Just trained a YOLOv8 model for campus traffic analysis! Happy to share dataset notes.")
    _, _, p2 = engine.create_post("rohan", "Built a PID-stabilized ESP32 quadcopter frame in the Robotics Lab today.")
    _, _, p3 = engine.create_post("vikram", "Benchmarked B+Trees vs LSM-Trees for our Systems seminar. Notes coming soon!")
    _, _, p4 = engine.create_post("shrish", "Implemented custom Trie + MaxHeap + BFS graph engine in Python for ChanakyaConnect!")

    if p1:
        engine.toggle_like("shrish", p1["post_id"])
        engine.toggle_like("vikram", p1["post_id"])
        _, _, c1 = engine.add_comment("shrish", p1["post_id"], "Awesome work Ananya! How many epochs did you train?")
        if c1:
            engine.add_comment("ananya", p1["post_id"], "Thanks Shrish! 50 epochs on Colab.", parent_comment_id=c1["comment_id"])

    if p2:
        engine.toggle_like("shrish", p2["post_id"])
        engine.add_comment("meera", p2["post_id"], "Clean wiring! Let's test telemetry next week.")


    # Skill Endorsements
    engine.endorse_skill("ananya", "shrish", "Python")
    engine.endorse_skill("rohan", "shrish", "DSA")
    engine.endorse_skill("shrish", "ananya", "PyTorch")

    # Jobs & Internships
    engine.create_job(
        "ananya",
        "AI / Computer Vision Research Intern",
        "Chanakya AI & Robotics Lab",
        "Bangalore (On-Campus)",
        "Research",
        "Work on real-time drone obstacle detection using PyTorch and OpenCV.",
        ["Python", "PyTorch", "OpenCV", "DSA"],
    )
    engine.create_job(
        "rohan",
        "Embedded Drone Firmware Intern",
        "AeroCU Student Team",
        "Bangalore",
        "Internship",
        "Develop flight telemetry & PID control loops on ESP32 and RISC-V.",
        ["C", "ESP32", "RISC-V", "Python"],
    )
    engine.create_job(
        "vikram",
        "Backend FastAPI Intern",
        "Bengaluru FinTech Studio",
        "Bangalore (Hybrid)",
        "Internship",
        "Build high-throughput REST APIs with Python, FastAPI, and PostgreSQL.",
        ["Python", "FastAPI", "PostgreSQL", "DSA"],
    )

    # Direct Messages
    engine.send_message("ananya", "shrish", "Hey Shrish! Want to collaborate on the drone CV pipeline?")
    engine.send_message("shrish", "ananya", "Definitely! Let's sync after the DSA lecture.")

    print(f"Seeded {len(students)} students at {storage_path}")


if __name__ == "__main__":
    seed(os.path.join(PROJECT_ROOT, "data", "network_data.json"))
