#!/usr/bin/env python3
"""Natural language query engine for parsing and executing JobTread dispatch commands."""

import re
import os
import sys
from dotenv import load_dotenv

# Absolute path configurations
dotenv_path = "/home/hermes/developer/JobTread API/.env"
load_dotenv(dotenv_path)

sys.path.insert(0, "/home/hermes/developer/JobTread API")
from jobtread import JobTreadClient

# Global constants for Gentry catalog mappings
COMMERCIAL_PLUMBING_TEMPLATE_ID = "22PAMCi89eGX" # "Commercial Plumbing Service" template ID

class JobTreadNLPEngine:
    """Interprets natural plumbing expressions into valid API transactions."""

    def __init__(self):
        self.client = JobTreadClient()

    def parse_and_apply(self, job_id, prompt):
        """Parse natural language command and apply to selected Job's budget.
        
        Examples:
            "Commercial Plumbing Service with $210 materials my cost, 75% markup"
            "Commercial Plumbing Service with $40 material my cost and 3 hrs labor"
        """
        print(f"Parsing prompt: '{prompt}'...")
        
        # 1. Clean the prompt
        prompt_clean = prompt.strip()
        
        # 2. Extract "my cost" materials overrides
        # Match pattern like: "$40 material my cost", "$210 materials my cost" or just "$210 my cost"
        my_cost_match = re.search(r'\$?([0-9.]+)\s*(?:materials?|fittings?)?\s*(?:my\s*cost)', prompt_clean, re.IGNORECASE)
        materials_cost = None
        materials_price = None
        materials_qty = None
        materials_markup = None
        
        if my_cost_match:
            materials_cost = float(my_cost_match.group(1))
            materials_qty = 1
            print(f"--> Found Override: Materials 'my cost' = ${materials_cost:.2f} (qty = 1). Price auto-calculates.")
            
        # 3. Extract custom markup percentage if specified
        # Match pattern like: "75% markup", "50% markup"
        markup_match = re.search(r'([0-9.]+)\s*%\s*markup', prompt_clean, re.IGNORECASE)
        if markup_match:
            materials_markup = float(markup_match.group(1))
            print(f"--> Found Custom Markup Override: {materials_markup}%")
            
        # 4. Extract "their cost" materials overrides
        # Match pattern like: "$120 material their cost", "$200 materials their cost"
        their_cost_match = re.search(r'\$?([0-9.]+)\s*(?:materials?|fittings?)?\s*(?:their\s*cost)', prompt_clean, re.IGNORECASE)
        if their_cost_match:
            materials_price = float(their_cost_match.group(1))
            materials_qty = 1
            print(f"--> Found Override: Materials 'their cost' = ${materials_price:.2f} (qty = 1).")
            
        # 5. Extract labor hours overrides
        # Matches patterns like: "3.5 hrs", "5 labor hours", "2 hours"
        labor_match = re.search(r'([0-9.]+)\s*(?:hrs?|hours?|labor\s*hours?|labor)', prompt_clean, re.IGNORECASE)
        labor_qty = None
        if labor_match:
            labor_qty = float(labor_match.group(1))
            print(f"--> Found Override: Labor Hours = {labor_qty} hours")
            
        # 6. Extract category/template name (Default to Commercial Plumbing Service)
        template_id = COMMERCIAL_PLUMBING_TEMPLATE_ID
        template_name = "Commercial Plumbing Service"
        
        # Overrides could support detecting other templates (Commercial Drain Service etc.) in the future
        if "drain" in prompt_clean.lower():
            template_id = "22PAVPnubEG3" # the Clear blockage template ID!
            template_name = "Commercial Drain Service - Clear blockage"
            print(f"--> Detected Cost Group Template: '{template_name}'")
        else:
            print(f"--> Defaulting to Cost Group Template: '{template_name}'")
            
        # 7. Apply to customer's job budget dynamically
        print("\nProcessing database replication via JobTread SDK...")
        result = self.client.add_cost_group_from_template(
            job_id=job_id,
            template_group_id=template_id,
            description_override=f"Instantiated from dispatch trigger: '{prompt_clean}'",
            materials_qty=materials_qty,
            materials_unit_cost=materials_cost,
            materials_unit_price=materials_price,
            materials_markup=materials_markup,
            labor_qty=labor_qty
        )
        
        # 8. Query resulting values to output calculated states!
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
                            "isTaxable": {}
                        }
                    }
                }
            }
        }
        res_verify = self.client.query(q_verify)
        items = res_verify["currentGrant"]["organization"]["costItems"]["nodes"]
        
        print(f"\n[Success] Created cost group: '{result['costGroup']['name']}'")
        print(f"{'Item Name':<30} {'Qty':<10} {'Cost':<10} {'Customer Price':<10} {'Taxable'}")
        print("-" * 75)
        for it in items:
            cost_str = f"${it['unitCost']:.2f}" if it.get("unitCost") is not None else "Dynamic"
            price_str = f"${it['unitPrice']:.2f}" if it.get("unitPrice") is not None else "Dynamic"
            print(f"{it['name']:<30} {it['quantity']:<10} {cost_str:<10} {price_str:<10} {it['isTaxable']}")
            
        return result

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 jobtread_parser.py <job_id> \"<natural language command>\"")
        sys.exit(1)
        
    job_id = sys.argv[1]
    prompt = sys.argv[2]
    
    engine = JobTreadNLPEngine()
    engine.parse_and_apply(job_id, prompt)

if __name__ == "__main__":
    main()
