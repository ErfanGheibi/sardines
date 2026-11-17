import asyncio
import csv
import io
import os
import time
import zipfile
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse
import tfnsw_metro_pb2 as metro_pb

# Set with: export TFNSW_API_KEY="your token"
API_KEY = os.environ.get("TFNSW_API_KEY", "")
BASE = "https://api.transport." + "nsw.gov.au"
VEHPOS_URL = f"{BASE}/v2/gtfs/vehiclepos/metro"
TRIPUPD_URL = f"{BASE}/v2/gtfs/realtime/metro"
STATIC_GTFS_URL = f"{BASE}/v1/gtfs/schedule/metro"

LINE_ORDER = [
    "Tallawong", "Rouse Hill", "Kellyville", "Bella Vista", "Norwest",
    "Hills Showground", "Castle Hill", "Cherrybrook", "Epping",
    "Macquarie University", "Macquarie Park", "North Ryde", "Chatswood",
    "Crows Nest", "Victoria Cross", "Barangaroo", "Martin Place",
    "Gadigal", "Central", "Waterloo", "Sydenham",
    "Marrickville", "Dulwich Hill", "Hurlstone Park", "Canterbury",
    "Campsie", "Belmore", "Lakemba", "Wiley Park", "Punchbowl", "Bankstown"
]

KNOWN_PLATFORMS = {
    "2155264": "Tallawong", "2155265": "Tallawong", "2155260": "Tallawong",
    "2155266": "Rouse Hill", "2155267": "Rouse Hill", "2155261": "Rouse Hill",
    "2155268": "Kellyville", "2155269": "Kellyville", "2155262": "Kellyville",
    "2153473": "Bella Vista", "2153474": "Bella Vista", "2153470": "Bella Vista",
    "2153405": "Norwest", "2153406": "Norwest", "2153471": "Norwest", "2153472": "Norwest",
    "2154392": "Hills Showground", "2154393": "Hills Showground", "2154390": "Hills Showground",
    "2154264": "Castle Hill", "2154265": "Castle Hill", "2154391": "Castle Hill",
    "2126158": "Cherrybrook", "2126159": "Cherrybrook", "2126150": "Cherrybrook",
    "2121231": "Epping", "2121232": "Epping", "2121230": "Epping",
    "2113361": "Macquarie University", "2113362": "Macquarie University", "2113330": "Macquarie University",
    "2113351": "Macquarie Park", "2113352": "Macquarie Park", "2113331": "Macquarie Park",
    "2113341": "North Ryde", "2113342": "North Ryde", "2113332": "North Ryde",
    "2067161": "Chatswood", "2067162": "Chatswood", "2067160": "Chatswood",
    "2065161": "Crows Nest", "2065162": "Crows Nest", "2065160": "Crows Nest",
    "2060113": "Victoria Cross", "2060114": "Victoria Cross", "2060120": "Victoria Cross",
    "2000434": "Barangaroo", "2000435": "Barangaroo", "2000430": "Barangaroo",
    "2000436": "Martin Place", "2000437": "Martin Place", "2000431": "Martin Place",
    "2000438": "Gadigal", "2000439": "Gadigal", "2000432": "Gadigal",
    "2000440": "Central", "2000441": "Central", "2000433": "Central",
    "2015131": "Waterloo", "2015132": "Waterloo", "2015130": "Waterloo",
    "2044111": "Sydenham", "2044112": "Sydenham", "2044110": "Sydenham",
    "2204111": "Marrickville", "2204112": "Marrickville", "220410": "Marrickville",
    "2203111": "Dulwich Hill", "2203112": "Dulwich Hill", "220310": "Dulwich Hill",
    "2193111": "Hurlstone Park", "2193112": "Hurlstone Park", "219310": "Hurlstone Park",
    "2193121": "Canterbury", "2193122": "Canterbury", "219320": "Canterbury",
    "2194111": "Campsie", "2194112": "Campsie", "219410": "Campsie",
    "2195111": "Belmore", "2195112": "Belmore", "219510": "Belmore",
    "2195121": "Lakemba", "2195122": "Lakemba", "219520": "Lakemba",
    "2195131": "Wiley Park", "2195132": "Wiley Park", "219530": "Wiley Park",
    "2196111": "Punchbowl", "2196112": "Punchbowl", "219610": "Punchbowl",
    "2200111": "Bankstown", "2200112": "Bankstown", "220010": "Bankstown",
}

OCCUPANCY_SCORES = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 99}
app = FastAPI()
LAST_STOPPED = {}
cached_data = {"ready": False, "updated_at": "Syncing...", "stations": LINE_ORDER, "trains": []}


