# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# CELL ********************

# Welcome to your new notebook
# Type here in the cell editor to add code!
%pip install websockets azure-eventhub

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# ========================================
# 🔧 CONFIGURATION - UPDATE AFTER DEPLOYMENT
# ========================================
# 
# ⚠️ REQUIRED: Update these values after deploying the Eventstream
#
# 1. FABRIC_ENTITY_NAME: Event Hub name from Eventstream custom endpoint
#    - Navigate to: Fabric Portal → Workspace → maritimeES Eventstream → LiveAISSource
#    - Go to: SAS Key Authentication → Live view
#    - Copy the Event Hub name (e.g., "esehchxkj881x95xl1hgnk_eh")
#
# 2. FABRIC_CONNECTION_STR: Connection string from same location
#    - Copy the full connection string starting with "Endpoint=sb://..."
#

# Event Hub Configuration (from Eventstream custom endpoint)
FABRIC_ENTITY_NAME = "esehchxkj881x95xl1hgnk_eh"  # ← UPDATE THIS with your Event Hub name

# Security Configuration
# Option 1 (Production): Use Azure Key Vault
KEY_VAULT_NAME = "https://kv-maritime-demo.vault.azure.net/"  # ← UPDATE THIS with your Key Vault URL
FABRIC_CONNECTION_STR = mssparkutils.credentials.getSecret(KEY_VAULT_NAME, "FabricConnectionString")

# Option 2 (Local Testing): Use direct value (NEVER commit to Git!)
# FABRIC_CONNECTION_STR = "Endpoint=sb://xxxxx.servicebus.windows.net/;SharedAccessKeyName=...;SharedAccessKey=...;EntityPath=esehchxkj881x95xl1hgnk_eh"

# ========================================

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import time
import json
import numpy as np
from datetime import datetime, timezone
from azure.eventhub import EventHubProducerClient, EventData

def generate_sync_path(total_points=100):

    # FORMAT: (Latitude, Longitude) (INVERSE from SIMULATION 1)
    waypoints = [
        # 5. OCEAN EXIT PHASE: Heading south down the Gulf of Oman toward open water
        (24.50, 59.50),  # NEW EXIT: Heading directly into the Indian Ocean
        (25.30, 58.50), # Safe deep-water passage 
        (25.80, 57.05), # Turning South-East into the main exit corridor


        # 2. RED ZONE (Iran High Risk Zone - Strait of Hormuz Centered Channel)
        # Adjusted to drop south/center into the deep water lane apex, clearing the land safely
        (26.30, 56.75), # EXITING CENTER: Clearing the eastern center-boundary of the Red Zone
        (26.45, 56.40), # CORE CENTER (Apex): Peak of the turn right through the middle of the Strait
        (26.35, 55.95), # ENTERING CENTER: Moving smoothly into the heart of the Red Zone


        # 3. YELLOW ZONE (Western Transit Corridor Centered Channel)
        # Re-centered to cut right through the middle instead of clipping the north edge
        (26.10, 55.50), # EXITING CENTER: Heading east out of the Yellow Zone's core
        (26.15, 55.10), # CORE CENTER: Cutting straight through the middle of Yellow Zone
        (26.20, 54.60), # ENTERING CENTER: West entry point of Yellow Zone


        # 5. TRANSIT TO YELLOW CORRIDOR: Straight line passing north of Qatar/UAE toward the center entrance
        (26.25, 53.80), # Mid-Gulf Transit 2 (Aligning with the center axis of Yellow Zone)
        (26.10, 52.80), # Mid-Gulf Transit 1

        # 5. ARRIVAL: Doha Port, Qatar
        (25.30, 51.55) # Doha Outbound

    ]


    lats, lons = [], []
    segments = len(waypoints) - 1
    pts_per_seg = total_points // segments
    
    for i in range(segments):
        lats.extend(np.linspace(waypoints[i][0], waypoints[i+1][0], pts_per_seg))
        lons.extend(np.linspace(waypoints[i][1], waypoints[i+1][1], pts_per_seg))
    
    return lats, lons

def stream_simulation():
    producer = EventHubProducerClient.from_connection_string(
        conn_str=FABRIC_CONNECTION_STR, 
        eventhub_name=FABRIC_ENTITY_NAME
    )
    
    ship_name = "EAST_SIMULATED_TANKER_02"
    
    while True:
        lats, lons = generate_sync_path(100)
        print(f"\n🚢 Voyage Start (Synced to 5s Refresh)...")
        
        try:
            for i in range(len(lats)):
                fabric_payload = {
                    "IngestionTime": datetime.now(timezone.utc).isoformat(),
                    "MMSI": 999888778,
                    "ShipName": ship_name,
                    "VesselType": 80, 
                    "Latitude": round(lats[i], 5),
                    "Longitude": round(lons[i], 5),
                    "SpeedKnots": 15.0,
                    "HeadingDegrees": 45 if i < 50 else 110,
                    "TransmittedUtc": datetime.now(timezone.utc).isoformat()
                }
                
                event_data = EventData(json.dumps(fabric_payload))
                with producer:
                    producer.send_batch([event_data])
                
                print(f"Step {i+1}/100 sent. Waiting 5s for Map Sync...")
                
                # MATCH THIS TO YOUR DASHBOARD REFRESH
                time.sleep(5) 

            print("\n✅ Resetting to Dubai...")
            time.sleep(2)

        except KeyboardInterrupt:
            break
    producer.close()

stream_simulation()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
