import requests
import json
from datetime import datetime, timedelta
import os

# York Region municipalities
YORK_REGION_MUNICIPALITIES = [
    'Markham', 'Vaughan', 'Richmond Hill', 'Newmarket', 'Aurora',
    'East Gwillimbury', 'Georgina', 'King', 'Whitchurch-Stouffville'
]

# Crime types mapping to template categories
CRIME_MAPPING = {
    'assaults': ['Assaults', 'Assault with a Weapon'],
    'auto-theft': ['Theft of Motor Vehicle'],
    'break-enter': ['Break and Enter - Residential', 'Break and Enter - Commercial']
}

def fetch_crime_data():
    """Fetch crime data from York Region Police API"""
    url = "https://services8.arcgis.com/lYI034SQcOoxRCR7/arcgis/rest/services/Occurrence/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def filter_york_region(data):
    """Filter data for York Region municipalities"""
    features = data.get('features', [])
    york_features = []
    
    for feature in features:
        props = feature.get('properties', {})
        municipality = props.get('municipality')
        if municipality in YORK_REGION_MUNICIPALITIES:
            york_features.append(feature)
    
    return {'type': 'FeatureCollection', 'features': york_features}

def calculate_weekly_stats(data, weeks_back=0):
    """Calculate stats for the specified week"""
    features = data.get('features', [])
    
    # Get current week range
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday() + 7 * weeks_back)
    week_end = week_start + timedelta(days=6)
    
    # Convert to timestamps (milliseconds since epoch)
    week_start_ts = int(week_start.timestamp() * 1000)
    week_end_ts = int(week_end.timestamp() * 1000)
    
    # Filter incidents in this week
    weekly_incidents = []
    for feature in features:
        props = feature.get('properties', {})
        occ_date = props.get('occ_date')
        if occ_date and week_start_ts <= occ_date <= week_end_ts:
            weekly_incidents.append(feature)
    
    # Count by crime type
    stats = {}
    for category, crime_types in CRIME_MAPPING.items():
        count = 0
        for incident in weekly_incidents:
            occ_type = incident['properties'].get('occ_type')
            if occ_type in crime_types:
                count += 1
        stats[category] = count
    
    return {
        'week_start': week_start.strftime('%b %d'),
        'week_end': week_end.strftime('%b %d'),
        'stats': stats,
        'total_incidents': len(weekly_incidents)
    }

def update_template(template_path, stats):
    """Update HTML template with stats"""
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Update week range
    week_range = f"{stats['week_start']} - {stats['week_end']}"
    content = content.replace('Oct 24 - Oct 30', week_range)
    
    # Update region
    content = content.replace('Peel Region', 'York Region')
    
    # Update counts and trends based on template type
    if 'assaults' in template_path:
        content = content.replace('47', str(stats['stats']['assaults']))
        trend = stats['trends']['assaults']
        content = content.replace('+2 incidents', f"{'+' if trend['delta'] >= 0 else ''}{trend['delta']} incidents")
        content = content.replace('(≈+44%)', f"(≈{'+' if trend['percent'] >= 0 else ''}{trend['percent']}%)")
    elif 'auto-theft' in template_path:
        content = content.replace('47', str(stats['stats']['auto-theft']))
        trend = stats['trends']['auto-theft']
        content = content.replace('+7 incidents', f"{'+' if trend['delta'] >= 0 else ''}{trend['delta']} incidents")
        content = content.replace('(≈+44%)', f"(≈{'+' if trend['percent'] >= 0 else ''}{trend['percent']}%)")
    elif 'break-enter' in template_path:
        # Assuming similar structure
        content = content.replace('47', str(stats['stats']['break-enter']))
        trend = stats['trends']['break-enter']
        content = content.replace('+7 incidents', f"{'+' if trend['delta'] >= 0 else ''}{trend['delta']} incidents")
        content = content.replace('(≈+44%)', f"(≈{'+' if trend['percent'] >= 0 else ''}{trend['percent']}%)")
    
    with open(template_path, 'w') as f:
        f.write(content)

def main():
    print("Fetching York Region Police data...")
    data = fetch_crime_data()
    if not data:
        return
    
    print(f"Fetched {len(data.get('features', []))} total incidents")
    
    york_data = filter_york_region(data)
    print(f"Filtered to {len(york_data.get('features', []))} York Region incidents")
    
    stats = calculate_weekly_stats(york_data)
    prev_stats = calculate_weekly_stats(york_data, weeks_back=1)
    
    # Calculate trends
    trends = {}
    for category in CRIME_MAPPING.keys():
        current = stats['stats'][category]
        previous = prev_stats['stats'][category]
        if previous > 0:
            delta = current - previous
            percent = round((delta / previous) * 100, 1)
            trends[category] = {'delta': delta, 'percent': percent}
        else:
            trends[category] = {'delta': current, 'percent': 0}
    
    stats['trends'] = trends
    
    # Update templates
    template_dir = 'templates'
    for filename in os.listdir(template_dir):
        if filename.endswith('.html'):
            template_path = os.path.join(template_dir, filename)
            update_template(template_path, stats)
            print(f"Updated {filename}")

if __name__ == '__main__':
    main()