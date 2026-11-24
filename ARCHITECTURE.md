# Sportscope architecture

## Current request flow
Browser -> Streamlit UI -> SportsEvents24 adapter -> normalize events -> group by sport -> tables/detail expanders.

## Target architecture
Frontend (React or Streamlit)
    |
Backend API (FastAPI)
    |
Discovery Orchestrator
    |-- country/competition event providers
    |-- team/player schedule providers
    |-- official federation/organiser source crawlers
    |-- broadcaster/OTT rights lookup by viewer market
    |
Entity resolution + event deduplication + verification
    |
PostgreSQL/Supabase + scheduled refresh jobs

## Canonical event model
- event_id, sport, event_name
- start_time_utc, start_time_local, timezone, timezone_confidence
- venue, city, country
- tournament_id, tournament_name, season
- participants[], teams[]
- selected_entity_ids[]
- broadcast_options[] (market, channel, OTT, source, valid_from, valid_to)
- status (scheduled/provisional/confirmed/postponed/cancelled/result)
- sources[], last_verified_at, provider_updated_at
