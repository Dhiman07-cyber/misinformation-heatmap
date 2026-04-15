import sys
import psutil
import os
import time
import threading

def monitor_memory():
    process = psutil.Process(os.getpid())
    while True:
        mb = process.memory_info().rss / 1024 / 1024
        print(f"Memory: {mb:.2f} MB")
        if mb > 1000:
            print("MEMORY EXCEEDS 1GB! ABORTING!")
            os._exit(1)
        time.sleep(2)

threading.Thread(target=monitor_memory, daemon=True).start()

import asyncio
# Add parent dir to path if needed, but we are running in the root.
sys.path.insert(0, os.path.abspath('backend'))

from massive_data_ingestion import fetch_massive_rss_data, process_event_with_fake_news_detection

async def test():
    print("Starting fetch...")
    events = await fetch_massive_rss_data()
    print("Fetched", len(events))
    
    tasks = []
    for event in events[:50]: 
        tasks.append(process_event_with_fake_news_detection(event))
        
    print("Starting process...")
    await asyncio.gather(*tasks, return_exceptions=True)
    print("Processed batch")

asyncio.run(test())
