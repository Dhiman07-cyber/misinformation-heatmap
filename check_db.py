import sqlite3
from datetime import datetime

conn = sqlite3.connect("data/enhanced_fake_news.db")
conn.row_factory = sqlite3.Row

print("Current UTC according to SQLite:")
row = conn.execute("SELECT datetime('now') as ut, datetime('now', '-24 hours') as ut24, datetime('now', '-7 days') as ut7d").fetchone()
print(f"  datetime('now'): {row['ut']}")
print(f"  datetime('now', '-24 hours'): {row['ut24']}")
print(f"  datetime('now', '-7 days'): {row['ut7d']}")

print("\nLast 5 events in database:")
rows = conn.execute("SELECT timestamp FROM events ORDER BY timestamp DESC LIMIT 5").fetchall()
for r in rows:
    print(f"  timestamp: {r['timestamp']}")

print("\nLet's test the 24 hour filter:")
row = conn.execute("SELECT COUNT(*) as cnt FROM events WHERE timestamp > datetime('now', '-24 hours')").fetchone()
print(f"  Count with > -24 hours: {row['cnt']}")

row = conn.execute("SELECT COUNT(*) as cnt FROM events").fetchone()
print(f"  Total count: {row['cnt']}")

conn.close()
