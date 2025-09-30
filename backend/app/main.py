from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import os
import json
from typing import Dict, List
import httpx


app = FastAPI(title="Ruhobod API")

# Basic CORS for local dev frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


def _local_prayer_schedule_for(date: datetime) -> Dict[str, Dict[str, str]]:
    """Local fallback timetable for Samarkand, Uzbekistan.
    
    TODO: Replace with IslamicFinder API or accurate calculation method.
    These are approximate times for Samarkand (39.6547° N, 66.9597° E).
    """
    # Approximate times for Samarkand in winter (adjust seasonally)
    return {
        "fajr": {"start": "05:45", "jamaah": "06:15"},
        "sunrise": {"start": "07:15", "jamaah": None},
        "dhuhr": {"start": "12:30", "jamaah": "13:00"},
        "asr": {"start": "15:30", "jamaah": "16:00"},
        "maghrib": {"start": "17:45", "jamaah": "17:45"},
        "isha": {"start": "19:15", "jamaah": "19:45"},
    }


@app.get("/prayer/daily")
def daily_prayer_times():
    today = datetime.now()
    # Try Aladhan API first
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://api.aladhan.com/v1/timingsByCity",
                params={
                    "city": "Samarkand",
                    "country": "Uzbekistan",
                    "method": 2,  # Islamic Society of North America (adjustable later)
                },
            )
            data = resp.json()
            if data.get("code") == 200:
                t = data["data"]["timings"]
                # Map to our model: use HH:MM format
                def clean(s: str) -> str:
                    return s.split(" ")[0]

                schedule = {
                    "fajr": {"start": clean(t["Fajr"]), "jamaah": None},
                    "sunrise": {"start": clean(t["Sunrise"]), "jamaah": None},
                    "dhuhr": {"start": clean(t["Dhuhr"]), "jamaah": None},
                    "asr": {"start": clean(t["Asr"]), "jamaah": None},
                    "maghrib": {"start": clean(t["Maghrib"]), "jamaah": None},
                    "isha": {"start": clean(t["Isha"]), "jamaah": None},
                }
                flat = {
                    "date": today.strftime("%Y-%m-%d"),
                    "fajr": schedule["fajr"]["start"],
                    "sunrise": schedule["sunrise"]["start"],
                    "dhuhr": schedule["dhuhr"]["start"],
                    "asr": schedule["asr"]["start"],
                    "maghrib": schedule["maghrib"]["start"],
                    "isha": schedule["isha"]["start"],
                }
                return {
                    **flat,
                    "schedule": schedule,
                    "jummah": ["13:00", "13:45"],
                    "location": "Samarkand, Uzbekistan",
                    "source": "aladhan",
                }
    except Exception:
        pass

    # Fallback to local approximations
    schedule = _local_prayer_schedule_for(today)
    flat = {
        "date": today.strftime("%Y-%m-%d"),
        "fajr": schedule["fajr"]["start"],
        "sunrise": schedule["sunrise"]["start"],
        "dhuhr": schedule["dhuhr"]["start"],
        "asr": schedule["asr"]["start"],
        "maghrib": schedule["maghrib"]["start"],
        "isha": schedule["isha"]["start"],
    }
    return {
        **flat,
        "schedule": schedule,
        "jummah": ["13:00", "13:45"],
        "location": "Samarkand, Uzbekistan",
        "source": "local-fallback",
    }


@app.get("/prayer/weekly")
def weekly_prayer_times():
    start = datetime.now()
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://api.aladhan.com/v1/calendarByCity",
                params={
                    "city": "Samarkand",
                    "country": "Uzbekistan",
                    "method": 2,
                    "month": start.month,
                    "year": start.year,
                },
            )
            data = resp.json()
            if data.get("code") == 200:
                # Slice the next 7 days from today index
                today_str = start.strftime("%Y-%m-%d")
                entries = data["data"]
                # Map entries to date string -> timings
                mapped: List[Dict[str, Dict[str, str]]] = []
                for e in entries:
                    date_str = e["date"]["gregorian"]["date"].replace("-", "-")
                    if date_str >= today_str and len(mapped) < 7:
                        t = e["timings"]
                        def clean(s: str) -> str:
                            return s.split(" ")[0]
                        schedule = {
                            "fajr": {"start": clean(t["Fajr"]), "jamaah": None},
                            "sunrise": {"start": clean(t["Sunrise"]), "jamaah": None},
                            "dhuhr": {"start": clean(t["Dhuhr"]), "jamaah": None},
                            "asr": {"start": clean(t["Asr"]), "jamaah": None},
                            "maghrib": {"start": clean(t["Maghrib"]), "jamaah": None},
                            "isha": {"start": clean(t["Isha"]), "jamaah": None},
                        }
                        mapped.append({"date": date_str, "schedule": schedule})
                if mapped:
                    return {"days": mapped, "source": "aladhan"}
    except Exception:
        pass

    # Fallback to local approximations
    days: List[Dict[str, Dict[str, str]]] = []
    for i in range(7):
        d = start + timedelta(days=i)
        schedule = _local_prayer_schedule_for(d)
        days.append({"date": d.strftime("%Y-%m-%d"), "schedule": schedule})
    return {"days": days, "source": "local-fallback"}
