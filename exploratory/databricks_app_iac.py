# Databricks App — Infrastructure as Code
#
# This notebook covers how to build, configure, and deploy a Databricks App
# using Databricks Asset Bundles (DAB). A Databricks App runs a web application
# (Streamlit, Gradio, Dash, Flask) directly on your Databricks workspace —
# no separate hosting infrastructure needed.
#
# WHEN TO USE A DATABRICKS APP (vs a Dashboard)
# ===============================================
# Use a Databricks Dashboard when:
#   - You need a read-only, shareable view of aggregated metrics
#   - Consumers are analysts or executives who don't need to interact
#   - Content is driven by SQL queries on Gold tables
#   - Examples: mutation catalogue overview, trial coverage heatmap
#
# Use a Databricks App when:
#   - You need interactivity beyond filters (form inputs, search, lookups)
#   - The use case is a workflow, not a report (e.g. a coordinator enters a
#     patient mutation and gets back trial eligibility results)
#   - You need to call Python functions, ML models, or external APIs at runtime
#   - Examples: patient-therapy matcher, trial eligibility checker
#
# For this DMD project, the patient-therapy matching use case (Phase 5) is
# the primary candidate for a Databricks App:
#   - Clinician enters a patient mutation (HGVS or exon range)
#   - App normalises the HGVS, looks up the reading frame effect
#   - App queries the Gold mutation catalogue and trial eligibility tables
#   - App returns a ranked list of matching trials and approved therapies
#
# ARCHITECTURE
# ============
# The app code runs as a Streamlit process on a Databricks cluster.
# It connects to Unity Catalog via Databricks Connect (DatabricksSession)
# using the app's service principal identity — no credentials in the code.
# The app YAML declares which SQL warehouses and clusters the app can access.
#
# DEPLOYMENT WORKFLOW
# ===================
# 1. Write the app code in apps/patient_matcher/app.py (see Section 2 below)
# 2. Write the app.yaml manifest (see exploratory/databricks_app.yaml)
# 3. Add the app to databricks.yml (see Section 3 below)
# 4. Deploy: databricks bundle deploy --target dev
# 5. Open: databricks bundle run dmd_patient_matcher_app --target dev
#
# RELATED FILES
# =============
# exploratory/databricks_app.yaml           — the app.yaml manifest template
# hub/templates/phi_access_control.py       — ABAC for patient data
# hub/templates/fhir_mapping.py             — FHIR API for EHR integration
#
# DEPENDENCIES (app runtime, not this notebook)
# =============================================
# streamlit>=1.30.0
# databricks-connect>=14.3
# databricks-sdk>=0.20.0

# COMMAND ----------
# SECTION 1 — Confirm Apps are available in your workspace

from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile="steff_horemans")

# List existing apps
try:
    apps = list(w.apps.list())
    print(f"Found {len(apps)} Databricks Apps in workspace")
    for app in apps:
        print(f"  {app.name:<40} status={app.app_status.state if app.app_status else 'unknown'}")
except Exception as e:
    print(f"Apps API not available or no apps deployed: {e}")

# COMMAND ----------
# SECTION 2 — Patient Therapy Matcher App (Streamlit)
#
# This is the app.py content for the patient-therapy matching use case.
# In production, this file lives at apps/patient_matcher/app.py.
# The code below is annotated for learning purposes.
#
# Copy it to apps/patient_matcher/app.py before deploying.

