# Scripts

- **stop-id.py** - Get the stop_id for a bus stop from the stop code ( 8313 -> 8313-ec0c55f5 )
- **get-stop-trips.py** - Get the next buses due at a bus stop using the stop_id
  - runs every 30 minutes or so
  - saves the list of trips due in next hour to a file ( trip_id, trip_start_time, arrival_time )
- **display-info.py** - Display the approaching bus information in a simple format
  - runs every minute or so
  - reads the list of trips due in next hour from a file and checks their delay status
  - outputs simple csv with estimated time of arrival ( trips_id, route_id (shortened) , time, delay ) sorted by next buses due
  - Checks buses every ( estimated  /5 ) with miniumum 35s
  - looks at buses due in in prev 10 minutes or next 30 minutes
  - needs to mark buses than have gione past as done so they are not checked again
  - buses returning no info assumed on time
  - ignores buses not due to leave until 2 minutes from in future ( to avoid buses that have not yet started their trip )
  - outputs to a file for next stage to read
  - probably needs some sort of storage file  ( can this be combined with the main output file ? )
  - use sqlite to keep track of state of trips of interest ( done, last checked time, last delay status , et)
  - good test stop is 7149-6d6d1e99 ( Symond St, near Cordis Hotel ) which has a lot of buses
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


