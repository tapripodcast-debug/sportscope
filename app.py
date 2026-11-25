import datetime as dt
import re
import unicodedata
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sportscope", page_icon="🏟️", layout="wide")
API_BASE = "https://sportsevents24.com/api/v1"
SPORTS = {
    "Football": 1, "Basketball": 2, "Ice Hockey": 3, "Volleyball": 4,
    "Rugby": 5, "Handball": 6, "Floorball": 7, "Baseball": 8,
    "American Football": 9, "Cricket": 11, "Field Hockey": 13,
    "Water Polo": 14, "Netball": 20, "Australian Rules Football": 21,
    "Lacrosse": 22, "Inline Hockey": 25, "Futsal": 27, "Softball": 42,
    "Bandy": 66, "Beach Soccer": 68,
}

# Aliases are intentionally explicit: do not infer national representation from venue/country.
COUNTRY_ALIASES = {
    "India": ["India", "India A", "India Women", "India U19", "India U-19", "India U23", "India U-23", "Team India", "Indian National Team"],
    "Australia": ["Australia", "Australia A", "Australia Women", "Australia U19", "Australia U-19"],
    "England": ["England", "England Women", "England U19", "England U-19"],
    "United States": ["United States", "USA", "United States Women", "USA Women"],
    "Brazil": ["Brazil", "Brazil Women", "Brazil U20", "Brazil U-20"],
}


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    return re.sub(r"\s+", " ", value)


def flatten_participants(event):
    """Collect participant names and explicit represented-country metadata from common event shapes."""
    names, represented = [], []
    for key in ("teamHome", "teamAway", "homeTeam", "awayTeam", "participantHome", "participantAway", "playerHome", "playerAway"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            names.append(value.strip())
        elif isinstance(value, dict):
            for nkey in ("name", "title", "displayName"):
                if value.get(nkey):
                    names.append(str(value[nkey]))
                    break
            for ckey in ("representedCountry", "country", "countryName", "area_name", "areaName"):
                if value.get(ckey): represented.append(str(value[ckey]))
            for ckey in ("countryCode", "area_code", "country_code"):
                if value.get(ckey): represented.append(str(value[ckey]))
    for key in ("participants", "competitors", "teams", "players", "subparticipants"):
        values = event.get(key)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str):
                    names.append(item)
                elif isinstance(item, dict):
                    for nkey in ("name", "title", "displayName", "shortName"):
                        if item.get(nkey):
                            names.append(str(item[nkey])); break
                    for ckey in ("representedCountry", "country", "countryName", "area_name", "areaName", "countryCode", "area_code", "country_code"):
                        if item.get(ckey): represented.append(str(item[ckey]))
    # Some providers expose a single event country field. This is not proof of representation;
    # only participant-level country metadata is used for the country search rule.
    return list(dict.fromkeys(names)), list(dict.fromkeys(represented))


def country_participation_match(event, country_name, country_code, aliases):
    names, represented = flatten_participants(event)
    alias_set = {norm(x) for x in aliases if norm(x)} | {norm(country_name)}
    # Team sports: require a participant/team name to match the selected national entity.
    if any(norm(name) in alias_set for name in names):
        return True, "National team participant name matched"
    # Individual sports: require participant-level representation metadata, never event venue country.
    country_tokens = {norm(country_name), norm(country_code)}
    if any(norm(value) in country_tokens for value in represented):
        return True, "Participant's represented-country metadata matched"
    return False, "No participant-level representation match"


def entity_match(event, entity_type, entity_name):
    names, _ = flatten_participants(event)
    target = norm(entity_name)
    if not target:
        return False
    return any(norm(name) == target for name in names)


def fetch_events(country_code, sport_id, start_date, end_date):
    params = {
        "country": country_code.upper(), "sport_id": sport_id,
        "from": start_date.isoformat(), "to": (end_date + dt.timedelta(days=1)).isoformat(), "limit": 100,
    }
    response = requests.get(f"{API_BASE}/events", params=params, timeout=25)
    if response.status_code == 429:
        raise RuntimeError("Free provider quota/rate limit reached (429). Try again later.")
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload["error"].get("message", "Provider error"))
    return payload.get("data") or [], payload.get("usage") or {}


