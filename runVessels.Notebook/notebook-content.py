# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "environment": {}
# META   }
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
# 3. AISSTREAM_API_KEY: Your AisStream.io API key
#    - Generate at: https://aisstream.io/ (free account)
#    - Store in Azure Key Vault for production OR set directly for testing
#

# Event Hub Configuration (from Eventstream custom endpoint)
FABRIC_ENTITY_NAME = "esehchxkj881x95xl1hgnk_eh"  # ← UPDATE THIS with your Event Hub name

# Security Configuration
# Option 1 (Production): Use Azure Key Vault
KEY_VAULT_NAME = "https://kv-maritime-demo.vault.azure.net/"  # ← UPDATE THIS with your Key Vault URL
AISSTREAM_API_KEY = mssparkutils.credentials.getSecret(KEY_VAULT_NAME, "AisStreamApiKey")
FABRIC_CONNECTION_STR = mssparkutils.credentials.getSecret(KEY_VAULT_NAME, "FabricConnectionString")

# Option 2 (Local Testing): Use direct values (NEVER commit to Git!)
# AISSTREAM_API_KEY = "your-aisstream-api-key-here"
# FABRIC_CONNECTION_STR = "Endpoint=sb://xxxxx.servicebus.windows.net/;SharedAccessKeyName=...;SharedAccessKey=...;EntityPath=esehchxkj881x95xl1hgnk_eh"

# ========================================

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import os
import asyncio
import json
import ssl
import sys
import time
from datetime import datetime, timezone
import websockets
from notebookutils import mssparkutils 
from azure.eventhub import EventHubProducerClient, EventData

TARGET_BOUNDING_BOX = [[[-90, -180], [90, 180]]]


def live_log(text: str) -> None:
    """Write log text to stdout without adding extra newlines."""
    sys.stdout.write(text)
    sys.stdout.flush()


async def stream_ais_to_fabric():
    """Stream AIS data over WebSocket and relay messages into Fabric Event Hub."""

    # Initialize the producer ONCE and reuse the connection for all events
    producer = EventHubProducerClient.from_connection_string(
        conn_str=FABRIC_CONNECTION_STR,
        eventhub_name=FABRIC_ENTITY_NAME,
    )

    uri = "wss://stream.aisstream.io/v0/stream"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    subscription_message = {
        "APIKey": AISSTREAM_API_KEY,
        "BoundingBoxes": TARGET_BOUNDING_BOX,
        "FilterMessageTypes": [
            "PositionReport",
            "StandardClassBPositionReport",
            "ExtendedClassBPositionReport",
        ],
    }

    # RECONNECT LOOP: If the connection drops, it will try again
    while True:
        live_log(f"\n[CONNECTING] Opening WebSocket to {uri}...\n")
        try:
            async with websockets.connect(
                uri,
                ssl=ssl_context,
                ping_interval=20,  # Send a ping every 20 seconds to keep it alive
                ping_timeout=20,  # Wait 20 seconds for a pong before giving up
            ) as websocket:

                await websocket.send(json.dumps(subscription_message))
                live_log("[CONNECTED] Relay active. Receiving global ship traffic...\n")

                while True:
                    try:
                        message_json = await asyncio.wait_for(
                            websocket.recv(), timeout=30
                        )
                        raw_data = json.loads(message_json)

                        msg_type = raw_data.get("MessageType")
                        if msg_type in [
                            "PositionReport",
                            "StandardClassBPositionReport",
                            "ExtendedClassBPositionReport",
                        ]:
                            report = raw_data.get("Message", {}).get(msg_type, {})
                            metadata = raw_data.get("MetaData", {})

                            fabric_payload = {
                                "IngestionTime": datetime.now(timezone.utc).isoformat(),
                                "MMSI": report.get("UserID"),
                                "ShipName": metadata.get("ShipName", "").strip(),
                                "VesselType": metadata.get("ShipType"),
                                "Latitude": report.get("Latitude"),
                                "Longitude": report.get("Longitude"),
                                "SpeedKnots": report.get("Sog"),
                                "HeadingDegrees": report.get("Cog"),
                                "TransmittedUtc": report.get("PositionUTC"),
                            }

                            event_data = EventData(json.dumps(fabric_payload))

                            # Use the producer as a context manager for each batch send
                            # to ensure proper flushing without recreating the client.
                            with producer:
                                producer.send_batch([event_data])

                            live_log(
                                f"🚢 {fabric_payload['ShipName']} ({fabric_payload['MMSI']}) | "
                                f"Lat: {fabric_payload['Latitude']}, Lon: {fabric_payload['Longitude']}\n"
                            )

                    except asyncio.TimeoutError:
                        live_log(" [No data for 30s - waiting] ")
                        continue

        except Exception as e:
            live_log(f"\n[CONNECTION LOST] Error: {e}\n")
            live_log("[RETRYING] Restarting connection in 5 seconds...\n")
            await asyncio.sleep(5)  # Wait before trying to reconnect


# --- EXECUTION ---
try:
    if asyncio.get_running_loop().is_running():
        await stream_ais_to_fabric()
    else:
        asyncio.run(stream_ais_to_fabric())
except Exception as e:
    print(f"Stopped: {e}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark",
# META   "frozen": false,
# META   "editable": true
# META }
