#!/usr/bin/env python3
"""Quick script to check what capabilities are available in the API."""
import asyncio
import json
import sys

async def main():
    """Check API capabilities."""
    # You'll need to run this from Home Assistant or provide credentials
    print("This script should be run from Home Assistant to check current API data.")
    print("Alternatively, check Home Assistant logs for capability information.")
    print("")
    print("To see what capabilities are currently available:")
    print("1. Go to Home Assistant")
    print("2. Check Developer Tools > States")
    print("3. Look for sensor.tibber_data_homevolt_teg06_* sensors")
    print("4. Or check the logs for 'Creating sensors for X known capabilities'")

if __name__ == "__main__":
    asyncio.run(main())
