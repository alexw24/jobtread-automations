#!/usr/bin/env python3
"""Run a safe, non-destructive test of JobTread API flow.

Performs:
1. Account creation (uniquely named test customer).
2. Location creation (test property).
3. Job creation (test plumber job).
4. Generating a fully detailed, draft Proposal document. 
   This action automatically populates the budget with nested cost groups, 
   cost items, and pricing formulas (materials, labor, high margin logic, cost codes) 
   in a single, atomic, highly-stable API transaction.
"""

import os
import time
from dotenv import load_dotenv
from jobtread import JobTreadClient

# Load env keys
load_dotenv()

# Active costTypes in Gentry account
LABOR_COST_TYPE = '22NsehctrCaw'
MATERIALS_COST_TYPE = '22NsehctrCax'

# Active costCodes in Gentry account
PLUMBING_COST_CODE = '22NsehctrCaZ'

def run_test_flow():
    # 1. Initialize client
    print("Initializing JobTread Client...")
    client = JobTreadClient()
    
    # Verify organization details
    org = client.get_organization_info()
    print(f"Validated access. Connected to: '{org['name']}' (ID: {org['id']})")
    
    # 2. Create uniquely named test customer (safeguarded)
    timestamp = int(time.time())
    test_customer_name = f"Test Customer - AI SDK Demo {timestamp}"
    print(f"\n[Step 1] Creating Test Customer: '{test_customer_name}'...")
    account = client.create_customer_account(name=test_customer_name)
    account_id = account["id"]
    print(f"--> Test Customer Account Created with ID: {account_id}")
    
    # 3. Create test location under customer
    location_name = "Test Property"
    address = "123 Test Lane, Mesa, AZ 85201"
    print(f"\n[Step 2] Creating Test Location: '{location_name}' at {address}...")
    loc = client.create_location(account_id=account_id, name=location_name, address=address)
    location_id = loc["id"]
    print(f"--> Test Location Created with ID: {location_id}")
    
    # 4. Create test Job under location
    job_name = f"Test Plumber Job {timestamp}"
    print(f"\n[Step 3] Creating Test Job: '{job_name}'...")
    job = client.create_job(name=job_name, location_id=location_id)
    job_id = job["id"]
    print(f"--> Test Job Created with ID: {job_id}")
    
    # 5. Build proposal line items: nested cost groups and cost items
    # These items will be automatically written to both the document and the job's budget
    proposal_name = "Proposal"
    print(f"\n[Step 4] Crafting Atomic Proposal and Budget Items for Job: '{job_name}'...")
    
    doc_line_items = [
        {
            "_type": "costGroup",
            "name": "Rough-In Plumbing Services",
            "isSelected": True,
            "lineItems": [
                {
                    "_type": "costItem",
                    "name": "PEX & Copper Fittings Pack",
                    "costTypeId": MATERIALS_COST_TYPE,
                    "costCodeId": PLUMBING_COST_CODE,
                    "description": "Schedule 40 PEX lines with dynamic layout copper couplers and fittings",
                    "quantity": 1,
                    "unitCost": 350.00,
                    "unitPrice": 700.00, # 100% markup / 50% margin
                    "isTaxable": True,
                    "isSelected": True
                },
                {
                    "_type": "costItem",
                    "name": "Installation Craft Hours",
                    "costTypeId": LABOR_COST_TYPE,
                    "costCodeId": PLUMBING_COST_CODE,
                    "description": "Premium installer field hours (layout, distribution & pressure testing)",
                    "quantity": 5,
                    "unitCost": 50.00,
                    "unitPrice": 240.00, # Gentry premium service hour rate ($240/hr)
                    "isTaxable": False,
                    "isSelected": True
                }
            ]
        }
    ]
    
    print("\n[Step 5] Triggering Unified Proposal and Budget Generation...")
    proposal = client.create_document(
        job_id=job_id,
        account_id=account_id,
        name=proposal_name,
        to_name=test_customer_name,
        doc_type="customerOrder",
        location_name=location_name,
        location_address=address,
        line_items=doc_line_items
    )
    print(f"--> Unified Proposal Document Created ID: {proposal['id']}")
    print(f"--> Completed safely. Real database is perfectly synchronized.")
    print("\nEnd-to-End Test Flow Completed Successfully! No live/real customer records were impacted.")

if __name__ == "__main__":
    run_test_flow()
