#!/usr/bin/env python3
"""Automated pipeline for processing JobTread water treatment web form submissions.

Triggers on a new Web Form Submission:
1. Queries the Job details, Custom Field Values, Location details, and Customer Account.
2. Identifies the originating web form and client options.
3. Automatically posts a thank-you comment visible to the customer on the Job.
4. Dynamically instantiates recursively Gentry's nested Selection structures
   from Gentry's master catalog ("Water Treatment" parent ID: 22PCTaQaEeLm).
5. Only copies packages (Whole House, RO, UV) that the client explicitly selected or indicated in web custom fields.
6. Emits internal plumber-intervention warning logs if the loop isn't pre-plumbed.
"""

import os
import sys
import time
from dotenv import load_dotenv

# Absolute path configurations
dotenv_path = "/home/hermes/developer/JobTread API/.env"
load_dotenv(dotenv_path)

sys.path.insert(0, "/home/hermes/developer/JobTread API")
from jobtread import JobTreadClient

# Master Catalog Package IDs (recursively copied to preserve interactive Selections)
PKGP_WHOLE_HOUSE_FILTRATION_ID = "22PCTaQaFm3e"  # Whole House Filtration package
PKGP_REVERSE_OSMOSIS_ID = "22PCTepJxrY9"         # Reverse Osmosis package
PKGP_UV_FILTER_ID = "22PCTepJxrYC"               # UV Filter package

# Document Template ID
WATER_TREATMENT_PROPOSAL_TEMPLATE_ID = "22PXgxgqnh27"

# Custom Field ID Mappings
CF_ORIGIN_PAGE_ID = "22PXggf2y4NV"     # Account Custom: (Web form) originating page
CF_SOFTENER_LOOP_ID = "22PV9jLYfUip"   # Location Custom: Pre-plumbed softener loop?
CF_ADDONS_ID = "22PV7qnEkJSj"          # Job Custom: Water Softener Addons (multipick list)
CF_GOALS_ID = "22PV9iPYXdgk"           # Job Custom: What are your goals? (multipick list)
CF_CURRENT_EQUIP_ID = "22PV6UdqHxx6"   # Location Custom: Current equipment
CF_BATHROOMS_ID = "22PV6UW62Cyx"       # Location Custom: Number of bathrooms

COLLAPSE_CHILDREN_GROUPS = {
    "Softener and Carbon Filter",
    "Pre-Filter",
    "Reverse Osmosis without remineralization",
    "Reverse Osmosis with Automatic Remineralization",
}


