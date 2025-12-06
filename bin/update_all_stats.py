import os
from stats.auto_theft import run as run_auto
from stats.break_enter import run as run_be
from stats.assaults import run as run_assaults

def main():
    period = os.environ.get('PERIOD', 'rolling7')  # rolling7 | iso_week | last30
    run_auto(period=period, template_path='templates/auto-theft.html')
    run_be(period=period, template_path='templates/break-enter.html')
    run_assaults(period=period, template_path='templates/assaults.html')

if __name__ == '__main__':
    main()