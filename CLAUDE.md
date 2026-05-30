# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a documentation and configuration project for the **JobTread API** — a construction/project management platform. It is not a traditional source code repository. The project contains API schema definitions, reference documentation, and sample data for building integrations with the JobTread platform.

## Key Files

- **`JobTread API Schema.json`** (~80K lines) — Complete Pave API schema with 171 entities. Too large to read in full; target specific sections by searching for entity names.
- **`JobTread API summary.rtf`** — Quick reference of all endpoint categories.
- **`JobTread Glossary of Terms.txt`** — Construction industry terminology as used in JobTread.
- **`catalog-parameters-template.csv`** — Template for job parameters (Number, Picklist, Formula types).
- **`real-job.csv`** — Sample job data showing cost structure with groups, items, cost codes, margin/markup.
- **`.env`** — Contains `GRANT_KEY` for API authentication.

## API Architecture (Pave)

The API uses **Pave**, a GraphQL-like query system. Every entity supports a consistent query pattern:

**Input:** `page`, `with`, `expressions`, `where`, `size` (min 1), `group` (by/aggs/firstIdBy), `sortBy`
**Output:** `nextPage`, `previousPage`, `nodes`, `withValues`, `count`

**Aggregations:** `count`, `sum`, `avg`, `min`, `max`, `values`
**Sort orders:** `asc`, `asc nulls first`, `desc`, `desc nulls last`

Authentication uses a grant-based system (`currentGrant` with a `GRANT_KEY`).

## Core Domain Entities

- **Jobs** (`job`) — Central entity; tracks budget, schedule, documents, costs, and profitability
- **Accounts** (`account`) — Customers and vendors
- **Documents** (`document`, 111 fields) — Invoices, estimates, bills, proposals, purchase orders, change orders
- **Cost tracking** — `costCode` > `costGroup` > `costItem` hierarchy with margin/markup, taxability, formulas
- **Tasks** (`task`) — Scheduling with baselines, dependencies, assignments, and subtasks
- **Payments** (`payment`) — With Stripe/Plaid integrations

## Financial Model

- **Cost codes** are accounting buckets; cost items always belong to a cost code
- **Cost groups** (aka cost templates) organize items into nestable groups (up to 5 levels)
- **Cost types:** Labor, Materials, Subcontractor, Equipment
- **Price types:** Fixed price, Cost plus, No customer
- **Margin** = profit / price; **Markup** = profit / cost
- Formulas supported for quantity, unit cost, and unit price (e.g., `{Shower floor sf}`, `ceil(if(...))`)
- Allowance types: Price Allowance, Cost Allowance, Cost & Fee Allowance

## Environment Setup

- Python 3.9 virtual environment in `.venv/`
- Activate: `source .venv/bin/activate`

## Working with the Schema

When looking up an entity, search the JSON schema file for the entity name rather than reading the whole file:
```bash
# Find a specific entity's schema
grep -n '"entityName"' "JobTread API Schema.json"
```

The schema root structure is: `schema.<entityName>.object.<field>` for entity fields, with `input`/`output` sub-objects defining query parameters and return types.