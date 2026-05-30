#!/usr/bin/env python3
"""Validate dynamic, template-driven cost group instantiation from JobTread Catalog."""

import os
import sys
import time
from dotenv import load_dotenv

# Path setup for engine validation
dotenv_path = "/home/hermes/developer/JobTread API/.env"
load_dotenv(dotenv_path)

sys.path.insert(0, "/home/hermes/developer/JobTread API")
from jobtread import JobTreadClient

# Master template ID found dynamically under Gentry's profile:
COMMERCIAL_DRAIN_TEMPLATE_ID = "22PAVPnubEG3" # "Commercial Drain Service - Clear blockage"

def test_dynamic_template_injection():
    print("Initializing JobTread Client...")
    client = JobTreadClient()
    
    # 1. Fetch search customer
    print("Finding valid test customer account...")
    test_accs = client.search_customer_accounts("Test Customer - AI SDK Demo", limit=1)
    if not test_accs:
        print("Creating temporary master test account...")
        acc = client.create_customer_account("Test Customer - Dynamic Catalog Demo")
        account_id = acc["id"]
        loc = client.create_location(account_id, "Test Site", "789 Active Way, Mesa, AZ 85206")
        location_id = loc["id"]
    else:
        account_id = test_accs[0]["id"]
        location_id = test_accs[0]["locations"]["nodes"][0]["id"]
        
    # 2. Build test Job context
    timestamp = int(time.time())
    job_name = f"Service Dispatch {timestamp}"
    print(f"\n[Step 1] Initializing Dispatch Job: '{job_name}'...")
    new_job = client.create_job(name=job_name, location_id=location_id)
    job_id = new_job["id"]
    print(f"--> Job Successfully Allocated (ID: {job_id})")
    
    # 3. Inject Cost Group dynamically copying Gentry's "Commercial Drain Service - Clear blockage" (ID: 22PAVPnubEG3)
    #    Applying specific overrides:
    #    - Custom description at group level
    #    - Materials: quantity = 1, unit_cost = 75.00, unit_price = 150.00
    #    - Labor: quantity = 2.5 hours
    custom_description = (
        f"Snaked employee bathroom main stack back to kitchen drain. "
        f"Pulled grease blockages using mechanical snake. Service dispatch reference #{timestamp}."
    )
    
    print(f"\n[Step 2] Injecting Master Cost Group Template (ID: {COMMERCIAL_DRAIN_TEMPLATE_ID}) into Job Budget...")
    print("Applying Overrides: Labor Hours = 2.5, Materials Qty = 1 ($75 Cost / $150 Price)...")
    
    result = client.add_cost_group_from_template(
        job_id=job_id,
        template_group_id=COMMERCIAL_DRAIN_TEMPLATE_ID,
        description_override=custom_description,
        materials_qty=1,
        materials_unit_cost=75.00,
        materials_unit_price=150.00,
        labor_qty=2.5
    )
    
    # 4. Display Results
    print(f"\n[Success] Cost Group instantiated successfully:")
    print(f"--> Instantiated Cost Group Name: '{result['costGroup']['name']}' (ID: {result['costGroup']['id']})")
    print(f"--> Active Description: {custom_description}\n")
    print(f"{'Instantiated Item Name':<30} {'Code ID':<15} {'Qty':<10} {'Unit Cost':<10} {'Unit Price':<10} {'Taxable'}")
    print("-" * 90)
    
    # Let's query the newly created items explicitly to output their live saved state!
    # This proves the database is updated with accurate overridden numbers.
    q_verify = {
        "currentGrant": {
            "organization": {
                "costItems": {
                    "$": {
                        "where": {"=": [{"field": ["costGroup", "id"]}, result["costGroup"]["id"]]}
                    },
                    "nodes": {
                        "name": {},
                        "quantity": {},
                        "unitCost": {},
                        "unitPrice": {},
                        "isTaxable": {},
                        "costCode": {"id": {}}
                    }
                }
            }
        }
    }
    res_verify = client.query(q_verify)
    saved_items = res_verify["currentGrant"]["organization"]["costItems"]["nodes"]
    
    for item in saved_items:
        cc_id = item["costCode"]["id"] if item.get("costCode") else "None"
        qty = str(item.get("quantity"))
        cost = str(item.get("unitCost"))
        price = str(item.get("unitPrice"))
        print(f"{item['name']:<30} {cc_id:<15} {qty:<10} {cost:<10} {price:<10} {item['isTaxable']}")
        
    print("\nEnd-to-End Dynamic Template Replication Completed Safely & Successfully!")

if __name__ == "__main__":
    test_dynamic_template_injection()