def event_row(event, sport_name, matched_reason, match_aliases):
    home = event.get("teamHome") or event.get("homeTeam") or event.get("playerHome") or "TBC"
    away = event.get("teamAway") or event.get("awayTeam") or event.get("playerAway") or "TBC"
    aliases = {norm(x) for x in match_aliases if norm(x)}
    home_is_selected = norm(home) in aliases
    away_is_selected = norm(away) in aliases
    start = event.get("startsAt") or event.get("localStartsAt")
    try:
        time_label = pd.to_datetime(start, utc=True).strftime("%d %b %Y, %H:%M UTC") if start else "TBC"
    except Exception:
        time_label = str(start or "TBC")
    # Show the opponent relative to the selected country/team/player when side data is available.
    opponent = away if home_is_selected else (home if away_is_selected else (away if str(home).strip() else home))
    return {
        "Event name": f"{home} vs {away}", "Opponent": opponent,
        "Series / tournament": event.get("tournament") or "TBC", "Time": time_label,
        "Venue": event.get("location") or "TBC", "Broadcast / OTT": "Not supplied by current provider",
        "_id": event.get("id"), "_sport": sport_name, "_raw": event, "_match_reason": matched_reason,
    }


st.title("🏟️ SPORT SCOPE")
st.caption("Participation-first sporting-event discovery · MVP v2")

with st.sidebar:
    st.header("Find sporting events")
    entity_type = st.selectbox("Search by", ["Country", "State", "City", "Team", "Player"])
    today = dt.date.today()
    if entity_type == "Country":
        country_name = st.text_input("Country / representation", "India")
        country_code = st.text_input("ISO country code (for provider candidate feed)", "IN", max_chars=2).upper().strip()
        suggested_aliases = COUNTRY_ALIASES.get(country_name, [country_name])
        aliases_text = st.text_area("National-team aliases (one per line)", "\n".join(suggested_aliases), height=115,
                                    help="Names used by event providers for the country's national teams. Add variants such as India Women or India U19.")
        aliases = [x.strip() for x in aliases_text.splitlines() if x.strip()]
    else:
        entity_name = st.text_input(f"Exact {entity_type} name", "")
        country_code = st.text_input("Country code for current candidate feed", "IN", max_chars=2).upper().strip()
        aliases = []
    start_date = st.date_input("From", today)
    end_date = st.date_input("To", today + dt.timedelta(days=7))
    selected_sports = st.multiselect("Sports", list(SPORTS.keys()), default=["Football", "Cricket"])
    run_search = st.button("🔎 Discover participating events", type="primary", use_container_width=True)

st.markdown("### Participation-first results")
st.write("Sportscope now filters event records by the actual participants/represented country. Venue country alone is never treated as proof that the selected country is participating.")

st.warning("**Coverage limitation — important:** the current free SportsEvents24 connector only lets us request events associated with one country + one sport. It does not provide a global participant-search endpoint. This version strictly removes unrelated events from the returned candidate feed, but it can still miss India playing overseas and does not yet provide badminton/tennis/F1 coverage. We must add sport-specific participant/team schedule providers to achieve complete global coverage.")

if start_date > end_date:
    st.error("The start date must be on or before the end date.")
