import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/enhanced_fake_news.db')
c = conn.cursor()
c.execute("SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM events")
min_ts, max_ts, cnt = c.fetchone()
print(f"Total Events: {cnt}")
print(f"Min Timestamp: {min_ts}")
print(f"Max Timestamp: {max_ts}")

c.execute("SELECT COUNT(*) FROM events WHERE timestamp > datetime('now', '-24 hours')")
last_24h_cnt = c.fetchone()[0]
print(f"Events in last 24h: {last_24h_cnt}")

# Check breakdown of classifications
c.execute("SELECT fake_news_verdict, COUNT(*) FROM events GROUP BY fake_news_verdict")
print("Verdict breakdown:", c.fetchall())

conn.close()
