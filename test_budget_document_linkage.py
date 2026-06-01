#!/usr/bin/env python3
"""Unit test for the budget -> document linkage in JobTreadClient.create_document_from_template.

Verifies (with a fully mocked `query`, zero network) that:
  1. The budget is built on the JOB (createCostGroup with jobId, no documentId) and its items
     are NOT pre-linked (budget items have no jobCostItemId).
  2. The document's line items mirror the budget tree and each cost item carries
     jobCostItemId = its BUDGET item's id (not the catalog item id) — the linkage that keeps
     estimated (budget) and approved (document) prices counted once.
  3. The template's payment schedule (scheduledDocuments) is copied onto the document.
"""

import os
import sys
import unittest

sys.path.insert(0, "/home/hermes/developer/JobTread API")
os.environ.setdefault("GRANT_KEY", "test-key")
from jobtread import JobTreadClient

# Ids used across the mock catalog and budget trees
PKG = "catalogPkg1"                 # catalog package (template) group id
CAT_ITEM1, CAT_ITEM2 = "catItem1", "catItem2"
BUDGET_GRP = "budgetGrp1"          # top budget group returned by createCostGroup
BUD_ITEM1, BUD_ITEM2 = "budItem1", "budItem2"   # budget item ids (the link targets)
OCI1, OCI2 = "orgItem1", "orgItem2"
CT, CC = "costType1", "costCode1"


def _tree(root_id, child_id, item1_id, item2_id):
    """A costGroups query response: root group + one nested child + one item in each."""
    node = lambda gid, name, parent=None: {
        "id": gid, "name": name, "description": None,
        "isSelected": False, "isSimpleSelection": False,
        "quantity": 1, "quantityFormula": None,
        "showChildren": True, "showChildCosts": True,
        "showChildDeltas": False, "showDescription": True,
        "minSelectionsRequired": None, "maxSelectionsAllowed": None,
        "files": {"nodes": []},
        **({"parentCostGroup": {"id": parent}} if parent is not None else {}),
    }
    item = lambda iid, name, gid, oci: {
        "id": iid, "name": name, "description": None,
        "costGroup": {"id": gid},
        "costType": {"id": CT}, "costCode": {"id": CC},
        "quantity": 1, "quantityFormula": None,
        "unitCost": 100, "unitCostFormula": None,
        "unitPrice": 200, "unitPriceFormula": None,
        "isTaxable": True, "isSelected": False,
        "files": {"nodes": []},
        "organizationCostItem": {"id": oci, "unitCost": 100, "unitCostFormula": None,
                                 "unitPrice": 200, "unitPriceFormula": None},
    }
    root = node(root_id, "Whole House Filtration")
    root["descendentCostGroups"] = {"nodes": [node(child_id, "Pre-Filter", parent=root_id)]}
    root["descendentCostItems"] = {"nodes": [
        item(item1_id, "Green Fusion 1500", root_id, OCI1),
        item(item2_id, "Pre Filter Material", child_id, OCI2),
    ]}
    return {"currentGrant": {"organization": {"costGroups": {"nodes": [root]}}}}


DOC_TMPL = {"currentGrant": {"organization": {
    "documentTemplates": {"nodes": [{
        "id": "tmpl1", "name": "Water Treatment Proposal", "type": "customerOrder",
        "fromName": "Gentry", "dueDays": 30, "requireSignature": True,
        "showScheduledDocuments": True,
        "scheduledDocuments": {"nodes": [
            {"id": "sd1", "name": "Deposit: due upon signing", "amount": None,
             "percentage": 0.3, "sendOnCreation": True, "createFromDocumentTemplate": {"id": "depTmpl"}},
            {"id": "sd2", "name": "Due upon completion", "amount": None,
             "percentage": None, "sendOnCreation": False, "createFromDocumentTemplate": None},
        ]},
    }]},
    "jobs": {"nodes": [{"location": {"name": "Site", "address": "123 St", "account": {
        "id": "acc1", "name": "Kevin Warsh (1654)",
        "primaryContact": {"customFieldValues": {"nodes": []}},
        "primaryLocation": {"address": "123 St"}}}}]},
}}}


