import sys
sys.path.insert(0, 'backend')
import asyncio

async def test():
    from watson_client import cloud_ingestion_manager, GDELTClient
    print("OK Import - No IBM Watson SDK required.")
    print(f"   Type: {type(cloud_ingestion_manager).__name__}")
    
    ok = await cloud_ingestion_manager.initialize()
    print(f"   Initialize: {ok}")
    
    events = await cloud_ingestion_manager.ingest_and_enhance_content([])
    print(f"   GDELT Events fetched: {len(events)}")
    
    if events:
        e0 = events[0]
        print(f"   Sample title: {e0.get('title', '')[:80]}")
        print(f"   Cloud source: {e0.get('cloud_source', 'N/A')}")
        
        print("   State extraction test (first 5 events):")
        from realtime_processor import extract_location
        for e in events[:5]:
            st = extract_location(e.get('title', ''))
            label = st if st else 'National'
            print(f"     [{label}] {e.get('title', '')[:60]}")
    else:
        print("   No GDELT events (may be cached or API unreachable). Local RSS pipeline unaffected.")

asyncio.run(test())
