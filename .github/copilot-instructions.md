# Copilot Instructions for Maritime Fabric Demo

## Project Overview

This repository is a **Microsoft Fabric demonstration** for maritime insurance risk assessment. It is **not** a traditional software project — there are no builds, tests, or linters. Instead, it's a data integration project that deploys Fabric assets (notebooks, semantic models, data agents, ontologies) to a cloud workspace.

The project demonstrates:
- Real-time vessel tracking via AIS data streaming
- Insurance ontology (knowledge graph) linking vessels, companies, cargo, and policies
- RAG-powered policy search using Azure AI Search
- Multi-source Data Agent reasoning across live telemetry, business logic, and document knowledge

## Deployment Workflow

### Critical Git Convention: Template Values

The repository uses **workspace-agnostic template values** (GUIDs, cluster URIs, workspace IDs). When `deployworkspace.ipynb` runs:
1. **Local files are modified** with deployment-specific values (actual workspace IDs, cluster URIs)
2. **These changes must NOT be committed** — revert with `git checkout .` or `git restore .` after deployment
3. The Git repository should always contain workspace-neutral template values

### Deployment Entry Point

All Fabric items deploy via `deployworkspace.ipynb`:
```bash
pip install azure-identity fabric-cicd requests
code deployworkspace.ipynb  # Run cells 1-9 sequentially
```

The notebook:
- Authenticates with Azure (device code flow)
- Deploys 18 Fabric items in 6 phases with automatic dependency ordering
- Modifies local files with your workspace IDs (template values → actual IDs)
- **Phase 1**: Lakehouse + Eventhouse (data foundation)
- **Phase 2**: Semantic Model + Power BI Report (DirectLake connection)
- **Phase 3**: Ontology
- **Phase 4**: Notebooks + Eventstream + Data Agent
- **Phase 5**: Reflex (alerting)
- **Phase 6**: Map (visualization)

## Fabric Asset Structure

Assets are stored in directories with Fabric-specific suffixes:

| Asset Type | Directory Pattern | Language | Purpose |
| --- | --- | --- | --- |
| Notebook | `*.Notebook/` | Python (PySpark) | ETL, simulation, ontology creation |
| Lakehouse | `*.Lakehouse/` | Spark/Delta | Structured entity tables (companies, vessels, cargo, policies) |
| Eventhouse | `*.Eventhouse/` | KQL | Real-time ship position stream (materialized view: `LatestShipPositionsEnriched`) |
| Semantic Model | `*.SemanticModel/` | Power Query | DirectLake connection to Lakehouse, ontology mappings |
| Report | `*.Report/` | JSON + PBIP | Power BI dashboards (e.g., "Vessels By Company") |
| Ontology | `*.Ontology/` | YAML | Entity relationships for business context navigation |
| Data Agent | `*.DataAgent/` | Fabric portal UI | Multi-source conversational agent (Eventhouse + Ontology + AI Search) |
| Eventstream | `*.Eventstream/` | Fabric portal UI | Event Hub ingestion (AisStream.io → Eventstream → Eventhouse) |
| Reflex | `*.Reflex/` | JSON | Alert automation (e.g., risk zone violations) |
| Map | `*.Map/` | JSON | Real-time geospatial visualization |

### Metadata Files

