# auckland-stop-display-simple
Display information the next buses due at an Auckland bus stop


# API setup using Auckland transport site
TODO

# Bash Examples

```bash
# Export you key for later queries
export AT_API_KEY="your-api-key-here"

# Get your stop id for a bus stop from the stop code ( 8313 -> 8313-ec0c55f5 )
curl "https://api.at.govt.nz/gtfs/v3/stops" \
  -H "Ocp-Apim-Subscription-Key: $AT_API_KEY" \
  | jq '.data[] | select(.attributes.stop_code == "8313") | .attributes | {stop_code, stop_id, stop_name}'

# Get info about the stop using the stop ID ( 8313-ec0c55f5 )
curl "https://api.at.govt.nz/gtfs/v3/stops/8313-ec0c55f5" \
  -H "Ocp-Apim-Subscription-Key: $AT_API_KEY" | jq .

# Get the trips due at a bus stop in two hour window using the stop id ( 8313-ec0c55f5 )
# Note that API does not accept 0, 00 or 24 for the hour. Use 23 instead
curl 'https://api.at.govt.nz/gtfs/v3/stops/8313-ec0c55f5/stoptrips?filter\[date\]=2026-09-02&filter\[start_hour\]=16&filter\[hour_range\]=2'  -H "Ocp-Apim-Subscription-Key: $AT_API_KEY" | jq .

# Or in a more readable format
curl -G "https://api.at.govt.nz/gtfs/v3/stops/8313-ec0c55f5/stoptrips" \
  -H "Ocp-Apim-Subscription-Key: $AT_API_KEY" \
  --data-urlencode "filter[date]=$(date +%F)" \
  --data-urlencode "filter[start_hour]=$(date +%H" \
  --data-urlencode "filter[hour_range]=2" | jq .

# Get the status of two trips using the trip id
# Note a query for a trip not yet running will return a empty result, so you may need to query for a trip that is currently running or has already run
curl -G "https://api.at.govt.nz/realtime/legacy/tripupdates?tripid=24-02403-56100-2-0705c91b,24-02403-59700-2-916eceb7" -H "Ocp-Apim-Subscription-Key: $AT_API_KEY" | jq .
```


# Scripts

- **stop-id.py** - get the stop id for a bus stop from the stop code ( 8313 -> 8313-ec0c55f5 )
- **get-stop-trips.py** - get the next buses due at a bus stop using the stop id
  - runs every 30 minutes or so
  - saves the list of trips due in next hour to a file ( trip_id, time )
- **display-info.py** - display the bus information in a simple format
  - runs every minute or so
  - reads the list of trips due in next hour from a file and checks their delay status
  - outputs simple csv with estimated time of arrival ( trips_id, services, time, delay ) sorted by next buses due
- **tell-pico.py** - display the bus information on a Raspberry Pi Pico
  - runs every minute or so ( dueing waking ours )
  - outputs time time next two buses are away and sends to pi ( 07, 15 ) 

## Notes for the scripts

- The bus stop code is the number on the bus stop sign ( 8313 )
- The bus stop id is the number used by the Auckland transport site ( 8313-ec0c55f5 )
- Scripts should have debug mode that outputs data to screen
- each need to have output to files so next stage can read
- API key should be read from environment variable $AT_API_KEY

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

This is useful because the AT API uses the longer `stop_id` value for timetable and realtime lookups, while the public stop sign on the street shows only the shorter stop code.

# Links

## Auckland Transport

- [AT data sources](https://at.govt.nz/about-us/at-data-sources)
- [Auckland Transport Developer Portal](https://dev-portal.at.govt.nz/)

## Other Projects

- [Auckland Transport Card](https://github.com/SeitzDaniel/auckland-transport-card)
- [Auckland Live LED Train Map](https://github.com/CDFER/Auckland-LED-Train-Map)
- [A simplified interface for the Auckland Transport API](https://github.com/Richienb/auckland-transport) - Probably out of date