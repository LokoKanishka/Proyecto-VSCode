#!/usr/bin/env python3
"""
Test script for Lucy Web consciousness integration
Simulates consciousness updates to test real-time visualization
"""

import json
import time
from datetime import datetime

# Test consciousness states
STATES = [
    {
        "state": "WAITING",
        "entropy": 0.1,
        "activity": 0.0,
        "last_thought": "System initialized, waiting for input",
        "timestamp": datetime.now().isoformat()
    },
    {
        "state": "PROCESSING",
        "entropy": 0.6,
        "activity": 0.8,
        "last_thought": "Analyzing user query: 'What is the meaning of life?'",
        "timestamp": datetime.now().isoformat()
    },
    {
        "state": "COHERENCE",
        "entropy": 0.2,
        "activity": 0.9,
        "last_thought": "Generated response using philosophical reasoning",
        "timestamp": datetime.now().isoformat()
    },
    {
        "state": "WAITING",
        "entropy": 0.1,
        "activity": 0.2,
        "last_thought": "Response delivered, awaiting next query",
        "timestamp": datetime.now().isoformat()
    },
]

def update_consciousness(state_data):
    """Write consciousness state to JSON file"""
    with open('lucy_consciousness.json', 'w', encoding='utf-8') as f:
        json.dump(state_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Updated consciousness: {state_data['state']} - {state_data['last_thought']}")

def main():
    print("🧠 Lucy Consciousness Test Simulator")
    print("="*60)
    print("This script simulates consciousness updates to test web UI")
    print("Make sure lucy_web is running and browser is open")
    print("="*60)
    
    input("\nPress Enter to start simulation...")
    
    for i, state in enumerate(STATES, 1):
        print(f"\n[{i}/{len(STATES)}] Updating state...")
        state["timestamp"] = datetime.now().isoformat()
        update_consciousness(state)
        
        if i < len(STATES):
            print("   Waiting 3 seconds for next update...")
            time.sleep(3)
    
    print("\n✅ Test completed!")
    print("\nCheck browser - you should see:")
    print("  1. State icon changes (💤 → ⚙️ → 💠 → 💤)")
    print("  2. Metrics bars animate (entropy, activity)")
    print("  3. Log entries appear with timestamps")
    print("  4. Border color changes (cyan variations)")

if __name__ == '__main__':
    main()
