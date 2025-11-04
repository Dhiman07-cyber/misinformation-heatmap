#!/usr/bin/env python3
"""
Test script for Enhanced Real-Time Misinformation Heatmap
"""

import sqlite3
import json
from datetime import datetime

def test_database():
    """Test if the database is working and has data"""
    try:
        conn = sqlite3.connect('enhanced_heatmap.db')
        cursor = conn.cursor()
        
        # Check events table
        cursor.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        
        # Check state content table
        cursor.execute("SELECT COUNT(*) FROM state_content WHERE total_events > 0")
        active_states = cursor.fetchone()[0]
        
        # Get sample events
        cursor.execute("SELECT title, state, misinformation_score, source FROM events LIMIT 5")
        sample_events = cursor.fetchall()
        
        conn.close()
        
        print("🔍 Enhanced System Database Test Results")
        print("=" * 50)
        print(f"📊 Total Events Processed: {event_count}")
        print(f"🗺️  Active States: {active_states}")
        print(f"📈 Sample Events:")
        
        for i, (title, state, score, source) in enumerate(sample_events, 1):
            risk_level = "🔴 High" if score > 0.7 else "🟡 Medium" if score > 0.4 else "🟢 Low"
            print(f"   {i}. {title[:60]}...")
            print(f"      State: {state} | Risk: {risk_level} ({score:.2f}) | Source: {source}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_rss_ingestion():
    """Test RSS ingestion functionality"""
    try:
        conn = sqlite3.connect('enhanced_heatmap.db')
        cursor = conn.cursor()
        
        # Check recent events (last hour)
        cursor.execute("""
            SELECT COUNT(*) FROM events 
            WHERE timestamp >= datetime('now', '-1 hour')
        """)
        recent_events = cursor.fetchone()[0]
        
        # Check source diversity
        cursor.execute("SELECT DISTINCT source FROM events")
        sources = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        print("\n📡 RSS Ingestion Test Results")
        print("=" * 50)
        print(f"🕐 Recent Events (last hour): {recent_events}")
        print(f"📰 Active Sources: {len(sources)}")
        print("   Sources:", ", ".join(sources))
        
        return recent_events > 0
        
    except Exception as e:
        print(f"❌ RSS ingestion test failed: {e}")
        return False

def test_ai_analysis():
    """Test AI analysis functionality"""
    try:
        conn = sqlite3.connect('enhanced_heatmap.db')
        cursor = conn.cursor()
        
        # Check analysis completeness
        cursor.execute("""
            SELECT 
                AVG(misinformation_score) as avg_score,
                COUNT(*) as total,
                SUM(CASE WHEN misinformation_score > 0.7 THEN 1 ELSE 0 END) as high_risk
            FROM events
        """)
        
        avg_score, total, high_risk = cursor.fetchone()
        
        # Check sentiment analysis
        cursor.execute("SELECT DISTINCT sentiment FROM events WHERE sentiment IS NOT NULL")
        sentiments = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        print("\n🧠 AI Analysis Test Results")
        print("=" * 50)
        print(f"📊 Average Misinformation Score: {avg_score:.3f}")
        print(f"🔴 High Risk Events: {high_risk}/{total} ({(high_risk/total*100):.1f}%)")
        print(f"😊 Sentiment Analysis: {', '.join(sentiments) if sentiments else 'Fallback mode'}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI analysis test failed: {e}")
        return False

def test_state_content():
    """Test state-specific content functionality"""
    try:
        conn = sqlite3.connect('enhanced_heatmap.db')
        cursor = conn.cursor()
        
        # Get top states by activity
        cursor.execute("""
            SELECT state, total_events, high_risk_events, avg_misinformation_score
            FROM state_content 
            WHERE total_events > 0
            ORDER BY total_events DESC
            LIMIT 5
        """)
        
        top_states = cursor.fetchall()
        
        conn.close()
        
        print("\n🗺️  State Content Test Results")
        print("=" * 50)
        print("📍 Top Active States:")
        
        for state, total, high_risk, avg_score in top_states:
            risk_level = "🔴 High" if avg_score > 0.7 else "🟡 Medium" if avg_score > 0.4 else "🟢 Low"
            print(f"   • {state}: {total} events ({high_risk} high-risk) - {risk_level}")
        
        return len(top_states) > 0
        
    except Exception as e:
        print(f"❌ State content test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Enhanced Real-Time Misinformation Heatmap - System Test")
    print("=" * 70)
    
    tests = [
        ("Database Functionality", test_database),
        ("RSS Ingestion", test_rss_ingestion),
        ("AI Analysis", test_ai_analysis),
        ("State Content", test_state_content)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("📋 Test Summary")
    print("=" * 70)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status} {test_name}")
    
    overall = "✅ ALL TESTS PASSED" if all(results) else "⚠️  SOME TESTS FAILED"
    print(f"\n🎯 Overall Status: {overall}")
    
    if all(results):
        print("\n🎉 Enhanced system is working perfectly!")
        print("🌐 Access the dashboard at: http://localhost:8080")
        print("🗺️  View the heatmap at: http://localhost:8080/heatmap")
    else:
        print("\n🔧 Some components need attention. Check the logs above.")

if __name__ == "__main__":
    main()