# Crime Stats Automation

This project automates the generation of weekly crime statistics posts for social media using data from the York Region Police API.

## Overview

The workflow:
1. Fetches crime incident data from York Region Police ArcGIS API
2. Filters data for York Region municipalities
3. Calculates weekly statistics for assaults, auto-theft, and break-and-enter
4. Updates HTML templates with the latest stats and trends
5. Generates PNG screenshots of the templates
6. Commits changes to GitHub
7. Triggers Make.com webhook for social media posting

## Files

- `fetch_data.py`: Fetches and processes crime data, updates HTML templates
- `screenshot.py`: Generates PNG screenshots from HTML templates using Playwright
- `requirements.txt`: Python dependencies
- `templates/`: HTML templates for different crime types
- `screenshots/`: Generated PNG images (auto-created)
- `.github/workflows/update-stats.yml`: GitHub Actions workflow for automation

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Install Playwright browsers: `playwright install chromium`
4. Install system dependencies: `sudo playwright install-deps`

## Manual Testing

Run the scripts locally:
```bash
python fetch_data.py
python screenshot.py
```

## Make.com Integration

1. Create a new scenario in Make.com
2. Add a "Webhooks" module as the trigger
3. Copy the webhook URL and replace `YOUR_MAKE_WEBHOOK_URL` in `.github/workflows/update-stats.yml`
4. Add modules to download the PNG files from GitHub and post to Facebook/Instagram

## Automation

The workflow runs automatically every Monday at midnight UTC. You can also trigger it manually from the Actions tab in GitHub.

## Data Source

York Region Police Crime Data API: https://gis.yorkmaps.ca/arcgis/rest/services/YorkMaps/OpenData/MapServer/1/query

## Dependencies

- Python 3.9+
- requests
- playwright