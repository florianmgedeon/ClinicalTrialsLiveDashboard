import requests
import json
import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import date

# FILTER INFO
def extract_summary(full_study: dict) -> dict:
    ps = full_study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    status = ps.get("statusModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {})
    cond_mod = ps.get("conditionsModule", {})
    loc_mod = ps.get("contactsLocationsModule", {})

    summary = {
        "nctId": ident.get("nctId"),
        "organisation": ident.get("organization", {}).get("fullName"),
        "officialTitle": ident.get("officialTitle"),
        "lastUpdateSubmitDate": status.get("lastUpdateSubmitDate"),
        "leadSponsor": sponsor.get("leadSponsor", {}).get("name"),
        "conditions": cond_mod.get("conditions", []),
        "locations": [],
        "hasResults": full_study.get("hasResults", False),
    }

    for loc in loc_mod.get("locations", []):
        gp = loc.get("geoPoint", {}) or {}
        summary["locations"].append({
            "state": loc.get("state"),
            "country": loc.get("country"),
            "lat": gp.get("lat"),
            "lon": gp.get("lon"),
        })

    return summary

# FETCH TRIALS
def fetch_trials_by_date(start_date: str, max_trials: int):
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    all_trials = []
    params = {
        "query.term": f"AREA[LastUpdatePostDate]RANGE[{start_date},{date.today().strftime('%Y-%m-%d')}]",
        "sort": "LastUpdatePostDate:desc",
        "pageSize": 1
    }

    page_count = 0
    while len(all_trials) < max_trials:
        resp = requests.get(base_url, params=params)
        resp.raise_for_status()
        rr = resp.json()
        studies = rr.get("studies", [])
        if not studies:
            break

        for study in studies:
            nct_id = study["protocolSection"]["identificationModule"]["nctId"]
            detail_resp = requests.get(f"{base_url}/{nct_id}")
            detail_resp.raise_for_status()
            full = detail_resp.json()
            all_trials.append(extract_summary(full))
            if len(all_trials) >= max_trials:
                break

        token = rr.get("nextPageToken")
        if not token:
            break
        params["pageToken"] = token

    return all_trials

# STREAMLIT UI
st.title("Clinical Trials Viewer")

col1, col2 = st.columns([3, 2])
with col1:
    start = st.date_input("Updated after date", value=date.today())
with col2:
    amount = st.number_input("Show up to", min_value=1, max_value=50, value=10, step=1)

if start > date.today():
    st.error("Start date cannot be in the future.")
else:
    trials = fetch_trials_by_date(start.strftime("%Y-%m-%d"), amount)

    if not trials:
        st.warning("No trials found in the selected range.")
    else:
        df_show = pd.DataFrame([{
            "Last Update": t["lastUpdateSubmitDate"],
            "Organisation": t["organisation"],
            "Title": t["officialTitle"],
            "NCT ID": t["nctId"],
            "Lead Sponsor": t["leadSponsor"],
            "Conditions": ", ".join(t["conditions"]),
            #"Has Results": "Yes" if t["hasResults"] else "No",
            "Location State": t["locations"][0]["state"] if t["locations"] else "",
            "Location Country": t["locations"][0]["country"] if t["locations"] else "",
        } for t in trials])

        st.subheader("Studies")
        st.dataframe(df_show, use_container_width=True, height=400)

        location_data = pd.DataFrame([{
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "organisation": t["organisation"],
            "title": t["officialTitle"],
            "state": loc["state"],
            "country": loc["country"]
        } for t in trials for loc in t["locations"] if loc.get("lat") and loc.get("lon")])

        if location_data.empty:
            st.info("No location data available for this study.")
        else:
            st.subheader("Study Locations")
            view_state = pdk.ViewState(latitude=0, longitude=0, zoom=0.5, pitch=0)
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=location_data,
                get_position='[longitude, latitude]',
                get_radius=7,
                radius_units='pixels',
                get_fill_color=[0, 255, 0, 180],
                pickable=True,
                tooltip=True
            )
            tooltip = {
                "html": """
                    <div style='max-width: 250px; word-wrap: break-word;'>
                        <b>Organisation:</b> {organisation}<br/>
                        <b>Title:</b> {title}<br/>
                        <b>State:</b> {state}<br/>
                        <b>Country:</b> {country}
                    </div>
                """,
                "style": {
                    "backgroundColor": "white",
                    "color": "black",
                    "fontSize": "12px",
                    "maxWidth": "250px"
                }
            }

            st.pydeck_chart(pdk.Deck(map_style=None,
                                     initial_view_state=view_state,
                                     layers=[layer],
                                     tooltip=tooltip),
                             height=400)