APP_CODE = '''
import streamlit as st
from databricks.connect import DatabricksSession

# DatabricksSession uses the app's service principal identity automatically
# when running inside a Databricks App. No credentials needed in code.
spark = DatabricksSession.builder.serverless(True).getOrCreate()

st.set_page_config(
    page_title="DMD Patient Therapy Matcher",
    page_icon=":dna:",
    layout="wide",
)

st.title("DMD Patient Therapy Matcher")
st.caption(
    "Enter a patient mutation to find matched clinical trials and approved therapies. "
    "Data sourced from the DMD Mutation Catalogue (Gold, last updated daily)."
)

# ── Input form ──────────────────────────────────────────────────────────────
with st.form("matcher_form"):
    col1, col2 = st.columns(2)

    with col1:
        hgvs_input = st.text_input(
            "HGVS cDNA notation",
            placeholder="e.g. NM_004006.2:c.6439del",
            help="Enter the canonical HGVS cDNA change. "
                 "Uncertain notation (e.g. c.(?_432-1)_(6438+1_?)del) is also accepted.",
        )

    with col2:
        exon_range = st.text_input(
            "Affected exon range (optional fallback)",
            placeholder="e.g. 45-52",
            help="If the HGVS cannot be parsed, the exon range is used as a fallback "
                 "for reading frame calculation.",
        )

    submitted = st.form_submit_button("Find matches")

# ── Results ─────────────────────────────────────────────────────────────────
if submitted and hgvs_input:
    # Step 1: normalise HGVS
    import sys
    sys.path.insert(0, "/Workspace/Users/steffhoremans@yahoo.com/hub/templates")
    from hgvs_normalization import normalize_hgvs

    with st.spinner("Normalising HGVS notation..."):
        norm = normalize_hgvs(hgvs_input.strip(), exon_range.strip() or None)

    if norm.unparseable:
        st.error(
            f"Could not parse the HGVS notation: {norm.parse_error}. "
            "Check the notation and try again, or enter an exon range as fallback."
        )
        st.stop()

    st.success(
        f"Normalised: **{norm.canonical_hgvs}** "
        f"(strategy: {norm.strategy}, type: {norm.mutation_type})"
    )

    # Step 2: look up matching variants in Gold
    with st.spinner("Querying mutation catalogue..."):
        matches = spark.sql(f"""
            SELECT
                canonical_hgvs,
                clinical_significance,
                reading_frame_effect,
                classification_conflict,
                vrs_allele_id
            FROM discovery.gold.dmd_mutation_catalogue
            WHERE canonical_hgvs = '{norm.canonical_hgvs}'
               OR (cdna_start BETWEEN {norm.cdna_start or 0} AND {norm.cdna_end or 0}
                   AND mutation_type = '{norm.mutation_type}')
            LIMIT 10
        """).toPandas()

    if matches.empty:
        st.warning(
            "No exact match found in the mutation catalogue. "
            "The variant may be novel or not yet curated."
        )
    else:
        st.subheader("Catalogue Match")
        st.dataframe(matches, use_container_width=True)

    # Step 3: query trial eligibility
    reading_frame = matches["reading_frame_effect"].iloc[0] if not matches.empty else None

    with st.spinner("Matching clinical trials..."):
        trials = spark.sql(f"""
            SELECT
                nct_id,
                title,
                phase,
                status,
                mutation_type_required,
                reading_frame_required,
                aon_exon_target
            FROM clinical.gold.trial_eligibility_catalogue
            WHERE (mutation_type_required = '{norm.mutation_type}' OR mutation_type_required = 'any')
              AND (reading_frame_required = '{reading_frame}' OR reading_frame_required IS NULL)
              AND status = 'Recruiting'
            ORDER BY phase
        """).toPandas()

    st.subheader(f"Matching Recruiting Trials ({len(trials)} found)")
    if trials.empty:
        st.info("No recruiting trials found for this mutation profile.")
    else:
        st.dataframe(trials, use_container_width=True)

    # Step 4: approved therapies
    with st.spinner("Checking approved therapies..."):
        therapies = spark.sql(f"""
            SELECT
                drug_name,
                approval_status,
                mutation_type_covered,
                exon_target,
                prescribing_note
            FROM clinical.gold.approved_therapies
            WHERE mutation_type_covered = '{norm.mutation_type}'
        """).toPandas()

    st.subheader(f"Approved Therapies ({len(therapies)} found)")
    if therapies.empty:
        st.info("No approved therapies found for this mutation type.")
    else:
        st.dataframe(therapies, use_container_width=True)

    st.caption(
        "Data is refreshed daily. Classification conflicts are excluded from trial matching. "
        "This tool is for research and clinical support — it does not constitute medical advice."
    )
'''

print("App code preview (first 30 lines):")
print("\n".join(APP_CODE.strip().splitlines()[:30]))

# COMMAND ----------
# SECTION 3 — Adding the App to databricks.yml
#
# Add this block to the root databricks.yml (or to a sub-bundle in apps/).
# The source_code_path points to the directory containing app.py and app.yaml.
#
# ──────────────────────────────────────────────────────────────────────────────
# resources:
#   apps:
#     dmd_patient_matcher:
#       name: dmd-patient-matcher        # URL slug — must be unique in workspace
#       description: "DMD patient mutation to trial and therapy matching app"
#       source_code_path: ./apps/patient_matcher
#
#       # Grant the app's service principal access to the SQL warehouses it needs
#       resources:
#         - name: mutation_catalogue_warehouse
#           sql_warehouse:
#             id: ${var.sql_warehouse_id}
#             permission: CAN_USE
#
#       permissions:
#         - level: CAN_USE
#           group_name: clinical_coordinators
#         - level: CAN_USE
#           group_name: researchers
#         - level: CAN_MANAGE
#           group_name: platform_engineers
# ──────────────────────────────────────────────────────────────────────────────
#
# Directory structure expected by the bundle:
#   apps/
#     patient_matcher/
#       app.py            ← the Streamlit code (copy APP_CODE above)
#       app.yaml          ← the app manifest (see exploratory/databricks_app.yaml)
#       requirements.txt  ← app runtime dependencies

# COMMAND ----------
# SECTION 4 — Deploy and manage the app via CLI
#
# Deploy the app (creates or updates):
#   databricks bundle deploy --target dev
#
# Start the app (if it was stopped):
#   databricks apps start dmd-patient-matcher
#
# Check app status:
#   databricks apps get dmd-patient-matcher
#
# View logs (useful for debugging startup errors):
#   databricks apps logs dmd-patient-matcher --follow
#
# Stop the app to save compute costs when not in use:
#   databricks apps stop dmd-patient-matcher
#
# Note: Apps on serverless compute scale to zero automatically when inactive.
# There is no need to manually stop a serverless app to avoid charges.

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import App

def get_app_url(app_name: str) -> str:
    """Return the URL of a deployed Databricks App."""
    w = WorkspaceClient(profile="steff_horemans")
    try:
        app = w.apps.get(app_name)
        return app.url or f"App {app_name} found but URL not yet available"
    except Exception as e:
        return f"App not found: {e}"

# print(get_app_url("dmd-patient-matcher"))
