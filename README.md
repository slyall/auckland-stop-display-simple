# auckland-stop-display-simple
Display information the next buses due at an Auckland bus stop


# API setup using Auckland transport site
TODO

# Scripts

- **stop-id.py** - get the stop id for a bus stop from the stop code ( 1234 -> 1234-56789 )
- **get-stop-info.py** - get the next buses due at a bus stop using the stop id
  - runs every 30 minutes or so
  - saves the list of trips due in next hour to a file ( trip_id,services,time )
- **display-info.py** - display the bus information in a simple format
  - runs every minute or so
  - reads the list of trips due in next hour from a file and checks their delay status
  - outputs simple csv with estimated time of arrival ( trips_id, services, time, delay ) sorted by next buses due
- **tell-pico.py** - display the bus information on a Raspberry Pi Pico
  - runs every minute or so ( dueing waking ours )
  - outputs time time next two buses are away and sends to pi ( 07, 15 ) 

## stop-id.py

This script converts a public Auckland Transport stop code into the full stop ID used by the API.

Example usage:

```bash
export AT_API_KEY="your-api-key-here"
python3 stop-id.py 8313
```

This resolves the Sandringham Road example stop code to:

```bash
8313-ec0c55f5
```

You can also inspect the fetched stop record directly:

```bash
curl "https://api.at.govt.nz/gtfs/v3/stops/8313-ec0c55f5" \
  -H "Ocp-Apim-Subscription-Key: $AT_API_KEY" | jq .
```

This is useful because the AT API uses the longer `stop_id` value for timetable and realtime lookups, while the public stop sign on the street shows only the shorter stop code.

Notes
  - The bus stop code is the number on the bus stop sign ( 1234 )
  - The bus stop id is the number used by the Auckland transport site ( 1234-56789 )
  - Scripts should have debug mode that outputs data to screen
  - each need to have output to files so next stage can read
  - API key should be read from environment variable $AT_API_KEY 