import requests
import json
import streamlit as st
import pandas as pd
import pydeck as pdk


# GET NCT ID

def fetch_latest_trial_summary():
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = {"sort": "LastUpdatePostDate:desc", "pageSize": 1}
    response = requests.get(base_url, params=params)
    response.raise_for_status()

    studies = response.json().get("studies", [])
    if not studies:
        return None

    nct_id = studies[0]["protocolSection"]["identificationModule"]["nctId"]
    detail = requests.get(f"https://clinicaltrials.gov/api/v2/studies/{nct_id}")
    detail.raise_for_status()
    full_study = detail.json()

    return extract_summary(full_study)

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


#MAIN:


#USER INPUT




trial = fetch_latest_trial_summary()
if trial is None:
    st.error("No trials found.")
else:
    #TABLE
    df = pd.DataFrame([{
        "NCT ID": trial["nctId"],
        "Organisation": trial["organisation"],
        "Title": trial["officialTitle"],
        "Last Update": trial["lastUpdateSubmitDate"],
        "Lead Sponsor": trial["leadSponsor"],
        "Conditions": ", ".join(trial["conditions"]),
        "Has Results": trial["hasResults"],
        "Location State": trial["locations"][0]["state"] if trial["locations"] else "",
        "Location Country": trial["locations"][0]["country"] if trial["locations"] else "",
        "Latitude": trial["locations"][0]["lat"] if trial["locations"] else "",
        "Longitude": trial["locations"][0]["lon"] if trial["locations"] else "",
    }])

    df_show = pd.DataFrame([{
        "Last Update": trial["lastUpdateSubmitDate"],
        "Organisation": trial["organisation"],
        "Title": trial["officialTitle"],
        "NCT ID": trial["nctId"],
        "Lead Sponsor": trial["leadSponsor"],
        "Conditions": ", ".join(trial["conditions"]),
        "Has Results": "Yes" if trial["hasResults"] else "No",
        "Location State": trial["locations"][0]["state"] if trial["locations"] else "",
        "Location Country": trial["locations"][0]["country"] if trial["locations"] else "",
    }])
st.subheader("Studies")
st.dataframe(df_show, use_container_width=True, height=150)
#MAP:
location_data = pd.DataFrame([{
    "latitude": loc["lat"],
    "longitude": loc["lon"],
    "organisation": trial["organisation"],
    "title": trial["officialTitle"],
    "state": loc["state"],
    "country": loc["country"]
} for loc in trial["locations"] if loc.get("lat") and loc.get("lon")])

if not location_data.empty:
    st.subheader("Study Location")

    # Set default view to global (zoomed out)
    view_state = pdk.ViewState(
        latitude=0,
        longitude=0,
        zoom=0.5,
        pitch=0
    )

    # Create scatter layer
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
            <b>Organisation:</b> {organisation}<br/>
            <b>Title:</b> {title}<br/>
            <b>State:</b> {state}<br/>
            <b>Country:</b> {country}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
            "fontSize": "12px"
        }
    }

    # Render the map
    st.pydeck_chart(pdk.Deck(
        map_style=None,
        initial_view_state=view_state,
        layers=[layer],
        tooltip=tooltip
        ),
        height=400
    )
else:
    st.info("No location data available for this study.")
