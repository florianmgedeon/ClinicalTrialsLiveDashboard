import requests
import json


# GET NCT ID

base_url = "https://clinicaltrials.gov/api/v2/studies"
params = {
    "sort": "LastUpdatePostDate:desc",
    "pageSize": 1
}

response = requests.get(base_url, params=params)
response.raise_for_status()

studies = response.json().get("studies", [])
if not studies:
    raise ValueError("No studies returned!")

nct_id = studies[0]["protocolSection"]["identificationModule"]["nctId"]
print(f"Most recently updated study: NCT ID = {nct_id}")


# GET FULL STUDY DETAILS

detail_url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"

detail_response = requests.get(detail_url)
detail_response.raise_for_status()

full_study = detail_response.json()


# PRINT

print("\n=== FULL STUDY DATA ===\n")
print(json.dumps(full_study, indent=2))
