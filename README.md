# ChanakyaConnect — Student Networking App (DSA Mini Project)

A networking platform for **Chanakya University, Bangalore** students (III Semester B.Tech., Data Structures and Algorithms) where students share projects, technical ideas, and connect with classmates.

## Architecture

The core DSA engine (`core/`) is completely decoupled from the user interfaces (`gui/`, `web/`, and `cli/`). All three interfaces invoke the exact same methods on `ChanakyaConnectEngine`.

```
chanakya_connect/
├── core/
│   ├── models.py           # User, Post, CommentNode (Tree), Notification
│   ├── data_structures.py  # HashTable, Trie, Queue, Stack, MaxHeap, SocialGraph
│   └── engine.py           # ChanakyaConnectEngine (in-memory DSA facade)
├── storage/
│   └── json_store.py       # Atomic JSON persistence (raw state only)
├── gui/
│   └── main.py             # Standalone Desktop GUI App (built-in Tkinter)
├── web/
│   ├── app.py              # FastAPI REST API + HTML frontend server
│   └── templates/
│       └── index.html      # Responsive Single-Page Web UI
├── cli/
│   └── main.py             # Console-based menu application
├── tests/
│   └── test_engine.py      # Unit tests for all DSA structures & persistence
├── seed_data.py            # Populates sample Chanakya University students & posts
└── DESIGN_REPORT.md        # Architecture & DSA complexity report
```

## Quick Start

1. **Seed demo data** (already pre-seeded, re-run anytime to reset):
   ```bash
   python seed_data.py
   ```
   Demo accounts (password: `pass1234`): `shrish`, `ananya`, `rohan`, `meera`, `vikram`, `kavya`.
2. **Run the Standalone Desktop App (Tkinter — zero extra installs)**:
   ```bash
   python gui/main.py
   ```
3. **Run the Console CLI (zero extra installs)**:
   ```bash
   python cli/main.py
   ```
4. **Run the Web App (FastAPI + UI)**:
   ```bash
   python -m pip install -r requirements.txt
   python -m uvicorn web.app:app --reload
   ```
   Open `http://127.0.0.1:8000` in your browser.
5. **Run Unit Tests**:
   ```bash
   python -m unittest discover -s tests -v
   ```
