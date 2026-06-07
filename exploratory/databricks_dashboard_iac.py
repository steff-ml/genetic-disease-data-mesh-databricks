# Databricks AI/BI Dashboard — Infrastructure as Code
#
# This notebook walks through how to version-control and deploy a Databricks
# Lakeview (AI/BI) dashboard using Databricks Asset Bundles (DAB).
#
# WHAT IS A LAKEVIEW DASHBOARD
# =============================
# Lakeview is the current Databricks dashboard product (previously called
# "AI/BI Dashboards" in the UI). It replaced the legacy DBSQL dashboards in 2024.
# Lakeview dashboards:
#   - Are defined by a .lvdash.json file checked into source control
#   - Reference Unity Catalog tables via embedded SQL datasets
#   - Are deployed and updated via `databricks bundle deploy`
#   - Support draft/published states (draft = editors; published = viewers)
#
# WORKFLOW OVERVIEW
# =================
# 1. Build the dashboard interactively in the Databricks UI (fastest for first draft)
# 2. Export it to .lvdash.json via the SDK (Section 2 below)
# 3. Commit the JSON to this repo under dashboards/
# 4. Reference it in databricks.yml (Section 3 below)
# 5. All future changes go through git — the UI remains the visual editor,
#    but the source of truth is the JSON file in git
#
# RELATED FILES
# =============
# exploratory/dmd_dashboard_template.lvdash.json  — the dashboard JSON template
# databricks.yml                                  — root bundle (add dashboard resource here)
#
# DEPENDENCIES
# ============
# pip install databricks-sdk

# COMMAND ----------
# SECTION 1 — Connect to the workspace

from databricks.sdk import WorkspaceClient
from databricks.connect import DatabricksSession

# Using the profile configured in ~/.databrickscfg
w = WorkspaceClient(profile="steff_horemans")

# List existing Lakeview dashboards to confirm connectivity
dashboards = list(w.lakeview.list())
print(f"Found {len(dashboards)} Lakeview dashboards in workspace")
for d in dashboards[:5]:
    print(f"  {d.dashboard_id:>40}  {d.display_name}")

# COMMAND ----------
# SECTION 2 — Export an existing dashboard to JSON
#
# If you built a dashboard in the UI first, export it here and commit the JSON.
# This is the recommended starting workflow — design visually, then export to IaC.

def export_dashboard_to_json(dashboard_id: str, output_path: str) -> None:
    """
    Export a Lakeview dashboard by ID to a .lvdash.json file.
    Find the dashboard_id from the URL when viewing the dashboard:
        https://<host>/dashboardsv3/<dashboard_id>/published
    """
    import json

    dashboard = w.lakeview.get(dashboard_id=dashboard_id)
    serialized = dashboard.serialized_dashboard  # this is the JSON string

    with open(output_path, "w") as f:
        # Pretty-print for readability in git diffs
        f.write(json.dumps(json.loads(serialized), indent=2))

    print(f"Dashboard '{dashboard.display_name}' exported to {output_path}")
    print("Commit this file and reference it in databricks.yml.")


# REPLACE with your actual dashboard ID if you created one in the UI:
# export_dashboard_to_json(
#     dashboard_id="01ef1234-abcd-...",
#     output_path="dashboards/dmd_mutation_catalogue.lvdash.json",
# )

