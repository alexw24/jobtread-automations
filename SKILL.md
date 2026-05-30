# JobTread API Integration Skill

This skill allows a coder or an AI agent to safely query and mutate Gentry Plumbing & Contracting's JobTread platform using the standard Pave API.

## Core Setup

Authentication utilizes a persistent `GRANT_KEY` and `organizationID` parsed from a `.env` file in the root project folder.

Always import and initialize `JobTreadClient`:
```python
from jobtread import JobTreadClient
client = JobTreadClient()
```

## Crucial Architectural Insights (Pave Protocol)

### 1. Sibling Mutation Nesting
Pave's mutation operations (such as `createAccount`, `createJob`, `createDocument`) return the `root` schema type. To fetch the identifier (ID) of the record that was just written, **nest the sibling `createdX` projection inside the mutation query block**:
```python
payload = {
    "createAccount": {
        "$": { "name": "Customer Name", "type": "customer", "organizationId": org_id }
    },
    "createdAccount": {
        "id": {},
        "name": {}
    }
}
```

### 2. Union Type discriminator (`_type`) for line items
JobTread does not wrap union arrays in selection labels (like `existingCostGroup`). It expects items within arrays directly as objects, identifying their concrete structure based on a required `_type` string:
* Cost Group: `{"_type": "costGroup", "name": "Rough-In", ...}`
* Cost Item: `{"_type": "costItem", "name": "Pipe fitting", ...}`

### 3. Creating Budget and Proposal Together (Atomic Workflow)
Do not create budget items on the Job first and then reference them individually. This leads to out-of-sync "Unknown Cost Group" issues. 
Instead, trigger **cohesive creation**! When creating a draft Document (e.g. `doc_type="customerOrder"`, which means a Proposal), nest your desired `costGroup` and `costItem` list directly inside the document's `lineItems`. JobTread automatically constructs the document, hooks up the elements, and populates the Job's budget cleanly in one transaction.

---

## Active Environment Gentry ID Catalog

When programmatically mapping services or cost accounting codes, use the valid IDs pulled directly from Gentry's production profile:

### Valid Cost Types
* **Labor:** `'22NsehctrCaw'`
* **Materials:** `'22NsehctrCax'`
* **Subcontractor:** `'22NsehctrCay'`
* **Other:** `'22NsehctrCaz'`
* **Equipment Rental:** `'22PV7ZSRNc9L'`

### Plumbing Cost Code
* **Plumbing Code 1100:** `'22NsehctrCaZ'`
