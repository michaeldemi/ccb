from __future__ import annotations

from typing import Dict, Iterable, Tuple
from datetime import datetime
from bs4 import BeautifulSoup

from .common import fetch_time_window, filter_york, attrs, bounds, DATA_SOURCE_TEXT

# Label sets normalized to avoid subtle whitespace mismatches
BREAK_ENTER_LABELS: Dict[str, set] = {
    'case_type_pubtrans': {
        'Break and Enter  - Residential',
        'Break and Enter  - Commercial',
    },
    'occ_type': {
        'Break and Enter - Residential',
        'Break and Enter - Commercial',
    },
}


def _in_window(ts: int | None, start_ms: int, end_ms: int) -> bool:
    return isinstance(ts, int) and start_ms <= ts <= end_ms


def count(features: Iterable[dict], start_ms: int, end_ms: int) -> int:
    """
    Count Break & Enter incidents in the given feature collection and time window.
    Uses either case_type_pubtrans or occ_type to match labels.
    """
    total = 0
    for f in features:
        p = attrs(f)
        ts = p.get('rep_date') or p.get('occ_date')
        if not _in_window(ts, start_ms, end_ms):
            continue

        ctp = p.get('case_type_pubtrans')
        ot = p.get('occ_type')
        if (ctp in BREAK_ENTER_LABELS['case_type_pubtrans']) or (ot in BREAK_ENTER_LABELS['occ_type']):
            total += 1
    return total


def fetch_and_count(period: str = "rolling7", weeks_back: int = 0) -> Tuple[int, int, int, int]:
    """
    Fetch York Region features for the given period and return:
    (current_count, prev_count, start_ms, end_ms)
    """
    # Current window
    start_dt, end_dt, start_ms, end_ms = bounds(period, weeks_back)
    features = fetch_time_window(
        start_ms,
        end_ms,
        out_fields='municipality,rep_date,occ_date,case_type_pubtrans,occ_type',
    )
    york = filter_york(features)
    current = count(york, start_ms, end_ms)

    # Previous window (same period length, one block back)
    ps_dt, pe_dt, ps_ms, pe_ms = bounds(period, weeks_back + 1)
    prev_features = fetch_time_window(
        ps_ms,
        pe_ms,
        out_fields='municipality,rep_date,occ_date,case_type_pubtrans,occ_type',
    )
    prev_york = filter_york(prev_features)
    previous = count(prev_york, ps_ms, pe_ms)

    return current, previous, start_ms, end_ms


def update_template(path: str, current_count: int, start_dt: datetime, end_dt: datetime, prev_count: int | None = None) -> None:
    with open(path, 'r', encoding='utf-8') as fh:
        html = fh.read()
    soup = BeautifulSoup(html, 'html.parser')

    ws = start_dt.strftime('%b %d'); we = end_dt.strftime('%b %d')
    rng = soup.find(id='week-range')
    if rng:
        rng.clear()
        rng.append(f"{ws} - {we}")

    # Update data-source
    src = soup.find(id='data-source')
    if src:
        src.clear()
        src.append(DATA_SOURCE_TEXT)

    cnt = soup.find(id='break-enter-count')
    if not cnt:
        cnt = soup.new_tag('span', id='break-enter-count')
        cnt['class'] = 'text-7xl font-extrabold tracking-tight'
        if rng and rng.parent:
            rng.parent.append(cnt)
        else:
            (soup.body or soup).append(cnt)
    cnt.clear()
    cnt.append(str(current_count))

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

        # Toggle trend icon
        trend_chip = tl.parent if tl else None
        icon = trend_chip.find('i') if trend_chip else None
        if icon:
            classes = [c for c in icon.get('class', []) if not c.startswith('ph-trend-')]
            classes.append('ph-trend-up' if delta > 0 else ('ph-trend-down' if delta < 0 else 'ph-arrow-right'))
            icon['class'] = classes

    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(str(soup))


def run(period: str = "rolling7", template_path: str = "templates/break-enter.html") -> None:
    """
    CLI entry for updating the Break & Enter stat card.
    """
    start_dt, end_dt, start_ms, end_ms = bounds(period, 0)
    # Current
    features = filter_york(
        fetch_time_window(
            start_ms,
            end_ms,
            out_fields='municipality,rep_date,occ_date,case_type_pubtrans,occ_type',
        )
    )
    current = count(features, start_ms, end_ms)
    # Previous
    ps_dt, pe_dt, ps_ms, pe_ms = bounds(period, 1)
    prev_features = filter_york(
        fetch_time_window(
            ps_ms,
            pe_ms,
            out_fields='municipality,rep_date,occ_date,case_type_pubtrans,occ_type',
        )
    )
    previous = count(prev_features, ps_ms, pe_ms)

    update_template(template_path, current, start_dt, end_dt, prev_count=previous)