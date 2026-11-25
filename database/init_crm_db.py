"""
database/init_crm_db.py — SQLite schema + 100 synthetic CRM ticket records (seed=42)
"""
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "crm_tickets.db"

CUSTOMER_NAMES = [
    "Alice Johnson", "Bob Martinez", "Carol Smith", "David Lee", "Eva Brown",
    "Frank Wilson", "Grace Taylor", "Henry Anderson", "Isla Thomas", "Jack White",
    "Karen Harris", "Liam Jackson", "Mia Robinson", "Noah Walker", "Olivia Hall",
    "Paul Allen", "Quinn Young", "Rachel King", "Sam Wright", "Tina Scott",
]

ISSUE_TYPES = ["Billing", "Technical", "Shipping", "Refund", "Account", "Password Reset"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
TEAMS = ["Billing Team", "Tech Support", "Logistics", "Account Services"]
STATUSES = ["Open", "In Progress", "Resolved", "Escalated"]

PRIORITY_WEIGHTS = [0.3, 0.4, 0.2, 0.1]
STATUS_WEIGHTS = [0.2, 0.3, 0.4, 0.1]

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id          TEXT PRIMARY KEY,
    customer_name      TEXT NOT NULL,
    issue_type         TEXT NOT NULL,
    priority           TEXT NOT NULL,
    resolution_time_hrs REAL,
    csat_score         INTEGER,
    assigned_team      TEXT NOT NULL,
    status             TEXT NOT NULL,
    created_at         TEXT NOT NULL
);
"""


def team_for_issue(issue: str) -> str:
    return {
        "Billing": "Billing Team",
        "Technical": "Tech Support",
        "Shipping": "Logistics",
        "Refund": "Billing Team",
        "Account": "Account Services",
        "Password Reset": "Account Services",
    }.get(issue, "Tech Support")


def generate_records(n: int = 100) -> list[dict]:
    rng = random.Random(42)
    base_date = datetime(2024, 1, 1)
    records = []
    for i in range(1, n + 1):
        issue = rng.choice(ISSUE_TYPES)
        status = rng.choices(STATUSES, STATUS_WEIGHTS)[0]
        priority = rng.choices(PRIORITIES, PRIORITY_WEIGHTS)[0]
        resolution_time = round(rng.uniform(0.5, 120.0), 2) if status == "Resolved" else None
        csat = rng.randint(1, 5) if status == "Resolved" else None
        created_at = base_date + timedelta(days=rng.randint(0, 364), hours=rng.randint(0, 23))
        records.append({
            "ticket_id": f"T{i:04d}",
            "customer_name": CUSTOMER_NAMES[(i - 1) % len(CUSTOMER_NAMES)],
            "issue_type": issue,
            "priority": priority,
            "resolution_time_hrs": resolution_time,
            "csat_score": csat,
            "assigned_team": team_for_issue(issue),
            "status": status,
            "created_at": created_at.isoformat(),
        })
    return records


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(CREATE_TABLE)
    cur.execute("DELETE FROM tickets")  # idempotent
    records = generate_records(100)
    cur.executemany(
        """INSERT INTO tickets
           (ticket_id, customer_name, issue_type, priority,
            resolution_time_hrs, csat_score, assigned_team, status, created_at)
           VALUES (:ticket_id,:customer_name,:issue_type,:priority,
                   :resolution_time_hrs,:csat_score,:assigned_team,:status,:created_at)""",
        records,
    )
    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    conn.close()
    print(f"✅ Initialized CRM DB at {DB_PATH}")
    print(f"   {count} ticket records inserted.")


if __name__ == "__main__":
    init_db()
