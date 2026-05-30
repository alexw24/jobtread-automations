#!/usr/bin/env python3
"""Example script searching for existing accounts, fetching associated locations, and preparing job context."""

import os
from dotenv import load_dotenv
from jobtread import JobTreadClient

# Load env configurations
load_dotenv()

def run_lookup_flow():
    client = JobTreadClient()
    
    # 1. Search for customer by keyword
    search_keyword = "La Quinta"
    print(f"Searching customer accounts with query: '{search_keyword}'...")
    matching_accounts = client.search_customer_accounts(name_query=search_keyword, limit=5)
    
    if not matching_accounts:
        print("No matching accounts found.")
        return
        
    print(f"\nFound {len(matching_accounts)} matching customer account(s):\n")
    print(f"{'Account Name':<40} {'Account ID':<15} {'Locations Tracked'}")
    print("-" * 80)
    for acc in matching_accounts:
        locations_list = acc.get("locations", {}).get("nodes", [])
        locations_count = len(locations_list)
        print(f"{acc['name']:<40} {acc['id']:<15} {locations_count} properties")
        
    # 2. Select first account and fetch locations explicitly
    target_account = matching_accounts[0]
    print(f"\nSelecting targeted account for deep-dive lookup: '{target_account['name']}' (ID: {target_account['id']})")
    
    print(f"Fetching properties/locations tied to: '{target_account['name']}'...")
    locations = client.get_account_locations(target_account['id'])
    
    print(f"\nFound {len(locations)} verified properties for this customer:")
    print("-" * 100)
    for i, loc in enumerate(locations, start=1):
        print(f"[{i}] Name:    {loc['name']}")
        print(f"    ID:      {loc['id']}")
        print(f"    Address: {loc['formattedAddress']}")
        print("    " + "."*30)

    # 3. Ready to spawn job context
    print("\n[Readiness Check]")
    print(f"We can programmatically spawn a new plumbing job under Location ID '{locations[0]['id']}' immediately!")
    print("Example invocation: client.create_job(name='Plumbing Repair', location_id='" + locations[0]['id'] + "')")

if __name__ == "__main__":
    run_lookup_flow()
