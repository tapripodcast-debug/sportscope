import datetime as dt
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

def fetch_events(country_code, sport_id, start_date, end_date):
    """Fetch one country + sport page. API's `to` date is exclusive."""
    params = {
        "country": country_code.upper(),
        "sport_id": sport_id,
        "from": start_date.isoformat(),
        "to": (end_date + dt.timedelta(days=1)).isoformat(),
        "limit": 100,
    }
    response = requests.get(f"{API_BASE}/events", params=params, timeout=20)
    if response.status_code == 429:
        raise RuntimeError("The free sports-data API quota/rate limit has been reached. Please retry later.")
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        err = payload["error"].get("message", "Unknown API error")
        raise RuntimeError(err)
    return payload.get("data") or [], payload.get("usage") or {}

def event_row(event, sport_name):
    home = event.get("teamHome") or "TBC"
    away = event.get("teamAway") or "TBC"
    start = event.get("startsAt") or event.get("localStartsAt")
    if start:
        try:
            time_label = pd.to_datetime(start, utc=True).strftime("%d %b %Y, %H:%M UTC")
        except Exception:
            time_label = str(start)
    else:
        time_label = "TBC"
    return {
        "Event name": f"{home} vs {away}",
        "Opponent": away if away != "TBC" else "TBC",
        "Series / tournament": event.get("tournament") or "TBC",
        "Time": time_label,
        "Venue": event.get("location") or "TBC",
        "Broadcast / OTT": "Not supplied by this data source",
        "_id": event.get("id"),
        "_sport": sport_name,
        "_raw": event,
    }