- Notebook metadata stored in cell headers: `# METADATA` blocks define Lakehouse/Eventhouse bindings
- Configuration cells (first code cell) hold workspace-specific parameters:
  - `AISSTREAM_API_KEY` — API key from [AisStream.io](https://aisstream.io/)
  - `FABRIC_ENTITY_NAME` — Event Hub name from Eventstream
  - `FABRIC_CONNECTION_STR` — Event Hub connection string (use Azure Key Vault in production)
  - `kusto_cluster` — Eventhouse KQL cluster URI (auto-updated on deployment)
  - `kusto_db` — KQL database name

## Data Flow & Architecture

### Core Entities (Semantic Model)

The **`maritimeSM`** semantic model contains five linked entities:

```
VESSEL (hub)
  ├── CompanyID → COMPANY (who operates it)
  ├── CargoID → CARGO (what it carries)
  ├── PolicyID → POLICY (insurance coverage)
  └── MMSI → LatestShipPositionsEnriched (live position, Eventhouse MV)
```

Entity relationships use **bi-directional cross-filtering** for context-aware queries.

**Key Tables:**
- `Vessels` — Ship metadata (MMSI, hull value, vessel type)
- `Companies` — Fleet operators (company ID, HQ, risk rating, fleet size)
- `Cargo` — Cargo manifest (type, handling class, insured value)
- `Policies` — Insurance contracts (type, deductible, coverage limit)
- `LatestShipPositionsEnriched` — **Eventhouse materialized view** (real-time: position, speed, heading, risk zone per MMSI)

All base entities are stored as Delta tables in the **`maritimeLH`** Lakehouse; the Eventhouse feeds live positions.

### Data Agent Sources

The **`maritimeDA`** Data Agent fuses three complementary data sources:

| Source | Type | Role |
| --- | --- | --- |
| `LatestShipPositionsEnriched` | KQL (Eventhouse MV) | Live telemetry: position, speed, heading, risk zone per MMSI |
| `maritimeOntologyfromSM` | Ontology | Business context: traverse vessel → company/cargo/policy relationships |
| Azure AI Search | Vector index (RAG) | Policy clauses, warranties, exclusions from `/resources/*.docx` documents |

The agent synthesizes multi-step reasoning: *"Is ship X in a high-risk zone? What does its policy say about that zone?"*

### Data Intake

- **Real-time**: `runVessels.ipynb` streams live AIS data from [AisStream.io](https://aisstream.io/) → Eventstream → Eventhouse (run 1-2 minutes)
- **Simulated**: `runVesselswithSimulation.ipynb` and `runVesselswithSimulation2.ipynb` inject test vessels crossing risk zones (run 1-2 minutes each)
- **Ontology**: `createOntology.ipynb` materializes 5 Lakehouse tables from Eventhouse data (run after vessel notebooks populate the stream)

After data is in the Lakehouse, the Semantic Model must be refreshed (`SemanticModel` → **Refresh → "Schema and data"**) to pick up new tables. This can take 15–20 minutes for metadata sync.

## Key Conventions

### Notebook Configuration Cells

Every executable notebook (runVessels, runVesselswithSimulation, createOntology) has a **configuration cell at the top** that sets workspace-specific parameters:

```python
# ===== CONFIGURATION =====
AISSTREAM_API_KEY = "your-key-from-aisstream-dashboard"
FABRIC_ENTITY_NAME = "esehchxkj881x95xl1hgnk_eh"  # Event Hub name
# Option A (Production): Use Key Vault
KEY_VAULT_NAME = "https://kv-maritime-demo.vault.azure.net/"
FABRIC_CONNECTION_STR = mssparkutils.credentials.getSecret(KEY_VAULT_NAME, "FabricConnectionString")
# Option B (Local): Use direct value (NEVER commit to Git)
# FABRIC_CONNECTION_STR = "Endpoint=sb://xxxxx.servicebus.windows.net/..."
```

**Best practice**: Store secrets in Azure Key Vault; never commit connection strings to Git.

### Notebook Metadata Binding

Notebooks are bound to Lakehouse/Eventhouse via metadata cells:

```python
# METADATA ********************
# META {
#   "dependencies": {
#     "lakehouse": {
#       "default_lakehouse": "e840bf2c-5866-42e4-91c2-3e6aca5ede5e",
#       "default_lakehouse_name": "maritimeLH",
#       "default_lakehouse_workspace_id": "821daf86-9ecb-4d7f-a7d9-9cc3c0541028"
#     }
#   }
# }
```

These values are **auto-updated on deployment**. Do not manually edit GUIDs — the deployment notebook handles this.

### Eventhouse KQL Queries

The Eventhouse uses **KQL (Kusto Query Language)**, not SQL. When querying from notebooks, use the `kusto_cluster` and `kusto_db` variables:

```python
kusto_cluster = "https://trd-sketzz3a64smc48ffd.z1.kusto.fabric.microsoft.com"
kusto_db = "maritimeEH"
# Query via Spark or direct KQL API
```

The key materialized view is `LatestShipPositionsEnriched` — updated in real-time with the most recent position per MMSI.

### Ontology Entity Binding

The Ontology (`maritimeOntologyfromSM`) maps Power BI entities to business concepts. When modifying ontology relationships:
1. Update the Semantic Model entity relationships
2. Refresh the Ontology in Fabric portal
3. If relationships don't appear, add a dummy property and remove it (triggers metadata refresh)

### Policy Documents for RAG

Insurance policy documents live in `/resources/`:
- `POL-9901.docx` — Sample hull & machinery policy
- `POL-9902.docx` — Sample war risk policy

These are imported into an **Azure AI Search index** (manual setup required). The Data Agent queries this index via RAG to answer policy-specific questions.

## File & Directory Guide

```
fabricdemo/
├── deployworkspace.ipynb              # Main entry point — deploy all 18 items
├── README.md                          # Full documentation (architecture, setup steps)
├── .gitignore                         # Excludes workspace-specific generated files
│
├── createOntology.Notebook/           # Create 5 Lakehouse tables from Eventhouse
├── runVessels.Notebook/               # Stream live AIS from AisStream.io
├── runVesselswithSimulation.Notebook/ # Simulated vessel #1 (test itinerary)
├── runVesselswithSimulation2.Notebook/# Simulated vessel #2 (test itinerary)
│
├── maritimeLH.Lakehouse/              # Delta Lake storage for entities
├── maritimeEH.Eventhouse/             # KQL database for real-time ship positions
├── maritimeSM.SemanticModel/          # DirectLake semantic model (Vessel hub entity)
├── Vessels By Company.Report/         # Power BI dashboard
├── maritimeOntologyfromSM.Ontology/   # Entity relationship graph
│
├── maritimeDA.DataAgent/              # Multi-source conversational agent
├── maritimeES.Eventstream/            # Event Hub ingestion
├── RedAlertActivator.Reflex/          # Alert automation
├── vessels_map.Map/                   # Real-time geospatial map
│
└── resources/
    ├── POL-9901.docx                  # Sample policy document #1
    ├── POL-9902.docx                  # Sample policy document #2
    ├── HormuzShippingCorridor.geojson # Risk zone geometry
    ├── hormuz_risk_zone.geojson       # Risk zone boundaries
    └── architecture.jpg               # High-level architecture diagram
```

## Common Tasks

### Deploy to a New Workspace
1. Update `TARGET_WORKSPACE_NAME` in `deployworkspace.ipynb`
2. Run cells 1–9
3. When deployment completes: `git checkout .` to revert workspace-specific file changes
4. Follow [Post-Deployment Configuration](README.md#post-deployment-configuration) in README.md

### Add a New Notebook
1. Create notebook in Fabric portal (or use VS Code with Fabric extension)
2. Export to local repository (Fabric CLI or Git sync)
3. Ensure metadata cell binds to `maritimeLH` Lakehouse
4. Add notebook directory name to `deployworkspace.ipynb` phase list

### Modify Semantic Model or Ontology
1. Edit in Fabric portal Semantic Model UI
2. Update entity relationships if needed
3. Run **Refresh → "Schema and data"** on the Semantic Model
4. If ontology relationships don't sync, add/remove a dummy property to trigger refresh
5. Export changes back to Git (via Fabric CLI or VS Code extension)

### Query Live Ship Positions
```python
# From a notebook, after runVessels has populated Eventhouse:
kusto_query = """
LatestShipPositionsEnriched
| where RiskZone == "Hormuz"
| project MMSI, Latitude, Longitude, Sog, LastUpdated
| take 10
"""
# Execute via KQL or Spark DataFrame API
```

### Test Data Agent Reasoning
1. Run `runVesselswithSimulation` or `runVesselswithSimulation2` notebooks (1–2 minutes)
2. Open `maritimeDA` Data Agent in Fabric portal
3. Ask: *"SIMULATED_TANKER_01 reported damage — are we covering it?"*
4. Agent queries Eventhouse (location), Ontology (policy), and AI Search (coverage terms) to answer

### Configure Azure AI Search for Policy RAG
See [Step 7 in README.md](README.md#7-configure-azure-ai-search-for-policy-documents). Requires:
1. Create Azure AI Search resource
2. Import `/resources/*.docx` with vector search enabled
3. Manually add the index as a data source to `maritimeDA` Data Agent

## Important Notes

- **No builds or tests** — this is a deployment and data integration project
- **Git is template-focused** — workspace IDs in local files are transient; revert after deployment
- **Metadata sync delays** — Lakehouse → Semantic Model can take 15–20 minutes; if "tables not found", wait and retry
- **Secrets in Key Vault** — connection strings should never appear in committed code; use Azure Key Vault
- **KQL not SQL** — Eventhouse queries use Kusto Query Language, not T-SQL
- **Bi-directional relationships** — Semantic Model uses cross-filtering for flexible entity navigation