def collect_items(line_items):
    """Recursively collect all costItem entries from a createDocument lineItems list."""
    items = []
    for li in line_items:
        if li.get("_type") == "costItem":
            items.append(li)
        elif li.get("_type") == "costGroup":
            items.extend(collect_items(li.get("lineItems", [])))
    return items


class TestBudgetDocumentLinkage(unittest.TestCase):
    def test_document_items_link_to_budget_items(self):
        client = JobTreadClient()
        self.calls = []

        def fake_query(body):
            self.calls.append(body)
            if "createCostGroup" in body:
                return {"createCostGroup": {"createdCostGroup": {"id": BUDGET_GRP, "name": "Whole House Filtration"}}}
            if "createDocument" in body:
                return {"createDocument": {"createdDocument": {"id": "doc1", "name": "Water Treatment Proposal", "type": "customerOrder"}}}
            org = body.get("currentGrant", {}).get("organization", {})
            if "documentTemplates" in org:
                return DOC_TMPL
            if "costGroups" in org:
                gid = org["costGroups"]["$"]["where"]["="][1]
                if gid == PKG:        # phase 1: read the catalog package
                    return _tree(PKG, "catChild", CAT_ITEM1, CAT_ITEM2)
                if gid == BUDGET_GRP:  # phase 2: read the budget back
                    return _tree(BUDGET_GRP, "budChild", BUD_ITEM1, BUD_ITEM2)
            raise AssertionError("unexpected query: " + str(body)[:160])

        client.query = fake_query
        doc = client.create_document_from_template("job1", "tmpl1", package_template_ids=[PKG])
        self.assertEqual(doc["id"], "doc1")

        # 1. Budget built on the JOB, items NOT pre-linked
        ccg = [c["createCostGroup"]["$"] for c in self.calls if "createCostGroup" in c]
        self.assertEqual(len(ccg), 1)
        self.assertEqual(ccg[0]["jobId"], "job1")
        self.assertNotIn("documentId", ccg[0])
        budget_items = collect_items(ccg[0]["lineItems"])
        self.assertEqual(len(budget_items), 2)
        for it in budget_items:
            self.assertNotIn("jobCostItemId", it, "budget items must not carry jobCostItemId")
        print("--> Budget built on job (jobId, no documentId); budget items unlinked. OK")

        # 2. Document items mirror the budget and link via jobCostItemId = BUDGET item ids
        cd = [c["createDocument"]["$"] for c in self.calls if "createDocument" in c][0]
        self.assertTrue(cd["includeInBudget"])
        doc_items = collect_items(cd["lineItems"])
        self.assertEqual(len(doc_items), 2)
        linked = {it["jobCostItemId"] for it in doc_items}
        self.assertEqual(linked, {BUD_ITEM1, BUD_ITEM2}, "doc items must link to BUDGET item ids")
        self.assertNotIn(CAT_ITEM1, linked, "must link to budget, not catalog, items")
        self.assertNotIn(CAT_ITEM2, linked)
        print("--> Every document item linked to its budget item via jobCostItemId. OK")

        # 3. Payment schedule copied from the template
        sched = cd["scheduledDocuments"]
        self.assertEqual(len(sched), 2)
        self.assertEqual(sched[0]["name"], "Deposit: due upon signing")
        self.assertEqual(sched[0]["percentage"], 0.3)
        self.assertEqual(sched[0]["createFromDocumentTemplateId"], "depTmpl")
        self.assertEqual(sched[1]["name"], "Due upon completion")
        self.assertNotIn("percentage", sched[1])   # no percentage/amount set on the balance row
        print("--> Payment schedule (deposit + remaining) copied from template. OK")


if __name__ == "__main__":
    unittest.main()
