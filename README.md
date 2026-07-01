# 🚢 Maritime Risk Assessment Data Agent ("Company Brain")

This repository provides the architectural blueprint for a maritime insurance "Company Brain." By fusing real-time IoT vessel telemetry with unstructured policy documentation, this solution enables generative AI to execute dynamic, ontology-driven risk and compliance checks.

## 🏗 High-Level Architecture

The solution relies on four core layers integrated within **Microsoft Fabric**:

1. **Ontology Layer:** Defines the semantic relationship between vessels, companies, cargo, and insurance contracts.
2. **Telemetry Stream:** We leverage **[AisStream.io](https://aisstream.io/)** as our real-time global maritime data source. Live AIS telemetry is ingested via Fabric Eventstream into a KQL Database (Eventhouse).
3. **Policy Knowledge Base:** Vectorized insurance policy documentation indexed in **Azure AI Search** for RAG (Retrieval-Augmented Generation).
4. **Data Agent:** An orchestrator that dynamically computes risk by mapping live vessel coordinates (from Eventhouse) against contractual warranties (from Azure AI Search).

## 📁 Repository Structure

```text
├── fabric-assets/      # Schema definitions for Eventhouse and Eventstream
├── notebooks/          # Fabric Notebooks for initialization and simulation
│   ├── createOntology.ipynb  # Builds static metadata (Vessels, Companies, Policies)
│   └── runVessels.ipynb      # Live telemetry generator streaming to Eventhouse
├── resources/           # Policy documents (Source of Truth for RAG)
└── maps/               # Power BI/Real-Time Dashboard definitions

```

## 🚀 Deployment Instructions

### 1. Initialize the Ontology

Import the `createOntology.ipynb` notebook into your Fabric Workspace and run it. This establishes your Lakehouse master tables and defines the business ontology.

### 2. Configure Security (Azure Key Vault)

To maintain enterprise security, this solution utilizes **Azure Key Vault**:

1. Create a Key Vault and add secrets: `AisStreamApiKey` and `FabricConnectionString`.
2. Ensure your Fabric identity has **"Key Vault Secrets User"** access to the Key Vault.
3. The `runVessels.ipynb` notebook dynamically fetches these secrets at runtime using `mssparkutils`, ensuring no credentials are ever committed to source control.

### 3. Run Simulations

To fully power the "Company Brain," run the following notebooks:

* **`createOntology.ipynb`**: Required first to populate the static metadata and master data tables.
* **`runVessels.ipynb`**: Run this continuously to generate and stream real-time AIS telemetry from **[AisStream.io](https://aisstream.io/)** into your Eventhouse.

### 4. Vectorize & Index Policies

To enable the Data Agent to understand contractual warranties:

1. **Manage Policies:** The policy documents are version-controlled in the `/resources` folder of this repository.
2. **Upload to Lakehouse:** Upload these files from your local clone to your Lakehouse `Files/` directory so they are accessible to the Azure AI Search indexer.
3. **Index:** Configure an Azure AI Search indexer to vectorize these documents (e.g., using `text-embedding-3-large`).

### 5. Visualize Risks

Connect your Power BI reports/dashboards to the Eventhouse KQL endpoint to visualize live ship movements, high-risk zone infractions, and policy warranty breaches.

## 🛠 Prerequisites

* A **Microsoft Fabric** capacity (Trial or Premium).
* **Azure Key Vault** for secure credential management.
* **Azure AI Search** for policy vectorization.

## 👨‍💻 Author

**Dori Rabin** Cloud Solution Architect

