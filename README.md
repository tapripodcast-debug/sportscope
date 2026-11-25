# Sportscope MVP v2 — participation-first filtering

## What changed
- Country searches now require a participant/team name alias or participant-level represented-country metadata.
- Team/player searches use exact participant-name matching.
- Event venue/country is never used as proof of participation.
- Added visible warnings explaining that the current SportsEvents24 provider is only a country-scoped candidate feed and cannot guarantee overseas fixtures or all sports.
- Added participant details and match-reason display to event expanders.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy update
Upload the new `app.py` and `requirements.txt` to the existing GitHub repository and commit to `main`. Streamlit Community Cloud should redeploy automatically.

## Known limits (not hidden)
SportsEvents24 accepts `country + sport_id` or `tournament_id`; it does not expose a global participant search endpoint. Its country query can therefore miss a selected country's team playing abroad. The current provider does not cover badminton, tennis, Formula 1 or Formula 2 in its published sport list. The app applies strict participant matching only to records returned by this candidate feed; it is not yet the complete global Sportscope engine.

## Next engineering milestone
Add participant/team schedule connectors with stable IDs and explicit representation metadata. Prioritise sport-specific sources for cricket, football, badminton, tennis, hockey, athletics and motorsport. Keep each source adapter independent, normalize to a common event schema, deduplicate by provider IDs/team/date/tournament, and store source + last-verified timestamp.