elif run_search:
    if not country_code or len(country_code) != 2 or not country_code.isalpha():
        st.error("Enter a valid two-letter ISO country code, such as IN, GB, US or AU.")
    elif not selected_sports:
        st.warning("Select at least one sport.")
    elif entity_type != "Country" and not entity_name.strip():
        st.warning(f"Enter the {entity_type.lower()} name you want to track.")
    else:
        min_date, max_date = today - dt.timedelta(days=7), today + dt.timedelta(days=30)
        if start_date < min_date or end_date > max_date:
            st.error(f"Current connector date range: {min_date:%d %b %Y} to {max_date:%d %b %Y}. Broader windows require additional providers.")
        else:
            matched_rows, errors, usage_records = [], [], []
            progress = st.progress(0, text="Retrieving candidate events and checking participants…")
            for i, sport in enumerate(selected_sports):
                try:
                    if sport not in SPORTS:
                        raise RuntimeError("No connector for this sport yet.")
                    events, usage = fetch_events(country_code, SPORTS[sport], start_date, end_date)
                    usage_records.append(usage)
                    for event in events:
                        if entity_type == "Country":
                            ok, reason = country_participation_match(event, country_name, country_code, aliases)
                        else:
                            ok = entity_match(event, entity_type, entity_name)
                            reason = f"Exact {entity_type.lower()} participant-name match"
                        if ok:
                            match_aliases = aliases if entity_type == "Country" else [entity_name]
                            matched_rows.append(event_row(event, sport, reason, match_aliases))
                except Exception as exc:
                    errors.append(f"{sport}: {exc}")
                progress.progress((i + 1) / len(selected_sports), text=f"Checked {sport}")
            progress.empty()
            if errors:
                with st.expander("Provider notices", expanded=True):
                    for message in errors: st.warning(message)
            if not matched_rows:
                st.info("No participant-matched events were found in this provider's candidate feed. This is not proof that the country/team/player has no events; the current source has incomplete global and sport coverage.")
            else:
                df = pd.DataFrame(matched_rows).drop_duplicates(subset=["_id", "_sport"])
                c1, c2, c3 = st.columns(3)
                c1.metric("Participant-matched events", len(df))
                c2.metric("Sports checked", len(selected_sports))
                c3.metric("Search entity", country_name if entity_type == "Country" else entity_name)
                st.success("Only participant-matched records from the current candidate feed are shown.")
                for sport in selected_sports:
                    sport_df = df[df["_sport"] == sport]
                    if sport_df.empty: continue
                    st.subheader(f"🏆 {sport}")
                    st.dataframe(sport_df[["Event name", "Opponent", "Series / tournament", "Time", "Venue", "Broadcast / OTT"]], use_container_width=True, hide_index=True)
                    for _, row in sport_df.iterrows():
                        raw = row["_raw"]
                        with st.expander(f"{row['Event name']} · {row['Time']}"):
                            names, represented = flatten_participants(raw)
                            a, b = st.columns(2)
                            with a:
                                st.write(f"**Participants:** {', '.join(names) if names else 'Not supplied'}")
                                st.write(f"**Tournament:** {raw.get('tournament') or 'TBC'}")
                                st.write(f"**Venue:** {raw.get('location') or 'TBC'}")
                            with b:
                                st.write(f"**UTC start:** {raw.get('startsAt') or 'TBC'}")
                                st.write(f"**Last updated:** {raw.get('updatedAt') or 'Not supplied'}")
                                st.write(f"**Match reason:** {row['_match_reason']}")
                                st.write(f"**Participant country metadata:** {', '.join(represented) if represented else 'Not supplied'}")
                            st.caption("Broadcast/OTT and rich team/player profiles require separate data connectors.")
                export = df.drop(columns=["_raw"]).to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download matched events CSV", export, "sportscope_participation_results.csv", "text/csv")
else:
    st.info("Ready. Try India + IN, add national-team aliases, select sports and search. Only records with a participant-level match will be displayed.")
    st.markdown("#### Participation rules")
    st.markdown("- Country: match a national-team participant alias or explicit participant-level represented-country metadata.\n- Team/player: exact participant-name match.\n- Venue country is never enough.\n- Missing participant data means the event is not shown as a confirmed match.")

st.divider()
st.markdown("**Current provider:** [SportsEvents24](https://sportsevents24.com/api) · Free open beta. Its country filter is a candidate-feed filter, not a national-team participation filter. See the coverage warning above.")
st.markdown("**Next connector priorities:** international cricket, football national teams, badminton, tennis, hockey, athletics and motorsport. Each connector must support participant/team schedules or official event rosters before it can contribute verified country results.")
