# Scripts

- **stop-id.py** - Get the stop_id for a bus stop from the stop code ( 8313 -> 8313-ec0c55f5 )
- **get-stop-trips.py** - Get the next buses due at a bus stop using the stop_id
  - runs every 30 minutes or so
  - saves the list of trips due in next hour to a file ( trip_id, route_id, arrival_time, stop_sequence )
- **display-info.py** - Display the approaching bus information in a simple format
  - runs every minute or so from cron job
  - reads the list of trips due in next hour from a file (created by get-stop-trips.py) and checks their delay status
    - Need simple way to know which ones to check
    - Probably first time just check all the ones in the file
      - this might be a one-shot  mode that doesn't read or write to the output file or db, just checks the trips in the file and outputs to screen
    - Trips can be then marked as past us ( no need to check again ), no left ( check regularly from 5 minutes for sceduled leave time, then every 2 minutes until it has left )
    -  Checks buses every ( estimated 1/5 of remaining distance ) with miniumum 35s
  - outputs simple csv with estimated time of arrival ( route_id (shortened), time, minutes away, stops away ) sorted by next buses due
  - buses returning no info assumed on time
  - Should query multiple trips at once (API allows this) to reduce number of API calls
  - probably needs some sort of storage file  ( can this be combined with the main output file ? )
  - use sqlite to keep track of state of trips of interest ( done, last checked time, last delay status , etc )
  - Command line to filer in/out trips of interest ( route probably, maybe trip_id too )
  - good test stop is 7149-6d6d1e99 ( Symond St, near Cordis Hotel ) which has a lot of buses
  - Should optionally output a pretty text version of the display
    - header with stop name, current time, stop short number
    - Buses arriving in next 40 minutes, max to show is 10 buses
    - line has bus route name, time due and minutes that is away 
  - Initial implementation uses `display-info.db` (SQLite) for trip state and writes `display.csv`
    atomically for the next stage. It reads `trips.txt` from `get-stop-trips.py` by default.
  - Run `python3 display-info.py --pretty --stop-name "Symonds St"` for a human-readable view.
- **tell-pico.py** - Push the next two bus ETAs to a Raspberry Pi Pico
  - runs every minute or so ( dueing waking ours )
  - outputs time time next two buses are away and sends to pi ( 07, 15 ) 
  - reads top two lines of previous file and checks if changed since last time, if so sends to pi

## Notes for the scripts

- The bus stop code is the number on the bus stop sign ( 8313 )
- The bus stop id is the number used by the Auckland transport site ( 8313-ec0c55f5 )
- Scripts should have debug mode that outputs data to screen
- each need to have output to files so next stage can read
- API key should be read from environment variable $AT_API_KEY


