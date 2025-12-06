import requests
from datetime import datetime, timedelta, timezone
import os
from bs4 import BeautifulSoup

YORK_REGION_MUNICIPALITIES = [
    'Markham', 'Vaughan', 'Richmond Hill', 'Newmarket', 'Aurora',
    'East Gwillimbury', 'Georgina', 'King', 'Whitchurch-Stouffville'
]

AUTO_THEFT_LABELS = {
    'case_type_pubtrans': {'Theft Over $5000 - Vehicle','Theft Under $5000 - Vehicle'},
    'occ_type': {'Theft of Motor Vehicle','Motor Vehicle Theft'}
}

API_URL = "https://services8.arcgis.com/lYI034SQcOoxRCR7/arcgis/rest/services/Occurrence/FeatureServer/0/query"

def fetch_data(start_ms: int, end_ms: int):
    features, offset, page = [], 0, 2000
    while True:
        resp = requests.post(
            API_URL,
            data={
                'where': '1=1',
                'time': f'{start_ms},{end_ms}',            # server-side time filter (UTC ms)
                'outFields': 'municipality,rep_date,occ_date,case_type_pubtrans,occ_type',
                'returnGeometry': 'false',
                'orderByFields': 'rep_date DESC',
                'resultOffset': offset,
                'resultRecordCount': page,
                'returnExceededLimitFeatures': 'true',
                'f': 'pjson',
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if 'error' in data:
            raise RuntimeError(f"ArcGIS error: {data['error']}")
        batch = data.get('features') or []
        features.extend(batch)
        if not batch or len(batch) < page:
            break
        offset += len(batch)
    return {'features': features}

def get_props(feature):
    return feature.get('attributes') or feature.get('properties') or {}

def filter_york(features):
    return [f for f in features if get_props(f).get('municipality') in YORK_REGION_MUNICIPALITIES]

def get_bounds(period: str = "rolling7", weeks_back: int = 0):
    now = datetime.now(timezone.utc)
    if period == "iso_week":
        # Monday–Sunday week window in UTC
        anchor = now - timedelta(days=now.weekday() + 7 * weeks_back)
        start_dt = datetime(anchor.year, anchor.month, anchor.day, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif period == "rolling7":
        end_dt = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc) - timedelta(days=7*weeks_back)
        start_dt = end_dt - timedelta(days=6)
    elif period == "last30":
        end_dt = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
        start_dt = end_dt - timedelta(days=29)
    else:
        raise ValueError(f"Unknown period: {period}")
    return start_dt, end_dt, int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)

def in_window(ms, start_ms, end_ms):
    return isinstance(ms, (int, float)) and start_ms <= ms <= end_ms

def count_auto_theft(features, start_ms, end_ms):
    count = 0
    for f in features:
        p = get_props(f)
        ts = p.get('rep_date') or p.get('occ_date')
        if not in_window(ts, start_ms, end_ms):
            continue
        if (p.get('case_type_pubtrans') in AUTO_THEFT_LABELS['case_type_pubtrans']) or \
           (p.get('occ_type') in AUTO_THEFT_LABELS['occ_type']):
            count += 1
    return count

def update_auto_theft_template(path, count, start_dt, end_dt, prev_count=None):
    with open(path, 'r', encoding='utf-8') as fh:
        html = fh.read()
    soup = BeautifulSoup(html, 'html.parser')

    # Range
    ws = start_dt.strftime('%b %d'); we = end_dt.strftime('%b %d')
    rng = soup.find(id='week-range')
    if rng: rng.clear(); rng.append(f"{ws} - {we}")

    # Count
    cnt = soup.find(id='auto-theft-count')
    if not cnt:
        cnt = soup.new_tag('span', id='auto-theft-count')
        cnt['class'] = 'text-7xl font-extrabold tracking-tight'
        (rng.parent if rng and rng.parent else (soup.body or soup)).append(cnt)
    cnt.clear(); cnt.append(str(count))

    # Trend/delta if prev_count provided
    if prev_count is not None:
        delta = count - prev_count
        percent = (delta / prev_count * 100) if prev_count > 0 else (100.0 if count > 0 else 0.0)
        trend_label = soup.find(id='trend-label')
        if trend_label:
            trend_label.clear()
            trend_label.append('Up vs last week' if delta > 0 else ('Down vs last week' if delta < 0 else 'Flat vs last week'))
        delta_inc = soup.find(id='delta-incidents')
        if delta_inc:
            sign = '+' if delta >= 0 else ''
            delta_inc.clear()
            delta_inc.append(f"{sign}{delta} incidents")
        delta_pct = soup.find(id='delta-percent')
        if delta_pct:
            sign = '+' if percent >= 0 else ''
            delta_pct.clear()
            delta_pct.append(f"(≈{sign}{round(percent)}%)")

    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(str(soup))

def main():
    period = os.environ.get('PERIOD', 'rolling7')  # rolling7 | iso_week | last30

    # Current window
    start_dt, end_dt, start_ms, end_ms = get_bounds(period=period, weeks_back=0)
    data = fetch_data(start_ms, end_ms)
    features = data.get('features') or []
    york = filter_york(features)
    current_count = count_auto_theft(york, start_ms, end_ms)

    # Previous window (same length, 1 week back)
    prev_start_dt, prev_end_dt, prev_start_ms, prev_end_ms = get_bounds(period=period, weeks_back=1)
    prev_data = fetch_data(prev_start_ms, prev_end_ms)
    prev_features = prev_data.get('features') or []
    prev_york = filter_york(prev_features)
    previous_count = count_auto_theft(prev_york, prev_start_ms, prev_end_ms)

    print(f"Current window: {start_dt.date()}..{end_dt.date()} | York features: {len(york)} | Auto thefts: {current_count}")
    print(f"Previous window: {prev_start_dt.date()}..{prev_end_dt.date()} | York features: {len(prev_york)} | Auto thefts: {previous_count}")

    template_path = os.path.join('templates', 'auto-theft.html')
    update_auto_theft_template(template_path, current_count, start_dt, end_dt, prev_count=previous_count)
    print(f"Updated {template_path}")

if __name__ == '__main__':
    main()