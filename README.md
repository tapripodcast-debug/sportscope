# Sportscope — MVP starter

A Streamlit web app for sport-wise event discovery using a free public sports-data feed.

## 1) Run locally

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501).

## 2) First test

- Search by: Country
- Country name: India
- Country code: IN
- Choose a date range within the last 7 days / next 30 days
- Select Cricket and Football
- Click Discover events

Use ISO 3166-1 alpha-2 country codes: IN, GB, US, AU, etc.

## 3) Deploy free

1. Create a GitHub repository and upload `app.py` and `requirements.txt`.
2. Sign in to Streamlit Community Cloud.
3. Select **Create app**, choose your repository and `app.py`.
4. Deploy.

Streamlit Community Cloud is free, but apps may sleep after inactivity and have resource limits.

## 4) Current MVP boundaries

This version is intentionally honest about provider coverage:
- The initial API supports a country + sport query, not guaranteed national-team participation matching.
- Its published date window is from 7 days in the past to 30 days ahead; the app enforces this.
- It has a free anonymous allowance of 100 data requests/day, 10 requests/minute, and 5,000 returned rows/month per observed IP.
- The feed supplies event/tournament, teams, scheduled times, venue/location, and update timestamps.
- It does not supply broadcast/OTT information or external official-source links.
- State/city/team/player-specific search, F1, tennis, badminton, broadcast rights, event verification and full clickable participant profiles are future connectors.

## 5) Planned next releases

1. Add provider adapters (TheSportsDB, API-Sports and sport-specific feeds).
2. Add entity resolution for national teams, clubs, cities, states and athletes.
3. Add official-source verification and duplicate reconciliation.
4. Add broadcast/OTT lookup by viewer country.
5. Add event, team and athlete detail pages.
6. Add persistent database and scheduled refreshes.

## Data-source documentation

- SportsEvents24 API: https://sportsevents24.com/api
- OpenAPI schema: https://sportsevents24.com/api/openapi.json
- Streamlit Community Cloud: https://docs.streamlit.io/deploy/streamlit-community-cloud
