#!/usr/bin/env python3
"""
Database optimization script - Add indexes for better performance
"""

import sqlite3
import os
from pathlib import Path

def optimize_database():
    """Add indexes to improve query performance"""
    
    # Get database path
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    db_path = os.path.join(data_dir, 'enhanced_fake_news.db')
    
    if not os.path.exists(db_path):
        print("Database not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔧 Optimizing database performance...")
        
        # Add indexes for common queries
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_events_state ON events(state)",
            "CREATE INDEX IF NOT EXISTS idx_events_verdict ON events(fake_news_verdict)",
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_state_verdict ON events(state, fake_news_verdict)",
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp_desc ON events(timestamp DESC)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
            print(f"✅ Created index: {index_sql.split('idx_')[1].split(' ON')[0]}")
        
        # Analyze tables for better query planning
        cursor.execute("ANALYZE")
        print("✅ Analyzed tables for query optimization")
        
        # Vacuum to optimize storage
        cursor.execute("VACUUM")
        print("✅ Vacuumed database for storage optimization")
        
        conn.commit()
        print("🚀 Database optimization complete!")
        
    except Exception as e:
        print(f"❌ Error optimizing database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    optimize_database()