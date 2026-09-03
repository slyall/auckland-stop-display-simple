# Sample API usage and output

## Stop ID lookup

$ curl -s "https://api.at.govt.nz/gtfs/v3/stops"   -H "Ocp-Apim-Subscription-Key: $AT_API_KEY"   | jq '.data[] | select(.attributes.stop_code == "8313")' 
{
  "type": "stop",
  "id": "8313-ec0c55f5",
  "attributes": {
    "location_type": 0,
    "stop_code": "8313",
    "stop_id": "8313-ec0c55f5",
    "stop_lat": -36.88937,
    "stop_lon": 174.73701,
    "stop_name": "Edendale Reserve",
    "wheelchair_boarding": 0
  }
}

## Stop info via stop_id

$ curl -s "https://api.at.govt.nz/gtfs/v3/stops/7149-6d6d1e99"   -H "Ocp-Apim-Subscription-Key: $AT_API_KEY"   | jq . 
{
  "data": {
    "type": "stop",
    "id": "7149-6d6d1e99",
    "attributes": {
      "location_type": 0,
      "stop_code": "7149",
      "stop_id": "7149-6d6d1e99",
      "stop_lat": -36.85741,
      "stop_lon": 174.76449,
      "stop_name": "Symonds Street/Karangahape Road",
      "wheelchair_boarding": 0
    }
  }
}


## List of trips for a stop soon (truncated)

$ curl -sG "https://api.at.govt.nz/gtfs/v3/stops/$STOP_ID/stoptrips"   -H "Ocp-Apim-Subscription-Key: $AT_API_KEY"   --data-urlencode "filter[date]=$(date +%F)"   --data-urlencode "filter[start_hour]=$(date +%H)" --data-urlencode "filter[hour_range]=1" | jq .
{
  "data": [
    {
      "type": "stoptrip",
      "id": "stop:8313-ec0c55f5_trip:24-02403-41760-2-d46c47e0",
      "attributes": {
        "arrival_time": "12:01:17",
        "departure_time": "12:01:17",
        "direction_id": 0,
        "drop_off_type": 0,
        "pickup_type": 0,
        "route_id": "24B-202",
        "service_date": "2026-09-03",
        "shape_id": "24-02403-ad20305e",
        "stop_headsign": "CITY CENTRE",
        "stop_id": "8313-ec0c55f5",
        "stop_sequence": 26,
        "trip_headsign": "New Lynn And Blockhouse Bay To City Centre Via Sandringham R",
        "trip_id": "24-02403-41760-2-d46c47e0",
        "trip_start_time": "11:36:00"
      }
    },
    {
      "type": "stoptrip",
      "id": "stop:8313-ec0c55f5_trip:1279-02401-43020-2-bf1d8aa7",
      "attributes": {
        "arrival_time": "12:16:17",
        "departure_time": "12:16:17",
        "direction_id": 0,
        "drop_off_type": 0,
        "pickup_type": 0,
        "route_id": "24R-202",
        "service_date": "2026-09-03",
        "shape_id": "1279-02401-7736f3a4",
        "stop_headsign": "CITY CENTRE",
        "stop_id": "8313-ec0c55f5",
        "stop_sequence": 22,
        "trip_headsign": "New Lynn To City Centre Via Sandingham Rd",
        "trip_id": "1279-02401-43020-2-bf1d8aa7",
        "trip_start_time": "11:57:00"
      }
    },


## Realtime trip updates

 curl -sG "https://api.at.govt.nz/realtime/legacy/tripupdates?tripid=27-02707-44100-2-fe6656cf,1153-07005-42600-2-0a9d0b39,25-02505-44100-2-0cdf365d" -H "Ocp-Apim-Subscription-Key: $AT_API_KEY" | jq . 
{
  "status": "OK",
  "response": {
    "header": {
      "timestamp": 1788396395.515,
      "gtfs_realtime_version": "1.0",
      "incrementality": 0
    },
    "entity": [
      {
        "id": "27-02707-44100-2-fe6656cf",
        "trip_update": {
          "trip": {
            "trip_id": "27-02707-44100-2-fe6656cf",
            "start_time": "12:15:00",
            "start_date": "20260903",
            "schedule_relationship": 0,
            "route_id": "27H-202",
            "direction_id": 0
          },
          "stop_time_update": {
            "stop_sequence": 36,
            "departure": {
              "delay": -590,
              "time": 1788396338,
              "uncertainty": 0
            },
            "stop_id": "7141-d8af5868",
            "schedule_relationship": 0
          },
          "vehicle": {
            "id": "14297",
            "label": "NB4297",
            "license_plate": "HDK664"
          },
          "timestamp": 1788396338,
          "delay": -590
        },
        "is_deleted": false
      },
      {
        "id": "1153-07005-42600-2-0a9d0b39",
        "trip_update": {
          "trip": {
            "trip_id": "1153-07005-42600-2-0a9d0b39",
            "start_time": "11:50:00",
            "start_date": "20260903",
            "schedule_relationship": 0,
            "route_id": "70-205",
            "direction_id": 0
          },
          "stop_time_update": {
            "stop_sequence": 38,
            "arrival": {
              "delay": -43,
              "time": 1788396388,
              "uncertainty": 0
            },
            "departure": {
              "delay": -43,
              "time": 1788396388,
              "uncertainty": 10
            },
            "stop_id": "7227-3ccd581c",
            "schedule_relationship": 0
          },
          "vehicle": {
            "id": "24518",
            "label": "HE0518",
            "license_plate": "MHY988"
          },
          "timestamp": 1788396388,
          "delay": -43
        },
        "is_deleted": false
      },
      {
        "id": "25-02505-44100-2-0cdf365d",
        "trip_update": {
          "trip": {
            "trip_id": "25-02505-44100-2-0cdf365d",
            "start_time": "12:15:00",
            "start_date": "20260903",
            "schedule_relationship": 0,
            "route_id": "25B-202",
            "direction_id": 0
          },
          "stop_time_update": {
            "stop_sequence": 38,
            "departure": {
              "delay": -261,
              "time": 1788396297,
              "uncertainty": 0
            },
            "stop_id": "8501-bc9f89ab",
            "schedule_relationship": 0
          },
          "vehicle": {
            "id": "15301",
            "label": "NB5301",
            "license_plate": "KSA889"
          },
          "timestamp": 1788396297,
          "delay": -215
        },
        "is_deleted": false
      }
    ]
  },
  "error": null
}