class WaterTreatmentAutomator:
    """Orchestrates dynamic budget building and messaging on new water form submissions."""

    def __init__(self):
        self.client = JobTreadClient()

    def process_submission(self, job_id):
        print(f"=== Starting Automation Pipeline for Job ID: {job_id} ===")
        
        # 1. Query Job details and Custom Field Values
        print("Fetching Job, Location, and Account custom demographics...")
        q = {
            "currentGrant": {
                "organization": {
                    "jobs": {
                        "$": {
                            "where": {"=": [{"field": "id"}, job_id]}
                        },
                        "nodes": {
                            "id": {},
                            "name": {},
                            "customFieldValues": {
                                "nodes": {
                                    "value": {},
                                    "customField": {"id": {}, "name": {}}
                                }
                            },
                            "location": {
                                "id": {},
                                "name": {},
                                "customFieldValues": {
                                    "nodes": {
                                        "value": {},
                                        "customField": {"id": {}, "name": {}}
                                    }
                                },
                                "account": {
                                    "id": {},
                                    "name": {},
                                    "customFieldValues": {
                                        "nodes": {
                                            "value": {},
                                            "customField": {"id": {}, "name": {}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        res = self.client.query(q)
        jobs_nodes = res["currentGrant"]["organization"]["jobs"]["nodes"]
        if not jobs_nodes:
            raise ValueError(f"Job ID '{job_id}' not found inside Organization.")
            
        job_node = jobs_nodes[0]
        location_node = job_node["location"]
        account_node = location_node["account"]
        
        # 2. Extract values from Custom Fields Arrays
        job_customs = {node["customField"]["id"]: node["value"] for node in job_node["customFieldValues"]["nodes"]}
        loc_customs = {node["customField"]["id"]: node["value"] for node in location_node["customFieldValues"]["nodes"]}
        acc_customs = {node["customField"]["id"]: node["value"] for node in account_node["customFieldValues"]["nodes"]}
        
        # Extract originating page
        origin_page = acc_customs.get(CF_ORIGIN_PAGE_ID, "")
        print(f"--> Custom Origin Page: '{origin_page}'")
        
        # Extract Loop status
        pre_plumbed_loop = loc_customs.get(CF_SOFTENER_LOOP_ID, None)
        print(f"--> Pre-Plumbed Softener Loop Status: '{pre_plumbed_loop}'")
        
        # Extract goals and addons arrays (multipicks are returned as string or arrays in form parsing)
        addons = job_customs.get(CF_ADDONS_ID, [])
        if isinstance(addons, str):
            addons = [addons]
        print(f"--> Selected Addons: {addons}")
        
        goals = job_customs.get(CF_GOALS_ID, [])
        if isinstance(goals, str):
            goals = [goals]
        print(f"--> Selected Goals: {goals}")
        
        current_equip = loc_customs.get(CF_CURRENT_EQUIP_ID, [])
        if isinstance(current_equip, str):
            current_equip = [current_equip]
        print(f"--> Current Equipment: {current_equip}")

        bathrooms = loc_customs.get(CF_BATHROOMS_ID, "")
        print(f"--> Number of Bathrooms: '{bathrooms}'")

        # 3. Post Customer-Facing Thank you message
        print("\nSending automated Gentry customer reply comment...")
        client_name = account_node["name"].split(" (")[0]  # strip temp indicators
        
        # Resolve user friendly form name from technical origin_page identifier
        form_name = "Water Treatment"
        if origin_page == "water-softener":
            form_name = "Water Softener"
        elif origin_page == "reverse-osmosis":
            form_name = "Reverse Osmosis"
        elif origin_page == "whole-home-filtration":
            form_name = "Whole-Home Water Filtration"
            
        customer_msg = f"Hi {client_name}! Thank you for filling out our {form_name} form. We're reviewing your submission and writing your quote now."
        payload_msg = {
            "createComment": {
                "$": {
                    "targetId": job_id,
                    "targetType": "job",
                    "message": customer_msg,
                    "isVisibleToCustomerRoles": True
                }
            }
        }
        self.client.query(payload_msg)
        print("--> Thank-you message delivered to customer on Job Timeline successfully!")

        # 4. Pull only the packages the customer selected / requested
        print("\nEvaluating client submissions to pull relevant packages...")
        packages_to_copy = []

        # A. Whole House Filtration Package
        wh_opt_selected = (origin_page == "water-softener" or origin_page == "whole-home-filtration")
        wh_upsell = False
        for gl in goals:
            gl_low = gl.lower()
            if "soften" in gl_low or "filtration in the whole house" in gl_low:
                wh_upsell = True
        if wh_opt_selected or wh_upsell:
            packages_to_copy.append(PKGP_WHOLE_HOUSE_FILTRATION_ID)
            print("Action: Pulling Whole House Filtration Tree (GF-1500 + Pre-filters)")

        # B. Reverse Osmosis Package
        ro_opt_selected = (origin_page == "reverse-osmosis" or origin_page == "whole-home-filtration")
        ro_upsell = False
        for gl in goals:
            gl_low = gl.lower()
            if "top quality drinkable" in gl_low or "drinking water" in gl_low or "quality drinkable" in gl_low:
                ro_upsell = True
        if ro_opt_selected or ro_upsell:
            packages_to_copy.append(PKGP_REVERSE_OSMOSIS_ID)
            print("Action: Pulling Reverse Osmosis Tree (with and without remineralization options)")

        # C. UV Filter Package
        uv_opt_selected = False  # addon-only; never triggered by origin page alone
        addon_uv = False
        for ad in addons:
            if "uv filter" in ad.lower():
                addon_uv = True
        if uv_opt_selected or addon_uv:
            packages_to_copy.append(PKGP_UV_FILTER_ID)
            print("Action: Pulling UV Filter Tree")

        # 5. Create Water Treatment Proposal document with packages as inline line items.
        #    includeInBudget=True means the document IS the budget — no separate budget step needed.
        print(f"\nCreating Water Treatment Proposal with {len(packages_to_copy)} package(s)...")
        doc = self.client.create_document_from_template(
            job_id,
            WATER_TREATMENT_PROPOSAL_TEMPLATE_ID,
            package_template_ids=packages_to_copy,
            collapse_group_names=COLLAPSE_CHILDREN_GROUPS
        )
        print(f"--> Proposal '{doc['name']}' (ID: {doc['id']}) created — budget and document populated atomically!")

        # 6. Post Internal plumber-warning if pre-plumb status requires manual loop building
        if pre_plumbed_loop == "No" or pre_plumbed_loop is False:
            print("\n⚠️ Loop pre-plumb status is 'No' (or false). Manual intervention required!")
            alert_msg = (
                "⚠️ Crew Alert: CUSTOMER SELECTED NO SOFTENER LOOP PRE-PLUMB!\n\n"
                "Requires manual loop installation. Please edit the budget manually to insert "
                "additional loop building materials and plumbing installation labor hours."
            )
            payload_alert = {
                "createComment": {
                    "$": {
                        "targetId": job_id,
                        "targetType": "job",
                        "message": alert_msg,
                        "isPinned": True,
                        "isVisibleToInternalRoles": True  # ONLY visible to crew (internal)!
                    }
                }
            }
            self.client.query(payload_alert)
            print("--> Internal pinned plumber alert added to Job timeline successfully!")

        print(f"\n=== Automation complete: {len(packages_to_copy)} packages added to proposal and budget. ===")
        return {"document": doc, "packages": packages_to_copy}

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 water_treatment_automator.py <job_id>")
        sys.exit(1)
        
    job_id = sys.argv[1]
    automator = WaterTreatmentAutomator()
    automator.process_submission(job_id)

if __name__ == "__main__":
    main()