# COMMAND ----------
# SECTION 3 — Deploying via Databricks Asset Bundles
#
# Add this block to databricks.yml (root bundle) to declare the dashboard as a resource.
# The file_path must be relative to the databricks.yml location.
#
# ──────────────────────────────────────────────────────────────────────────────
# resources:
#   dashboards:
#     dmd_mutation_catalogue:
#       display_name: "DMD Mutation Catalogue"
#       file_path: ./dashboards/dmd_mutation_catalogue.lvdash.json
#       warehouse_id: ${var.sql_warehouse_id}   # warehouse used to run datasets
#       embed_credentials: false                # viewers use their own credentials
#       permissions:
#         - level: CAN_VIEW
#           group_name: researchers
#         - level: CAN_EDIT
#           group_name: platform_engineers
#
#     trial_eligibility_dashboard:
#       display_name: "Trial Eligibility Overview"
#       file_path: ./dashboards/trial_eligibility.lvdash.json
#       warehouse_id: ${var.sql_warehouse_id}
# ──────────────────────────────────────────────────────────────────────────────
#
# Add the variable to your targets section:
# ──────────────────────────────────────────────────────────────────────────────
# variables:
#   sql_warehouse_id:
#     description: "SQL warehouse used by dashboards"
#
# targets:
#   dev:
#     variables:
#       sql_warehouse_id: "<dev-warehouse-id>"
#   prod:
#     variables:
#       sql_warehouse_id: "<prod-warehouse-id>"
# ──────────────────────────────────────────────────────────────────────────────
#
# Deploy with:
#   databricks bundle deploy --target dev
#   databricks bundle deploy --target prod

# COMMAND ----------
# SECTION 4 — Create a dashboard programmatically (SDK, no UI)
#
# Use this if you want to generate dashboard JSON from code rather than the UI.
# Useful when the dashboard content is data-driven (e.g. one tab per exon).

import json

def create_dashboard_from_json(json_path: str, display_name: str) -> str:
    """
    Create (or update) a Lakeview dashboard from a .lvdash.json file.
    Returns the dashboard_id.

    Call this during pipeline development to iterate without touching the UI.
    In production, use `databricks bundle deploy` instead.
    """
    with open(json_path) as f:
        serialized = json.dumps(json.load(f))  # re-serialize to a JSON string

    # Check if a dashboard with this name already exists
    existing = [d for d in w.lakeview.list() if d.display_name == display_name]

    if existing:
        dashboard_id = existing[0].dashboard_id
        w.lakeview.update(
            dashboard_id=dashboard_id,
            display_name=display_name,
            serialized_dashboard=serialized,
        )
        print(f"Updated dashboard: {dashboard_id}")
    else:
        dashboard = w.lakeview.create(
            display_name=display_name,
            serialized_dashboard=serialized,
        )
        dashboard_id = dashboard.dashboard_id
        print(f"Created dashboard: {dashboard_id}")

    return dashboard_id


# COMMAND ----------
# SECTION 5 — Publish a dashboard (draft → published)
#
# Dashboards are created in draft state. Publish to make them visible to viewers.
# In production, publish as part of the CI/CD pipeline after validation.

def publish_dashboard(dashboard_id: str) -> None:
    """Publish a draft dashboard to make it visible to CAN_VIEW users."""
    w.lakeview.publish(dashboard_id=dashboard_id)
    print(f"Dashboard {dashboard_id} is now published.")


# COMMAND ----------
# SECTION 6 — Validate datasets in the dashboard JSON
#
# Before deploying, verify that every SQL dataset in the dashboard references
# tables that exist in Unity Catalog with the expected schema.

def validate_dashboard_datasets(json_path: str) -> None:
    """
    Parse the dashboard JSON and verify that each dataset SQL query references
    a table that exists in Unity Catalog.
    """
    import re

    with open(json_path) as f:
        dashboard = json.load(f)

    datasets = dashboard.get("datasets", [])
    print(f"Found {len(datasets)} datasets in {json_path}\n")

    spark = DatabricksSession.builder.profile("steff_horemans").serverless(True).getOrCreate()

    for ds in datasets:
        name  = ds.get("displayName", ds.get("name", "unknown"))
        query = ds.get("query", "")
        # Extract table references from the SQL (simple regex — catches most cases)
        tables = re.findall(r'\bFROM\s+([\w.]+)', query, re.IGNORECASE)
        tables += re.findall(r'\bJOIN\s+([\w.]+)', query, re.IGNORECASE)

        print(f"Dataset: {name}")
        for table in set(tables):
            try:
                spark.table(table).limit(0)
                print(f"  OK   {table}")
            except Exception as e:
                print(f"  FAIL {table}: {e}")
        print()