st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
[data-testid="stMetric"] {background: rgba(128,128,128,.08); padding: 12px; border-radius: 12px;}
.small-muted {color: #8b8b8b; font-size: .85rem;}
</style>
""", unsafe_allow_html=True)

st.title("🏟️ SPORT SCOPE")
st.caption("Global sporting-event discovery · Early access MVP")

with st.sidebar:
    st.header("Find sporting events")
    entity_type = st.selectbox("Search by", ["Country", "State", "City", "Team", "Player"])
    if entity_type == "Country":
        entity_name = st.text_input("Country name", "India")
        country_code = st.text_input("2-letter country code", "IN", max_chars=2).upper().strip()
    else:
        entity_name = st.text_input(f"{entity_type} name", "")
        country_code = st.text_input("Country code for event feed (optional)", "IN", max_chars=2).upper().strip()
        st.info("This first data connector currently retrieves country-scoped event feeds. Team/player/state/city-specific participation matching is planned for the next connector release.")
    today = dt.date.today()
    start_date = st.date_input("From", today)
    end_date = st.date_input("To", today + dt.timedelta(days=7))
    selected_sports = st.multiselect("Sports", list(SPORTS.keys()), default=["Football", "Cricket", "Formula 1"] if "Formula 1" in SPORTS else ["Football", "Cricket"])
    run_search = st.button("🔎 Discover events", type="primary", use_container_width=True)

st.markdown("### Your sports intelligence dashboard")
st.write("Choose an entity, date range and sports in the sidebar. Results are grouped automatically by sport.")

if entity_type != "Country":
    st.warning("**Coverage limitation:** the current free connector supports country + sport queries, not verified team/player participation or state/city geofencing. Select Country to run the live event search. The UI already includes the other entity types for the next development phase.")

if start_date > end_date:
    st.error("The start date must be on or before the end date.")
elif run_search:
    if not country_code or len(country_code) != 2 or not country_code.isalpha():
        st.error("Enter a valid two-letter ISO country code, such as IN, GB, US or AU.")
    elif not selected_sports:
        st.warning("Select at least one sport.")
    else:
        # Provider date-window limits: last 7 days through next 30 days.
        min_date = today - dt.timedelta(days=7)
        max_date = today + dt.timedelta(days=30)
        if start_date < min_date or end_date > max_date:
            st.error(f"The current free data connector only supports dates from {min_date:%d %b %Y} through {max_date:%d %b %Y}. The interface will support longer ranges once additional providers are connected.")
        else:
            all_rows = []
            errors = []
            usage_records = []
            progress = st.progress(0, text="Connecting to sports data providers…")
            for i, sport in enumerate(selected_sports):
                if sport not in SPORTS:
                    errors.append(f"{sport}: not yet available in the current data connector.")
                    progress.progress((i + 1) / len(selected_sports), text=f"Checking {sport}…")
                    continue
                try:
                    events, usage = fetch_events(country_code, SPORTS[sport], start_date, end_date)
                    usage_records.append(usage)
                    all_rows.extend([event_row(e, sport) for e in events])
                except Exception as exc:
                    errors.append(f"{sport}: {exc}")
                progress.progress((i + 1) / len(selected_sports), text=f"Checked {sport}")
            progress.empty()

            if errors:
                with st.expander("Data-source notices", expanded=True):
                    for msg in errors:
                        st.warning(msg)

            if not all_rows:
                st.info("No events were returned for this selection. This does not prove that no events exist; coverage depends on the provider's published data.")
            else:
                df = pd.DataFrame(all_rows).drop_duplicates(subset=["_id", "_sport"])
                c1, c2, c3 = st.columns(3)
                c1.metric("Events found", len(df))
                c2.metric("Sports searched", len(selected_sports))
                c3.metric("Country feed", country_code)
                st.success("Live data retrieved. Check each event's details and source coverage before relying on it.")
                for sport in selected_sports:
                    sport_df = df[df["_sport"] == sport]
                    if sport_df.empty:
                        continue
                    st.subheader(f"🏆 {sport}")
                    display = sport_df[["Event name", "Opponent", "Series / tournament", "Time", "Venue", "Broadcast / OTT"]].copy()
                    st.dataframe(display, use_container_width=True, hide_index=True)
                    for _, row in sport_df.iterrows():
                        raw = row["_raw"]
                        label = f"{row['Event name']} · {row['Time']}"
                        with st.expander(label):
                            left, right = st.columns(2)
                            with left:
                                st.write(f"**Tournament:** {raw.get('tournament') or 'TBC'}")
                                st.write(f"**Home:** {raw.get('teamHome') or 'TBC'}")
                                st.write(f"**Away:** {raw.get('teamAway') or 'TBC'}")
                                st.write(f"**Venue:** {raw.get('location') or 'TBC'}")
                            with right:
                                st.write(f"**UTC start:** {raw.get('startsAt') or 'TBC'}")
                                st.write(f"**Local start:** {raw.get('localStartsAt') or 'TBC'}")
                                st.write(f"**Timezone:** {raw.get('timeZone') or 'Not supplied'}")
                                st.write(f"**Updated:** {raw.get('updatedAt') or 'Not supplied'}")
                                st.write(f"**Record ID:** {raw.get('id')}")
                            st.caption("Broadcast information, line-ups and detailed participant profiles are not included in this connector yet.")
                            st.caption("Verification: provider-published record; independent official-source confirmation is not yet implemented.")
                csv = df.drop(columns=["_raw"]).to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download results as CSV", csv, "sportscope_events.csv", "text/csv")
                if usage_records:
                    latest = usage_records[-1]
                    if "requestsRemaining" in latest:
                        st.caption(f"Provider quota remaining (reported): {latest.get('requestsRemaining')} requests today · {latest.get('rowsRemaining')} records this month.")
else:
    st.info("Ready when you are. Try Country = India, country code = IN, and a date range within the next 30 days.")
    st.markdown("#### Current connector coverage")
    st.write("Football, basketball, ice hockey, volleyball, rugby, handball, baseball, American football, cricket, field hockey and several additional sports are available through the initial free feed.")
    st.caption("Formula 1, tennis, badminton and other specialist sports require additional dedicated data connectors.")

st.divider()
st.caption("Sportscope MVP · Data provider: SportsEvents24 open beta. This is an early prototype, not a guarantee of exhaustive global coverage. Always confirm fixtures, venue, time and broadcast details with the organiser or rights holder.")