def clean_station_name(raw):
    return raw.split(" Station")[0].split(", Platform")[0].strip()


def load_official_stops():
    """Download TfNSW static Metro stops.txt once to map all platform IDs."""
    headers = {"Authorization": f"apikey {API_KEY}"}
    resp = requests.get(STATIC_GTFS_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        with zf.open("stops.txt") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
            for row in reader:
                sid = row.get("stop_id", "").strip()
                raw = row.get("stop_name", "").strip()
                if sid and raw:
                    KNOWN_PLATFORMS[sid] = clean_station_name(raw)
    print(f"Loaded {len(KNOWN_PLATFORMS)} Metro stop IDs from official GTFS.")


def next_station_after(station, dir_key):
    if station not in LINE_ORDER:
        return station
    idx = LINE_ORDER.index(station)
    if dir_key == "Bankstown" and idx + 1 < len(LINE_ORDER):
        return LINE_ORDER[idx + 1]
    if dir_key == "Tallawong" and idx - 1 >= 0:
        return LINE_ORDER[idx - 1]
    return station


def resolve_stop(sid):
    if sid in KNOWN_PLATFORMS:
        return KNOWN_PLATFORMS[sid]
    try:
        r = requests.get(
            f"{BASE}/v1/tp/stop_finder",
            params={"outputFormat": "rapidJSON", "type_sf": "stop", "name_sf": sid},
            headers={"Authorization": f"apikey {API_KEY}"},
            timeout=3,
        )
        for loc in r.json().get("locations", []):
            raw = loc.get("disassembledName") or loc.get("name", "")
            clean = clean_station_name(raw)
            if clean:
                KNOWN_PLATFORMS[sid] = clean
                return clean
    except Exception:
        pass
    return f"Stop {sid}"


def poll_feeds():
    headers = {"Authorization": f"apikey {API_KEY}"}
    now_ts = int(time.time())

    tu_resp = requests.get(TRIPUPD_URL, headers=headers, timeout=10)
    tu_resp.raise_for_status()
    tu_feed = metro_pb.FeedMessage()
    tu_feed.ParseFromString(tu_resp.content)

    trip_etas = {}
    for entity in tu_feed.entity:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        tid = tu.trip.trip_id
        upcoming = {}
        for stu in tu.stop_time_update:
            arr_ts = stu.arrival.time or stu.departure.time
            if arr_ts and arr_ts >= now_ts - 15:
                st_name = resolve_stop(stu.stop_id)
                mins = max(0, round((arr_ts - now_ts) / 60))
                if st_name not in upcoming or mins < upcoming[st_name]:
                    upcoming[st_name] = mins
        trip_etas[tid] = upcoming

    vp_resp = requests.get(VEHPOS_URL, headers=headers, timeout=10)
    vp_resp.raise_for_status()
    vp_feed = metro_pb.FeedMessage()
    vp_feed.ParseFromString(vp_resp.content)

    trains = []
    for entity in vp_feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        vid = v.vehicle.id or v.trip.trip_id
        tid = v.trip.trip_id
        dir_key = "Bankstown" if v.trip.direction_id == 0 else "Tallawong"
        state = "STOPPED" if v.current_status == 1 else "MOVING"
        station = resolve_stop(v.stop_id)

        trip_key = f"{vid}:{tid}"
        if state == "STOPPED":
            LAST_STOPPED[trip_key] = station
        elif LAST_STOPPED.get(trip_key) == station:
            station = next_station_after(station, dir_key)

        carriages = []
        for idx, c in enumerate(v.consist, start=1):
            carriages.append({
                "pos": idx,
                "score": OCCUPANCY_SCORES.get(c.occupancy_status, 50),
            })

        trains.append({
            "dir": dir_key,
            "state": state,
            "station": station,
            "etas": trip_etas.get(tid, {}),
            "carriages": carriages,
        })

    cached_data["ready"] = True
    cached_data["updated_at"] = time.strftime("%I:%M:%S %p")
    cached_data["stations"] = LINE_ORDER
    cached_data["trains"] = trains


async def background_poller():
    try:
        await asyncio.to_thread(load_official_stops)
    except Exception as e:
        print("GTFS static stops fallback active:", e)
    while True:
        try:
            await asyncio.to_thread(poll_feeds)
        except Exception as e:
            print("Poll error:", e)
        await asyncio.sleep(8)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_poller())


@app.get("/api/metro")
def get_metro():
    return cached_data


@app.get("/")
def index():
    return FileResponse("index.html")
