from bs4 import BeautifulSoup
from .common import fetch_time_window, filter_york, attrs, bounds, DATA_SOURCE_TEXT

AUTO_THEFT_LABELS = {
    'case_type_pubtrans': {'Theft Over $5000 - Vehicle','Theft Under $5000 - Vehicle'},
    'occ_type': {'Theft of Motor Vehicle','Motor Vehicle Theft'}
}

def count(features, start_ms, end_ms):
    c = 0
    for f in features:
        p = attrs(f)
        ts = p.get('rep_date') or p.get('occ_date')
        if ts is None or ts < start_ms or ts > end_ms: continue
        if (p.get('case_type_pubtrans') in AUTO_THEFT_LABELS['case_type_pubtrans']) or \
           (p.get('occ_type') in AUTO_THEFT_LABELS['occ_type']):
            c += 1
    return c

def update_template(path, current_count, start_dt, end_dt, prev_count=None):
    with open(path, 'r', encoding='utf-8') as fh:
        soup = BeautifulSoup(fh.read(), 'html.parser')
    ws, we = start_dt.strftime('%b %d'), end_dt.strftime('%b %d')
    rng = soup.find(id='week-range')
    if rng: rng.clear(); rng.append(f"{ws} - {we}")

    # Update data-source
    src = soup.find(id='data-source')
    if src:
        src.clear()
        src.append(DATA_SOURCE_TEXT)

    cnt = soup.find(id='auto-theft-count')
    if not cnt:
        cnt = soup.new_tag('span', id='auto-theft-count'); cnt['class'] = 'text-7xl font-extrabold tracking-tight'
        (rng.parent if rng and rng.parent else (soup.body or soup)).append(cnt)
    cnt.clear(); cnt.append(str(current_count))
    if prev_count is not None:
        delta = current_count - prev_count
        pct = (delta / prev_count * 100) if prev_count > 0 else (100.0 if current_count > 0 else 0.0)
        tl = soup.find(id='trend-label'); di = soup.find(id='delta-incidents'); dp = soup.find(id='delta-percent')
        if tl: tl.clear(); tl.append('Up vs last week' if delta>0 else ('Down vs last week' if delta<0 else 'Flat vs last week'))
        if di: di.clear(); di.append(f"{'+' if delta>=0 else ''}{delta} incidents")
        if dp: dp.clear(); dp.append(f"(≈{'+' if pct>=0 else ''}{round(pct)}%)")
        # Toggle trend icon
        trend_chip = tl.parent if tl else None
        icon = trend_chip.find('i') if trend_chip else None
        if icon:
            classes = [c for c in icon.get('class', []) if not c.startswith('ph-trend-')]
            classes.append('ph-trend-up' if delta > 0 else ('ph-trend-down' if delta < 0 else 'ph-arrow-right'))
            icon['class'] = classes
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(str(soup))

def run(period="rolling7", template_path="templates/auto-theft.html"):
    start_dt, end_dt, start_ms, end_ms = bounds(period, 0)
    features = filter_york(fetch_time_window(start_ms, end_ms, 'municipality,rep_date,occ_date,case_type_pubtrans,occ_type'))
    current = count(features, start_ms, end_ms)
    ps, pe, psm, pem = bounds(period, 1)
    prev_features = filter_york(fetch_time_window(psm, pem, 'municipality,rep_date,occ_date,case_type_pubtrans,occ_type'))
    previous = count(prev_features, psm, pem)
    update_template(template_path, current, start_dt, end_dt, prev_count=previous)