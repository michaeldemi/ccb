import requests
from datetime import datetime, timedelta, timezone

API_URL = "https://services8.arcgis.com/lYI034SQcOoxRCR7/arcgis/rest/services/Occurrence/FeatureServer/0/query"
YORK_REGION_MUNICIPALITIES = ['Markham','Vaughan','Richmond Hill','Newmarket','Aurora','East Gwillimbury','Georgina','King','Whitchurch-Stouffville']
DATA_SOURCE_TEXT = "Source: York Regional Police"

def fetch_time_window(start_ms: int, end_ms: int, out_fields: str, order: str = 'rep_date DESC'):
    features, offset, page = [], 0, 2000
    while True:
        r = requests.post(API_URL, data={
            'where': '1=1',
            'time': f'{start_ms},{end_ms}',         # CRITICAL: server-side time filter
            'outFields': out_fields,
            'returnGeometry': 'false',
            'orderByFields': order,
            'resultOffset': offset,
            'resultRecordCount': page,
            'returnExceededLimitFeatures': 'true',
            'f': 'pjson',
        }, timeout=30)
        r.raise_for_status()
        data = r.json()
        batch = data.get('features') or []
        features.extend(batch)
        if not batch or len(batch) < page:
            break
        offset += len(batch)
    return features

def attrs(f): return f.get('attributes') or f.get('properties') or {}
def filter_york(features): return [f for f in features if attrs(f).get('municipality') in YORK_REGION_MUNICIPALITIES]

def bounds(period="rolling7", weeks_back=0):
    now = datetime.now(timezone.utc)
    if period == "rolling7":
        end_dt = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc) - timedelta(days=7*weeks_back)
        start_dt = end_dt - timedelta(days=6)
    elif period == "iso_week":
        anchor = now - timedelta(days=now.weekday() + 7*weeks_back)
        start_dt = datetime(anchor.year, anchor.month, anchor.day, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif period == "last30":
        end_dt = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
        start_dt = end_dt - timedelta(days=29)
    else:
        raise ValueError(period)
    return start_dt, end_dt, int(start_dt.timestamp()*1000), int(end_dt.timestamp()*1000)