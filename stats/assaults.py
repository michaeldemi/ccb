from bs4 import BeautifulSoup
from .common import fetch_time_window, filter_york, attrs, bounds, DATA_SOURCE_TEXT

ASSAULT_LABELS = {
    'case_type_pubtrans': {
        'Assault',
        'Assault with a Weapon',
    },
    'occ_type': {
        'Assaults',
    },
}

def count(features, start_ms, end_ms):
    total = 0
    for f in features:
        p = attrs(f)
        ts = p.get('rep_date') or p.get('occ_date')
        if ts is None or ts < start_ms or ts > end_ms:
            continue
        ctp = p.get('case_type_pubtrans')
        ot = p.get('occ_type')
        if (ctp in ASSAULT_LABELS['case_type_pubtrans']) or (ot in ASSAULT_LABELS['occ_type']):
            total += 1
    return total

def update_template(path, current_count, start_dt, end_dt, prev_count=None):
    with open(path, 'r', encoding='utf-8') as fh:
        soup = BeautifulSoup(fh.read(), 'html.parser')

    ws, we = start_dt.strftime('%b %d'), end_dt.strftime('%b %d')
    rng = soup.find(id='week-range')
    if rng:
        rng.clear()
        rng.append(f"{ws} - {we}")

    # Update data-source
    src = soup.find(id='data-source')
    if src:
        src.clear()
        src.append(DATA_SOURCE_TEXT)

    cnt = soup.find(id='assaults-count')
    if not cnt:
        cnt = soup.new_tag('div', id='assaults-count')
        cnt['class'] = 'text-[450px] leading-none font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-b from-white to-slate-400 drop-shadow-2xl pr-12 pb-4'
        if rng and rng.parent:
            rng.parent.append(cnt)
        else:
            (soup.body or soup).append(cnt)
    cnt.clear()
    cnt.append(str(current_count))

    # Trend/delta
    if prev_count is not None:
        delta = current_count - prev_count
        pct = (delta / prev_count * 100.0) if prev_count > 0 else (100.0 if current_count > 0 else 0.0)

        tl = soup.find(id='trend-label')
        di = soup.find(id='delta-incidents')
        dp = soup.find(id='delta-percent')

        if tl:
            tl.clear()
            tl.append('Up vs last week' if delta > 0 else ('Down vs last week' if delta < 0 else 'Flat vs last week'))
        if di:
            di.clear()
            di.append(f"{'+' if delta >= 0 else ''}{delta} incidents")
        if dp:
            dp.clear()
            dp.append(f"(≈{'+' if pct >= 0 else ''}{round(pct)}%)")

        # Toggle trend icon class
        trend_chip = tl.parent if tl else None
        icon = None
        if trend_chip:
            # find first <i> within the chip
            icon = trend_chip.find('i')
        if icon:
            classes = icon.get('class', [])
            # remove any existing trend classes
            classes = [c for c in classes if not c.startswith('ph-trend-')]
            # add up/down/flat
            if delta > 0:
                classes.append('ph-trend-up')
            elif delta < 0:
                classes.append('ph-trend-down')
            else:
                # optional: use a neutral icon
                classes.append('ph-arrow-right')
            icon['class'] = classes

    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(str(soup))

def run(period="rolling7", template_path="templates/assaults.html"):
    start_dt, end_dt, start_ms, end_ms = bounds(period, 0)
    features = fetch_time_window(
        start_ms, end_ms,
        out_fields='municipality,rep_date,occ_date,case_type_pubtrans,occ_type'
    )
    york = filter_york(features)
    current = count(york, start_ms, end_ms)

    ps_dt, pe_dt, ps_ms, pe_ms = bounds(period, 1)
    prev_features = fetch_time_window(
        ps_ms, pe_ms,
        out_fields='municipality,rep_date,occ_date,case_type_pubtrans,occ_type'
    )
    prev_york = filter_york(prev_features)
    previous = count(prev_york, ps_ms, pe_ms)

    print(f"[assaults] current={current} prev={previous} window={start_dt.date()}..{end_dt.date()} york_current={len(york)} york_prev={len(prev_york)}")
    update_template(template_path, current, start_dt, end_dt, prev_count=previous)
    print(f"[assaults] updated {template_path}")