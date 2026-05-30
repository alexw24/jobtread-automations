#!/usr/bin/env python3
"""Download overdue customer invoice PDFs from JobTread API."""

import os
import re
import time
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.jobtread.com/pave"
GRANT_KEY = os.environ["GRANT_KEY"]
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "invoices")


def sanitize(name):
    """Sanitize a string for use as a filename/directory name."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.strip(". ")
    return name or "Unknown"


def api_query(query_body):
    """Make a Pave API query. Wraps query_body in the required envelope."""
    payload = {"query": {"$": {"grantKey": GRANT_KEY}, **query_body}}
    resp = requests.post(API_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp


def fetch_overdue_invoices():
    """Fetch all overdue customer invoices, handling pagination."""
    invoices = []
    page = None
    today = date.today().isoformat()

    while True:
        doc_query = {
            "$": {
                "where": {
                    "and": [
                        {"=": [{"field": "type"}, "customerInvoice"]},
                        {"=": [{"field": "status"}, "pending"]},
                        {"<=": [{"field": "dueDate"}, today]},
                    ]
                },
                "sortBy": [{"field": ["dueDate"], "order": "asc"}],
                "size": 50,
            },
            "nodes": {
                "id": {},
                "name": {},
                "fullName": {},
                "dueDate": {},
                "jobLocationName": {},
                "account": {"name": {}},
            },
            "count": {},
            "nextPage": {},
        }
        if page:
            doc_query["$"]["page"] = page

        resp = api_query({
            "currentGrant": {
                "organization": {
                    "documents": doc_query,
                },
            },
        })
        result = resp.json()
        docs = result["currentGrant"]["organization"]["documents"]
        nodes = docs.get("nodes", [])

        for node in nodes:
            invoices.append({
                "id": node["id"],
                "name": node.get("name", "Unnamed"),
                "fullName": node.get("fullName", ""),
                "dueDate": node.get("dueDate", ""),
                "accountName": (node.get("account") or {}).get("name", "Unknown"),
                "jobLocationName": node.get("jobLocationName", ""),
            })

        page = docs.get("nextPage")
        if not page:
            break

    return invoices


def download_pdf(doc_id, filepath):
    """Generate and download a PDF for a document."""
    resp = api_query({
        "pdf": {
            "$": {
                "id": "document",
                "download": True,
                "options": {"id": doc_id},
            },
        },
    })

    if resp.headers.get("Content-Type", "").startswith("application/pdf"):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(resp.content)
        return True

    print(f"  ERROR: Unexpected response for {doc_id}: {resp.headers.get('Content-Type')}")
    return False


def main():
    print("Fetching overdue customer invoices...")
    invoices = fetch_overdue_invoices()

    if not invoices:
        print("No overdue invoices found.")
        return

    print(f"\nFound {len(invoices)} overdue invoice(s):\n")
    print(f"{'Due Date':<12} {'Account':<30} {'Location':<30} {'Name'}")
    print("-" * 100)
    for inv in invoices:
        print(f"{inv['dueDate']:<12} {inv['accountName']:<30} {inv['jobLocationName']:<30} {inv['name']}")

    print(f"\nPDFs will be saved to: {OUTPUT_DIR}/")
    response = input("\nDownload all PDFs? [y/N] ").strip().lower()
    if response != "y":
        print("Aborted.")
        return

    print()
    success = 0
    for i, inv in enumerate(invoices, 1):
        account_dir = sanitize(inv["accountName"])
        location = sanitize(inv["jobLocationName"]) if inv["jobLocationName"] else ""
        doc_name = sanitize(inv["name"])

        invoice_num = sanitize(inv["fullName"]) if inv["fullName"] else inv["id"][-6:]
        if location:
            filename = f"{invoice_num} {location}.pdf"
        else:
            filename = f"{invoice_num}.pdf"

        filepath = os.path.join(OUTPUT_DIR, account_dir, filename)
        print(f"[{i}/{len(invoices)}] {inv['name']}...", end=" ", flush=True)

        try:
            if download_pdf(inv["id"], filepath):
                print("OK")
                success += 1
            if i < len(invoices):
                time.sleep(0.5)
        except Exception as e:
            print(f"FAILED: {e}")

    print(f"\nDone. {success}/{len(invoices)} PDFs downloaded to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
