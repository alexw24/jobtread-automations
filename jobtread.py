#!/usr/bin/env python3
"""JobTread API Client Wrapper.

Provides clean Python-based interaction with the JobTread Pave REST API.
"""

import os
import requests

class JobTreadClient:
    """Client for interacting with the JobTread Pave API."""

    API_URL = "https://api.jobtread.com/pave"

    def __init__(self, grant_key=None, organization_id=None):
        self.grant_key = grant_key or os.environ.get("GRANT_KEY")
        self.organization_id = organization_id or os.environ.get("organizationID")
        if not self.grant_key:
            raise ValueError("grant_key must be provided or set in environment variable GRANT_KEY")

    def query(self, query_body):
        """Execute a raw Pave query request."""
        payload = {
            "query": {
                "$": {
                    "grantKey": self.grant_key
                },
                **query_body
            }
        }
        resp = requests.post(self.API_URL, json=payload, timeout=60)
        # Raise descriptive errors if any
        if resp.status_code != 200:
            raise requests.exceptions.HTTPError(
                f"JobTread API returned status {resp.status_code}: {resp.text}",
                response=resp
            )
        data = resp.json()
        if "errors" in data:
            raise ValueError(f"JobTread API Query Errors: {data['errors']}")
        return data

    def get_organization_info(self):
        """Fetch details of the current organization and grant validation."""
        q = {
            "currentGrant": {
                "organization": {
                    "id": {},
                    "name": {}
                }
            }
        }
        res = self.query(q)
        return res["currentGrant"]["organization"]

    def search_customer_accounts(self, name_query=None, limit=20):
        """Search or query existing customer accounts.
        
        Args:
            name_query (str, optional): Account name query (case-insensitive substring match).
            limit (int, optional): Maximum results to fetch. Default is 20.
        """
        where_val = {"=": [{"field": "type"}, "customer"]}
        if name_query:
            where_val = {
                "and": [
                    {"=": [{"field": "type"}, "customer"]},
                    {"like": [{"field": "name"}, f"%{name_query}%"]}
                ]
            }

        q = {
            "currentGrant": {
                "organization": {
                    "accounts": {
                        "$": {
                            "where": where_val,
                            "sortBy": [{"field": ["createdAt"], "order": "desc"}],
                            "size": limit
                        },
                        "nodes": {
                            "id": {},
                            "name": {},
                            "createdAt": {},
                            "locations": {
                                "nodes": {
                                    "id": {},
                                    "name": {},
                                    "formattedAddress": {}
                                }
                            }
                        }
                    }
                }
            }
        }
        res = self.query(q)
        return res["currentGrant"]["organization"]["accounts"]["nodes"]

    def get_account_locations(self, account_id, limit=20):
        """Query physical locations associated with a specific customer account.
        
        Args:
            account_id (str): The customer account ID.
            limit (int, optional): Maximum locations to fetch. Default is 20.
        """
        q = {
            "currentGrant": {
                "organization": {
                    "locations": {
                        "$": {
                            "where": {
                                "=": [{"field": ["account", "id"]}, account_id]
                            },
                            "size": limit
                        },
                        "nodes": {
                            "id": {},
                            "name": {},
                            "formattedAddress": {},
                            "street": {},
                            "city": {},
                            "state": {},
                            "postalCode": {}
                        }
                    }
                }
            }
        }
        res = self.query(q)
        return res["currentGrant"]["organization"]["locations"]["nodes"]

    def create_customer_account(self, name, custom_fields=None, is_taxable=True):
        """Create a new customer account in JobTread.
        
        Args:
            name (str): Name of the customer account.
            custom_fields (dict, optional): Custom fields as a dictionary of custom field ID -> value.
            is_taxable (bool, optional): Taxable setting. Defaults to True.
        """
        payload = {
            "createAccount": {
                "$": {
                    "name": name,
                    "type": "customer",
                    "isTaxable": is_taxable,
                    "organizationId": self.organization_id
                },
                "createdAccount": {
                    "id": {},
                    "name": {}
                }
            }
        }
        if custom_fields:
            payload["createAccount"]["$"]["customFieldValues"] = custom_fields
            
        res = self.query(payload)
        return res["createAccount"]["createdAccount"]

    def create_location(self, account_id, name, address=None, custom_fields=None):
        """Create a physical location for a customer account."""
        payload = {
            "createLocation": {
                "$": {
                    "accountId": account_id,
                    "name": name,
                    "address": address
                },
                "createdLocation": {
                    "id": {},
                    "name": {},
                    "formattedAddress": {}
                }
            }
        }
        if custom_fields:
            payload["createLocation"]["$"]["customFieldValues"] = custom_fields
            
        res = self.query(payload)
        return res["createLocation"]["createdLocation"]

    def create_job(self, name, location_id, price_type="fixed", copy_costs_from_job_id=None, custom_fields=None):
        """Create a new job for a customer location."""
        payload = {
            "createJob": {
                "$": {
                    "name": name,
                    "locationId": location_id,
                    "priceType": price_type
                },
                "createdJob": {
                    "id": {},
                    "name": {}
                }
            }
        }
        if copy_costs_from_job_id:
            payload["createJob"]["$"]["copyCostsFromJobId"] = copy_costs_from_job_id
        if custom_fields:
            payload["createJob"]["$"]["customFieldValues"] = custom_fields
            
        res = self.query(payload)
        return res["createJob"]["createdJob"]

    def create_cost_group(self, job_id=None, name=None, description=None, quantity=1, quantity_formula=None,
                          parent_cost_group_id=None, is_selected=None, is_simple_selection=None,
                          min_selections_required=None, max_selections_allowed=None,
                          show_children=None, show_child_costs=None, show_child_deltas=None,
                          show_description=None, document_id=None):
        """Create a nesting cost group under a job budget or document."""
        args = {"name": name, "description": description, "quantity": quantity}
        if document_id:
            args["documentId"] = document_id
        else:
            args["jobId"] = job_id
        payload = {
            "createCostGroup": {
                "$": args,
                "createdCostGroup": {
                    "id": {},
                    "name": {}
                }
            }
        }
        if quantity_formula:
            payload["createCostGroup"]["$"]["quantityFormula"] = quantity_formula
        if parent_cost_group_id:
            payload["createCostGroup"]["$"]["parentCostGroupId"] = parent_cost_group_id
        if is_selected is not None:
            payload["createCostGroup"]["$"]["isSelected"] = is_selected
        if is_simple_selection is not None:
            payload["createCostGroup"]["$"]["isSimpleSelection"] = is_simple_selection
        if min_selections_required is not None:
            payload["createCostGroup"]["$"]["minSelectionsRequired"] = min_selections_required
        if max_selections_allowed is not None:
            payload["createCostGroup"]["$"]["maxSelectionsAllowed"] = max_selections_allowed
        if show_children is not None:
            payload["createCostGroup"]["$"]["showChildren"] = show_children
        if show_child_costs is not None:
            payload["createCostGroup"]["$"]["showChildCosts"] = show_child_costs
        if show_child_deltas is not None:
            payload["createCostGroup"]["$"]["showChildDeltas"] = show_child_deltas
        if show_description is not None:
            payload["createCostGroup"]["$"]["showDescription"] = show_description
            
        res = self.query(payload)
        return res["createCostGroup"]["createdCostGroup"]

    def update_cost_group(self, cost_group_id, show_children=None, show_child_costs=None,
                          show_child_deltas=None, show_description=None, name=None, description=None):
        """Update properties of an existing cost group."""
        args = {"id": cost_group_id}
        if show_children is not None: args["showChildren"] = show_children
        if show_child_costs is not None: args["showChildCosts"] = show_child_costs
        if show_child_deltas is not None: args["showChildDeltas"] = show_child_deltas
        if show_description is not None: args["showDescription"] = show_description
        if name is not None: args["name"] = name
        if description is not None: args["description"] = description
        payload = {"updateCostGroup": {"$": args}}
        self.query(payload)

    def create_cost_item(self, job_id=None, cost_group_id=None, name=None, cost_type_id=None, cost_code_id=None,
                         description=None, quantity=1, quantity_formula=None,
                         unit_cost=None, unit_cost_formula=None,
                         unit_price=None, unit_price_formula=None,
                         is_taxable=True, organization_cost_item_id=None, is_selected=None,
                         document_id=None):
        """Create a cost item under a cost group in a job budget or document."""
        args = {
            "costGroupId": cost_group_id,
            "name": name,
            "costTypeId": cost_type_id,
            "costCodeId": cost_code_id,
            "quantity": quantity,
            "isTaxable": is_taxable
        }
        if document_id:
            args["documentId"] = document_id
        else:
            args["jobId"] = job_id
        payload = {
            "createCostItem": {
                "$": args,
                "createdCostItem": {
                    "id": {},
                    "name": {}
                }
            }
        }
        if description: payload["createCostItem"]["$"]["description"] = description
        if organization_cost_item_id: payload["createCostItem"]["$"]["organizationCostItemId"] = organization_cost_item_id
        if quantity_formula: payload["createCostItem"]["$"]["quantityFormula"] = quantity_formula
        if is_selected is not None: payload["createCostItem"]["$"]["isSelected"] = is_selected
        
        # Saphire pricing logic: only pass numeric values if they are explicitly overridden!
        if unit_cost is not None: payload["createCostItem"]["$"]["unitCost"] = unit_cost
        if unit_price is not None: payload["createCostItem"]["$"]["unitPrice"] = unit_price
        
        # Always propagate formulas if present!
        if unit_cost_formula: payload["createCostItem"]["$"]["unitCostFormula"] = unit_cost_formula
        if unit_price_formula: payload["createCostItem"]["$"]["unitPriceFormula"] = unit_price_formula
            
        res = self.query(payload)
        return res["createCostItem"]["createdCostItem"]

    def create_document(self, job_id, account_id, name, to_name, doc_type="customerOrder", 
                        from_name="Gentry Plumbing & Contracting", tax_rate=0.081, 
                        location_name=None, location_address=None, due_days=30, line_items=None):
        """Create a proposal, proposal template, or invoice document for a job.
        
        Args:
            job_id (str): The relevant Job ID.
            account_id (str): The Customer Account ID.
            name (str): Title of the document.
            to_name (str): Person receiving the document.
            doc_type (str): "customerOrder" (Proposal/Estimate), "customerInvoice" (Invoice), etc.
            from_name (str): Organization representation name.
            tax_rate (float): Base applicable tax rate.
            location_name (str, optional): Name of property/location. Required by JobTread.
            location_address (str, optional): Address of property/location. Required by JobTread.
            due_days (int): Valid timeline for payment/signing (required by API business logic).
            line_items (list, optional): Cost group or cost item bindings (direct format).
        """
        payload = {
            "createDocument": {
                "$": {
                    "jobId": job_id,
                    "accountId": account_id,
                    "name": name,
                    "type": doc_type,
                    "fromName": from_name,
                    "toName": to_name,
                    "taxRate": tax_rate,
                    "dueDays": due_days
                },
                "createdDocument": {
                    "id": {},
                    "name": {},
                    "type": {}
                }
            }
        }
        if location_name:
            payload["createDocument"]["$"]["jobLocationName"] = location_name
        if location_address:
            payload["createDocument"]["$"]["jobLocationAddress"] = location_address
        if line_items:
            payload["createDocument"]["$"]["lineItems"] = line_items
            
        res = self.query(payload)
        return res["createDocument"]["createdDocument"]

    def _catalog_template_as_lineitem(self, template_group_id, collapse_group_names=None,
                                      link_job_cost_items=False):
        """Fetch a cost group (catalog template OR job budget) and all its descendants, returning a
        newCostGroup dict suitable for use as a createDocument/createCostGroup lineItem entry.

        When link_job_cost_items=True, each cost-item entry carries jobCostItemId = the source
        item's id. This is used when copying a job BUDGET into a document: the resulting document
        items stay linked to their budget items (so JobTread counts them once — estimated price
        from the budget, approved price from the document). No mutations are made.
        """
        collapse_group_names = collapse_group_names or set()

        node_fields = {
            "id": {}, "name": {}, "description": {},
            "isSelected": {}, "isSimpleSelection": {},
            "quantity": {}, "quantityFormula": {},
            "showChildren": {}, "showChildCosts": {},
            "showChildDeltas": {}, "showDescription": {},
            "minSelectionsRequired": {}, "maxSelectionsAllowed": {},
            "files": {"nodes": {"id": {}}}
        }
        item_fields = {
            "id": {}, "name": {}, "description": {},
            "costGroup": {"id": {}},
            "costType": {"id": {}}, "costCode": {"id": {}},
            "quantity": {}, "quantityFormula": {},
            "unitCost": {}, "unitCostFormula": {},
            "unitPrice": {}, "unitPriceFormula": {},
            "isTaxable": {}, "isSelected": {},
            "files": {"nodes": {"id": {}}},
            "organizationCostItem": {
                "id": {}, "unitCost": {}, "unitCostFormula": {},
                "unitPrice": {}, "unitPriceFormula": {}
            }
        }

        res = self.query({
            "currentGrant": {"organization": {"costGroups": {
                "$": {"where": {"=": [{"field": "id"}, template_group_id]}},
                "nodes": {
                    **node_fields,
                    "descendentCostGroups": {"nodes": {**node_fields, "parentCostGroup": {"id": {}}}},
                    "descendentCostItems": {"nodes": item_fields}
                }
            }}}
        })
        nodes = res["currentGrant"]["organization"]["costGroups"]["nodes"]
        if not nodes:
            raise ValueError(f"Template group '{template_group_id}' not found.")

        root = nodes[0]
        desc_groups = root.pop("descendentCostGroups")["nodes"]
        desc_items = root.pop("descendentCostItems")["nodes"]

        children_by_parent = {template_group_id: []}
        for g in desc_groups:
            pid = (g.get("parentCostGroup") or {}).get("id")
            children_by_parent.setdefault(pid, []).append(g)

        items_by_group = {}
        for item in desc_items:
            gid = (item.get("costGroup") or {}).get("id")
            items_by_group.setdefault(gid, []).append(item)

        def group_entry(g):
            name = g["name"]
            entry = {
                "_type": "costGroup",
                "name": name,
                "description": g.get("description"),
                "isSelected": g.get("isSelected") or False,
                "isSimpleSelection": g.get("isSimpleSelection") or False,
                "quantity": g.get("quantity") or 1,
                "showChildren": False if name in collapse_group_names else (g.get("showChildren") if g.get("showChildren") is not None else True),
                "showChildCosts": g.get("showChildCosts") if g.get("showChildCosts") is not None else True,
                "showChildDeltas": g.get("showChildDeltas") or False,
                "showDescription": g.get("showDescription") if g.get("showDescription") is not None else True,
                "lineItems": (
                    [item_entry(i) for i in items_by_group.get(g["id"], [])] +
                    [group_entry(c) for c in children_by_parent.get(g["id"], [])]
                )
            }
            if g.get("quantityFormula"): entry["quantityFormula"] = g["quantityFormula"]
            if g.get("minSelectionsRequired") is not None: entry["minSelectionsRequired"] = g["minSelectionsRequired"]
            if g.get("maxSelectionsAllowed") is not None: entry["maxSelectionsAllowed"] = g["maxSelectionsAllowed"]
            group_files = [{"_type": "lineItemFile", "id": f["id"]} for f in (g.get("files") or {}).get("nodes", [])]
            if group_files:
                entry["files"] = group_files
            return entry

        def item_entry(i):
            master = i.get("organizationCostItem") or {}
            # Cascade: template item values first, fall back to master catalog
            qty_formula = i.get("quantityFormula") or master.get("quantityFormula")
            cost_formula = i.get("unitCostFormula") or master.get("unitCostFormula")
            price_formula = i.get("unitPriceFormula") or master.get("unitPriceFormula")
            cost = None if cost_formula else (i.get("unitCost") if i.get("unitCost") is not None else master.get("unitCost"))
            price = None if price_formula else (i.get("unitPrice") if i.get("unitPrice") is not None else master.get("unitPrice"))

            entry = {
                "_type": "costItem",
                "name": i["name"],
                "costTypeId": i["costType"]["id"],
                "quantity": i.get("quantity") or 1,
                "isTaxable": i.get("isTaxable") if i.get("isTaxable") is not None else True,
                "isSelected": i.get("isSelected") or False,
            }
            if i.get("description"): entry["description"] = i["description"]
            if i.get("costCode"): entry["costCodeId"] = i["costCode"]["id"]
            if master.get("id"): entry["organizationCostItemId"] = master["id"]
            # Link the document item back to its source budget item (see docstring).
            if link_job_cost_items: entry["jobCostItemId"] = i["id"]
            if qty_formula: entry["quantityFormula"] = qty_formula
            if cost_formula: entry["unitCostFormula"] = cost_formula
            elif cost is not None: entry["unitCost"] = cost
            if price_formula: entry["unitPriceFormula"] = price_formula
            elif price is not None: entry["unitPrice"] = price
            item_files = [{"_type": "lineItemFile", "id": f["id"]} for f in (i.get("files") or {}).get("nodes", [])]
            if item_files:
                entry["files"] = item_files
            return entry

        return group_entry(root)

    def create_budget_from_packages(self, job_id, package_template_ids=None, collapse_group_names=None):
        """Build the job BUDGET from catalog package templates.

        Each package is instantiated as a top-level cost group directly on the job
        (createCostGroup with jobId, no documentId), carrying its full nested hierarchy,
        attached files, and selection options. These budget cost groups have document=None —
        they are what shows in the job's Budget tab. createCostGroup accepts nested `lineItems`
        and `files`, so each package tree is created in a single mutation.

        Returns the list of created top-level budget cost groups (id, name).
        """
        created_groups = []
        for pkg_id in (package_template_ids or []):
            entry = self._catalog_template_as_lineitem(pkg_id, collapse_group_names)
            # `entry` is a newCostGroup-shaped dict; its fields map directly onto the
            # createCostGroup input (name, description, files, selections, nested lineItems...).
            args = {k: v for k, v in entry.items() if k != "_type"}
            args["jobId"] = job_id
            payload = {
                "createCostGroup": {
                    "$": args,
                    "createdCostGroup": {"id": {}, "name": {}}
                }
            }
            res = self.query(payload)
            created_groups.append(res["createCostGroup"]["createdCostGroup"])
        return created_groups

    def create_document_from_template(self, job_id, template_id, package_template_ids=None, collapse_group_names=None):
        """Build the job budget from catalog packages, then create a document copying the budget.

        Mirrors JobTread's own "create document from budget" flow:
          1. Each selected package is built on the job BUDGET (createCostGroup with jobId —
             document=None, shows in the Budget tab), retaining files and selection options.
          2. A document is created whose line items mirror that budget tree, with each item
             carrying jobCostItemId = its budget item's id. The document items stay linked to
             the budget items, so JobTread counts them once (estimated price from the budget,
             approved price from the document).

        The document also inherits the template's header settings, selection display, and
        payment schedule (scheduledDocuments — e.g. deposit + remaining balance).
        """
        # Phase 1: build the budget on the job from the catalog packages.
        budget_groups = self.create_budget_from_packages(job_id, package_template_ids, collapse_group_names)

        # Phase 2: fetch template + job context (including the template's payment schedule).
        q = {
            "currentGrant": {
                "organization": {
                    "documentTemplates": {
                        "$": {"where": {"=": [{"field": "id"}, template_id]}},
                        "nodes": {
                            "id": {}, "name": {}, "type": {}, "footer": {},
                            "fromName": {}, "fromAddress": {}, "fromOrganizationName": {},
                            "fromEmailAddress": {}, "fromPhoneNumber": {},
                            "requireSignature": {}, "showChildCosts": {}, "showQuantity": {},
                            "dueDays": {}, "emailMessage": {}, "coverPageTitle": {},
                            "coverPageSubtitle": {}, "coverPageTemplate": {}, "description": {},
                            "groupsStartCollapsed": {}, "showLinesAtDepth": {},
                            "showProfit": {}, "showCostItemFiles": {}, "allowPartialPayments": {},
                            "showScheduledDocuments": {},
                            "scheduledDocuments": {
                                "$": {"sortBy": [{"field": ["position"], "order": "asc"}]},
                                "nodes": {
                                    "id": {}, "name": {}, "amount": {}, "percentage": {},
                                    "sendOnCreation": {},
                                    "createFromDocumentTemplate": {"id": {}}
                                }
                            }
                        }
                    },
                    "jobs": {
                        "$": {"where": {"=": [{"field": "id"}, job_id]}},
                        "nodes": {
                            "location": {
                                "name": {}, "address": {},
                                "account": {
                                    "id": {}, "name": {},
                                    "primaryContact": {
                                        "customFieldValues": {
                                            "nodes": {"value": {}, "customField": {"id": {}, "name": {}}}
                                        }
                                    },
                                    "primaryLocation": {"address": {}}
                                }
                            }
                        }
                    }
                }
            }
        }
        res = self.query(q)

        tmpl = res["currentGrant"]["organization"]["documentTemplates"]["nodes"][0]
        location = res["currentGrant"]["organization"]["jobs"]["nodes"][0]["location"]
        account = location["account"]
        to_name = account["name"].split(" (")[0]

        # Extract email and phone from primary contact custom fields
        contact_cfs = {
            cf["customField"]["name"]: cf["value"]
            for cf in ((account.get("primaryContact") or {}).get("customFieldValues") or {}).get("nodes", [])
        }
        to_email = contact_cfs.get("Email")
        to_phone = contact_cfs.get("Phone")
        to_address = ((account.get("primaryLocation") or {}).get("address"))

        # Build the document's line items by mirroring the budget groups created in phase 1.
        # link_job_cost_items=True sets jobCostItemId on each item so the document stays linked
        # to the budget. Files and selection options carry through from the budget.
        line_items = [
            self._catalog_template_as_lineitem(grp["id"], collapse_group_names, link_job_cost_items=True)
            for grp in budget_groups
        ]

        # Copy the payment schedule from the document template. Each scheduled document maps a
        # percentage/amount to a child document template that JobTread auto-issues (e.g. deposit,
        # progress, and final invoices) once the proposal is approved.
        scheduled_documents = []
        for sd in (tmpl.get("scheduledDocuments") or {}).get("nodes", []):
            entry = {"name": sd["name"], "sendOnCreation": sd.get("sendOnCreation") or False}
            if sd.get("amount") is not None:
                entry["amount"] = sd["amount"]
            if sd.get("percentage") is not None:
                entry["percentage"] = sd["percentage"]
            cff = sd.get("createFromDocumentTemplate") or {}
            if cff.get("id"):
                entry["createFromDocumentTemplateId"] = cff["id"]
            scheduled_documents.append(entry)

        payload_args = {
            "jobId": job_id,
            "accountId": account["id"],
            "name": tmpl["name"],
            "type": tmpl["type"],
            "fromName": tmpl.get("fromName") or "",
            "toName": to_name,
            "dueDays": tmpl.get("dueDays") or 30,
            "taxRate": 0,
            "jobLocationName": location["name"],
            "jobLocationAddress": location["address"],
            # includeInBudget = this document's line items are part of the job's budget /
            # financial tracking. The items link back to the budget via jobCostItemId (set
            # above), so they are counted once. JobTread's own budget→document flow sets this
            # True, so we match it.
            "includeInBudget": True,
            "lineItems": line_items
        }
        if scheduled_documents:
            payload_args["scheduledDocuments"] = scheduled_documents
        if to_address: payload_args["toAddress"] = to_address
        if to_email: payload_args["toEmailAddress"] = to_email
        if to_phone: payload_args["toPhoneNumber"] = to_phone
        for field in ("footer", "emailMessage", "coverPageTitle", "coverPageSubtitle",
                      "coverPageTemplate", "description", "requireSignature", "showChildCosts",
                      "showQuantity", "showCostItemFiles", "groupsStartCollapsed",
                      "showLinesAtDepth", "showProfit", "allowPartialPayments",
                      "showScheduledDocuments",
                      "fromAddress", "fromOrganizationName", "fromEmailAddress", "fromPhoneNumber"):
            val = tmpl.get(field)
            if val is not None:
                payload_args[field] = val

        payload = {
            "createDocument": {
                "$": payload_args,
                "createdDocument": {"id": {}, "name": {}, "type": {}}
            }
        }
        res = self.query(payload)
        return res["createDocument"]["createdDocument"]

    def add_cost_group_from_template(self, job_id, template_group_id, description_override=None,
                                     materials_qty=None, materials_unit_cost=None, materials_unit_price=None,
                                     materials_markup=None, labor_qty=None, labor_unit_cost=None, labor_unit_price=None):
        """Dynamically fetch and add a catalog cost group template to a job budget with customizations.
        
        Retains Gentry standard pricing formulas automatically by carrying over Organization Cost Item 
        configurations and cascading parent variables.
        """
        # 1. Fetch details of the template cost group
        q_group = {
            "currentGrant": {
                "organization": {
                    "costGroups": {
                        "$": {
                            "where": {"=": [{"field": "id"}, template_group_id]}
                        },
                        "nodes": {
                            "name": {},
                            "description": {}
                        }
                    }
                }
            }
        }
        res_group = self.query(q_group)
        nodes_group = res_group["currentGrant"]["organization"]["costGroups"]["nodes"]
        if not nodes_group:
            raise ValueError(f"Catalog template Cost Group ID '{template_group_id}' not found.")
            
        template_name = nodes_group[0]["name"]
        template_desc = nodes_group[0]["description"]
        
        # 2. Fetch all child template cost items, deeply fetching related catalog masters
        q_items = {
            "currentGrant": {
                "organization": {
                    "costItems": {
                        "$": {
                            "where": {"=": [{"field": ["costGroup", "id"]}, template_group_id]},
                            "size": 100
                        },
                        "nodes": {
                            "name": {},
                            "description": {},
                            "isTaxable": {},
                            "unitCost": {},
                            "unitPrice": {},
                            "quantity": {},
                            "unitCostFormula": {},
                            "unitPriceFormula": {},
                            "quantityFormula": {},
                            "costType": {"id": {}},
                            "costCode": {"id": {}},
                            "organizationCostItem": {
                                "id": {},
                                "unitCostFormula": {},
                                "unitPriceFormula": {},
                                "quantityFormula": {},
                                "unitCost": {},
                                "unitPrice": {}
                            }
                        }
                    }
                }
            }
        }
        res_items = self.query(q_items)
        template_items = res_items["currentGrant"]["organization"]["costItems"]["nodes"]
        
        # 3. Create the new nested cost group under the Job
        final_description = description_override if description_override is not None else template_desc
        created_group = self.create_cost_group(job_id=job_id, name=template_name, description=final_description)
        new_group_id = created_group["id"]
        
        added_items = []
        
        # 4. Process and instantiate each cost item carrying over master formulas
        for t_item in template_items:
            name = t_item["name"]
            desc = t_item.get("description")
            is_taxable = t_item.get("isTaxable", True)
            cost_type_id = t_item["costType"]["id"]
            cost_code_id = t_item["costCode"]["id"] if t_item.get("costCode") else None
            
            # Fetch master catalog reference if any
            master_ref = t_item.get("organizationCostItem") or {}
            org_item_id = master_ref.get("id")
            
            # Default values from template/catalog
            final_qty = t_item.get("quantity") or 1
            final_qty_formula = t_item.get("quantityFormula") or master_ref.get("quantityFormula")
            
            # Inherit formulas from template, or cascade to master catalog item
            final_cost_formula = t_item.get("unitCostFormula") or master_ref.get("unitCostFormula")
            final_price_formula = t_item.get("unitPriceFormula") or master_ref.get("unitPriceFormula")
            
            # Only specify raw costs if not using formulas, or if overridden
            final_cost = None
            final_price = None
            
            if not final_cost_formula:
                final_cost = t_item.get("unitCost") or master_ref.get("unitCost")
            if not final_price_formula:
                final_price = t_item.get("unitPrice") or master_ref.get("unitPrice")
            
            # Detect materials or labor based on name keywords
            name_lower = name.lower()
            if "material" in name_lower or "fitting" in name_lower:
                if materials_qty is not None: final_qty = materials_qty
                
                # Material pricing override engine
                if materials_unit_cost is not None:
                    final_cost = materials_unit_cost
                    final_cost_formula = None # Wiping formula if cost is explicitly customized
                    
                    # Applying customized markup percentage if provided!
                    if materials_unit_price is None:
                        if materials_markup is not None:
                            # e.g., materials_markup = 75% -> cost * 1.75
                            final_price = materials_unit_cost * (1.0 + (materials_markup / 100.0))
                            final_price_formula = None
                            print(f"Applying customized cost markup of {materials_markup}% -> unitPrice = ${final_price:.2f}")
                        else:
                            # Default back to 100% Gentry standard material markup
                            final_price = materials_unit_cost * 2.0
                            final_price_formula = None
                            
                if materials_unit_price is not None:
                    final_price = materials_unit_price
                    final_price_formula = None # Wiping formula if price is explicitly customized
                    
            elif "labor" in name_lower or "install" in name_lower:
                if labor_qty is not None: final_qty = labor_qty
                if labor_unit_cost is not None:
                    final_cost = labor_unit_cost
                    final_cost_formula = None
                if labor_unit_price is not None:
                    final_price = labor_unit_price
                    final_price_formula = None
                
            # Create item retaining catalog ties and formulas
            new_item = self.create_cost_item(
                job_id=job_id,
                document_id=document_id,
                cost_group_id=new_group_id,
                name=name,
                cost_type_id=cost_type_id,
                cost_code_id=cost_code_id,
                description=desc,
                quantity=final_qty,
                quantity_formula=final_qty_formula,
                unit_cost=final_cost,
                unit_cost_formula=final_cost_formula,
                unit_price=final_price,
                unit_price_formula=final_price_formula,
                is_taxable=is_taxable,
                organization_cost_item_id=org_item_id,
                is_selected=t_item.get("isSelected")
            )
            added_items.append(new_item)
            
        return {
            "costGroup": created_group,
            "costItems": added_items
        }

    def add_cost_group_from_template_recursive(self, job_id=None, template_group_id=None, parent_cost_group_id=None,
                                              materials_qty=None, materials_unit_cost=None, materials_unit_price=None,
                                              materials_markup=None, labor_qty=None, labor_unit_cost=None, labor_unit_price=None,
                                              document_id=None):
        """Recursively fetch and add a catalog cost group template and all its nested subgroups and cost items.

        Preserves visual hierarchies exactly as designed in Gentry's master catalog, keeping selection
        options, defaults, and formula configurations intact.
        Pass document_id to attach items to a document (and job budget) instead of the raw job budget.
        """
        # 1. Fetch details of the template cost group
        q_group = {
            "currentGrant": {
                "organization": {
                    "costGroups": {
                        "$": {
                            "where": {"=": [{"field": "id"}, template_group_id]}
                        },
                        "nodes": {
                            "name": {},
                            "description": {},
                            "isSelected": {},
                            "isSimpleSelection": {},
                            "minSelectionsRequired": {},
                            "maxSelectionsAllowed": {},
                            "showChildren": {},
                            "showChildCosts": {},
                            "showChildDeltas": {},
                            "showDescription": {},
                            "quantity": {},
                            "quantityFormula": {}
                        }
                    }
                }
            }
        }
        res_group = self.query(q_group)
        nodes_group = res_group["currentGrant"]["organization"]["costGroups"]["nodes"]
        if not nodes_group:
            raise ValueError(f"Catalog template Cost Group ID '{template_group_id}' not found.")
            
        tg = nodes_group[0]
        template_name = tg["name"]
        template_desc = tg["description"]

        # 2. Create the copy of this group under the Job or Document referencing parent_cost_group_id
        created_group = self.create_cost_group(
            job_id=job_id,
            document_id=document_id,
            name=template_name,
            description=template_desc,
            quantity=tg.get("quantity") or 1,
            quantity_formula=tg.get("quantityFormula"),
            parent_cost_group_id=parent_cost_group_id,
            is_selected=tg.get("isSelected"),
            is_simple_selection=tg.get("isSimpleSelection"),
            min_selections_required=tg.get("minSelectionsRequired"),
            max_selections_allowed=tg.get("maxSelectionsAllowed"),
            show_children=tg.get("showChildren"),
            show_child_costs=tg.get("showChildCosts"),
            show_child_deltas=tg.get("showChildDeltas"),
            show_description=tg.get("showDescription")
        )
        new_group_id = created_group["id"]
        
        # 3. Fetch and copy all child template cost items
        q_items = {
            "currentGrant": {
                "organization": {
                    "costItems": {
                        "$": {
                            "where": {"=": [{"field": ["costGroup", "id"]}, template_group_id]},
                            "size": 100
                        },
                        "nodes": {
                            "name": {},
                            "description": {},
                            "isTaxable": {},
                            "isSelected": {},
                            "unitCost": {},
                            "unitPrice": {},
                            "quantity": {},
                            "unitCostFormula": {},
                            "unitPriceFormula": {},
                            "quantityFormula": {},
                            "costType": {"id": {}},
                            "costCode": {"id": {}},
                            "organizationCostItem": {
                                "id": {},
                                "unitCostFormula": {},
                                "unitPriceFormula": {},
                                "quantityFormula": {},
                                "unitCost": {},
                                "unitPrice": {}
                            }
                        }
                    }
                }
            }
        }
        res_items = self.query(q_items)
        template_items = res_items["currentGrant"]["organization"]["costItems"]["nodes"]
        
        added_items = []
        for t_item in template_items:
            name = t_item["name"]
            desc = t_item.get("description")
            is_taxable = t_item.get("isTaxable", True)
            cost_type_id = t_item["costType"]["id"]
            cost_code_id = t_item["costCode"]["id"] if t_item.get("costCode") else None
            
            # Fetch master catalog reference if any
            master_ref = t_item.get("organizationCostItem") or {}
            org_item_id = master_ref.get("id")
            
            # Default values from template/catalog
            final_qty = t_item.get("quantity") or 1
            final_qty_formula = t_item.get("quantityFormula") or master_ref.get("quantityFormula")
            
            # Inherit formulas from template, or cascade to master catalog item
            final_cost_formula = t_item.get("unitCostFormula") or master_ref.get("unitCostFormula")
            final_price_formula = t_item.get("unitPriceFormula") or master_ref.get("unitPriceFormula")
            
            final_cost = None
            final_price = None
            
            if not final_cost_formula:
                final_cost = t_item.get("unitCost") or master_ref.get("unitCost")
            if not final_price_formula:
                final_price = t_item.get("unitPrice") or master_ref.get("unitPrice")
            
            # Detect materials or labor based on name keywords to apply customizations
            name_lower = name.lower()
            if "material" in name_lower or "fitting" in name_lower:
                if materials_qty is not None: final_qty = materials_qty
                if materials_unit_cost is not None:
                    final_cost = materials_unit_cost
                    final_cost_formula = None
                    if materials_unit_price is None:
                        if materials_markup is not None:
                            final_price = materials_unit_cost * (1.0 + (materials_markup / 100.0))
                            final_price_formula = None
                        else:
                            final_price = materials_unit_cost * 2.0
                            final_price_formula = None
                if materials_unit_price is not None:
                    final_price = materials_unit_price
                    final_price_formula = None
                    
            elif "labor" in name_lower or "install" in name_lower:
                if labor_qty is not None: final_qty = labor_qty
                if labor_unit_cost is not None:
                    final_cost = labor_unit_cost
                    final_cost_formula = None
                if labor_unit_price is not None:
                    final_price = labor_unit_price
                    final_price_formula = None
                
            new_item = self.create_cost_item(
                job_id=job_id,
                document_id=document_id,
                cost_group_id=new_group_id,
                name=name,
                cost_type_id=cost_type_id,
                cost_code_id=cost_code_id,
                description=desc,
                quantity=final_qty,
                quantity_formula=final_qty_formula,
                unit_cost=final_cost,
                unit_cost_formula=final_cost_formula,
                unit_price=final_price,
                unit_price_formula=final_price_formula,
                is_taxable=is_taxable,
                organization_cost_item_id=org_item_id,
                is_selected=t_item.get("isSelected")
            )
            added_items.append(new_item)

        # 4. Fetch and recursively copy all child template cost groups
        q_children = {
            "currentGrant": {
                "organization": {
                    "costGroups": {
                        "$": {
                            "where": {"=": [{"field": ["parentCostGroup", "id"]}, template_group_id]},
                            "size": 100
                        },
                        "nodes": {
                            "id": {}
                        }
                    }
                }
            }
        }
        res_children = self.query(q_children)
        child_groups = res_children["currentGrant"]["organization"]["costGroups"]["nodes"]
        
        nested_results = []
        for child_g in child_groups:
            c_res = self.add_cost_group_from_template_recursive(
                job_id=job_id,
                template_group_id=child_g["id"],
                parent_cost_group_id=new_group_id,
                materials_qty=materials_qty,
                materials_unit_cost=materials_unit_cost,
                materials_unit_price=materials_unit_price,
                materials_markup=materials_markup,
                labor_qty=labor_qty,
                labor_unit_cost=labor_unit_cost,
                labor_unit_price=labor_unit_price,
                document_id=document_id
            )
            nested_results.append(c_res)
            
        return {
            "costGroup": created_group,
            "costItems": added_items,
            "childGroups": nested_results
        }
