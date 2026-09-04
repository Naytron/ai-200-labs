# -*- coding: utf-8 -*-
# Domain 4 - Secure, monitor, and troubleshoot Azure solutions (20-25%)

DOMAIN = {
    "key": "secure",
    "name": "Secure, Monitor and Troubleshoot Azure Solutions",
    "weight": "20\u201325%",
    "blurb": "Secure Azure AI solutions by retrieving and rotating secrets in Key Vault, externalizing labeled settings in App Configuration, authenticating with managed identity instead of passwords, tracing distributed calls with OpenTelemetry, and using KQL over Application Insights / Log Analytics logs and metrics to isolate failures, latency and correlation IDs.",
}

LABS = [
# ---------------------------------------------------------------- 4.1
{
"id": "4.1",
"title": "Secure secrets with Azure Key Vault: retrieval and rotation",
"time": "30 min",
"level": "Foundational",
"objective": "Create an RBAC-based Key Vault, store and retrieve versioned secrets, and model manual plus event-driven rotation.",
"exam": [
 "Azure RBAC is the recommended authorization model for new vaults; access policies remain supported for legacy compatibility. Read secrets with <b>Key Vault Secrets User</b>; create / rotate them with <b>Key Vault Secrets Officer</b>.",
 "A secret update creates a <b>new version</b>. A versionless <code>get_secret(name)</code> retrieves the latest version, not the latest enabled version. If it is disabled, the call fails instead of falling back; a version-pinned client keeps using its specified version.",
 "<b>Soft-delete</b> is always on for new vaults. <b>Purge protection</b> is optional, irreversible once enabled, and commonly required for production / compliance.",
 "Rotation pattern: set an expiry on the secret, subscribe Key Vault events to <code>Microsoft.KeyVault.SecretNearExpiry</code>, and invoke an Azure Function that writes a new version.",
 "Secret values should be retrieved at runtime through <code>DefaultAzureCredential</code>; never copy them into app settings, source code or container images.",
],
"prereq": "An Azure subscription, Azure CLI 2.x, and permission to create role assignments. For Python: <code>pip install azure-identity azure-keyvault-secrets</code>.",
"portal": [
 "##Create an RBAC vault",
 "Azure portal \u2192 search <b>Key vaults</b> \u2192 <b>+ Create</b>. RG <code>rg-ai200-secure</code>, name <code>ai200kv&lt;unique&gt;</code>, region near your app.",
 "On <b>Access configuration</b>, choose <b>Azure role-based access control</b>. Leave soft-delete enabled; enable <b>Purge protection</b> for production-like practice.",
 "Vault \u2192 <b>Access control (IAM)</b> \u2192 assign yourself <b>Key Vault Secrets Officer</b> so you can create and rotate secrets.",
 "##Create and read a secret",
 "Vault \u2192 <b>Objects \u2192 Secrets</b> \u2192 <b>+ Generate/Import</b>. Name <code>openai-api-key</code>, value a lab placeholder, set an <b>Expiration date</b>.",
 "Open the secret \u2192 note <b>Current Version</b> and the versioned <b>Secret Identifier</b>. Create a new version by selecting <b>New Version</b>.",
 "Assign the consuming app identity <b>Key Vault Secrets User</b> at the vault scope, then retrieve the secret with the SDK or a Key Vault reference.",
 "##Wire rotation",
 "Vault \u2192 <b>Events</b> \u2192 <b>+ Event Subscription</b>. Event type <code>Secret Near Expiry</code>, endpoint type <b>Azure Function</b>.",
 "The function should validate the event, generate / fetch the replacement credential from the backing service, then call <code>set_secret</code> to create a new secret version.",
],
"cli": r"""RG=rg-ai200-secure
LOC=eastus
KV=ai200kv$RANDOM

az group create -n $RG -l $LOC

# --- Create a vault that uses Azure RBAC for the data plane ----------
# Soft-delete is always on; purge protection is optional but exam-relevant.
az keyvault create -g $RG -n $KV -l $LOC \
  --enable-rbac-authorization true \
  --retention-days 90 \
  --enable-purge-protection true

VAULT_ID=$(az keyvault show -g $RG -n $KV --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)

# Writer / rotator role: can set and version secrets.
az role assignment create \
  --assignee $ME \
  --role "Key Vault Secrets Officer" \
  --scope $VAULT_ID

# Allow RBAC propagation before the first data-plane call.
sleep 60

# --- Set v1 with an expiry so near-expiry rotation can fire ----------
EXPIRY=$(date -u -d "+30 days" +%Y-%m-%dT%H:%M:%SZ)
az keyvault secret set --vault-name $KV \
  --name openai-api-key \
  --value "lab-v1-$RANDOM" \
  --expires "$EXPIRY"

# Latest-version retrieval (what most apps should do).
az keyvault secret show --vault-name $KV \
  --name openai-api-key \
  --query "{id:id,value:value,expires:attributes.expires}" -o json

# --- Rotate manually: same name, new version ------------------------
az keyvault secret set --vault-name $KV \
  --name openai-api-key \
  --value "lab-v2-$RANDOM" \
  --expires "$(date -u -d "+60 days" +%Y-%m-%dT%H:%M:%SZ)"

az keyvault secret list-versions --vault-name $KV \
  --name openai-api-key -o table

# Reader can retrieve values individually; list operations return metadata only.
az role assignment create \
  --assignee-object-id <app-managed-identity-object-id> \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope $VAULT_ID

# --- Event-driven rotation pattern ---------------------------------
# SecretNearExpiry -> Azure Function. The Function writes a new version.
az eventgrid event-subscription create \
  --name rotate-openai-key-near-expiry \
  --source-resource-id $VAULT_ID \
  --included-event-types Microsoft.KeyVault.SecretNearExpiry \
  --endpoint 'https://<function-app>.azurewebsites.net/runtime/webhooks/EventGrid?functionName=RotateSecret&code=<function-key>'""",
"code": r"""# pip install azure-identity azure-keyvault-secrets
# Exam point: DefaultAzureCredential uses managed identity in Azure and your
# developer login locally; no secret value belongs in code or app settings.

import os
from datetime import datetime, timedelta, timezone

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

vault_name = os.environ["KEY_VAULT_NAME"]
secret_name = os.environ.get("SECRET_NAME", "openai-api-key")

credential = DefaultAzureCredential()
client = SecretClient(
    vault_url=f"https://{vault_name}.vault.azure.net",
    credential=credential,
)

# Read the latest version. This does not search backward for an enabled version.
latest = client.get_secret(secret_name)
print(f"Using {secret_name} version {latest.properties.version}")

# Pinning is explicit. Most production apps should avoid pinning unless a
# controlled rollout needs a specific version.
same_version = client.get_secret(secret_name, latest.properties.version)
assert same_version.value == latest.value

# Manual rotation: setting the same name creates a new version.
rotated = client.set_secret(
    secret_name,
    os.environ["NEW_SECRET_VALUE"],
    expires_on=datetime.now(timezone.utc) + timedelta(days=60),
    tags={"rotated-by": "ai200-lab"},
)
print(f"Rotated to version {rotated.properties.version}")

print("Known versions:")
for props in client.list_properties_of_secret_versions(secret_name):
    print(props.version, "enabled=", props.enabled, "expires_on=", props.expires_on)


# Azure Function Event Grid handler sketch for SecretNearExpiry.
# The real handler would generate the replacement in the source system first.
def rotate_on_near_expiry(event):
    if event.event_type != "Microsoft.KeyVault.SecretNearExpiry":
        return

    near_expiry_name = event.subject.rsplit("/", 1)[-1]
    replacement = os.environ["NEW_SECRET_VALUE"]
    client.set_secret(
        near_expiry_name,
        replacement,
        expires_on=datetime.now(timezone.utc) + timedelta(days=90),
    )""",
"code_label": "Python / SDK",
"traps": [
 "Choosing <b>Access policies</b> when the scenario says centralized RBAC / least privilege is usually wrong. Access policies are legacy and managed on the vault, not through Azure IAM.",
 "<b>Key Vault Secrets User</b> can read secret values but cannot rotate them; <b>Key Vault Secrets Officer</b> can set versions but is too broad for a runtime app.",
 "Deleting a secret does not immediately destroy it because soft-delete is on. With purge protection enabled, even privileged users cannot purge until retention expires.",
 "A Key Vault <b>reference</b> or App Configuration Key Vault reference stores a URI, not the secret value. The consuming app still needs permission to the vault.",
 "A near-expiry event does not rotate anything by itself \u2014 Event Grid only notifies; your Function performs the credential replacement and <code>set_secret</code> call.",
],
"cleanup": r"""# Deferred: Labs 4.2 and 4.3 reuse this vault and resource group.
# Run the consolidated secure-resource cleanup after Lab 4.3.""",
},
# ---------------------------------------------------------------- 4.2
{
"id": "4.2",
"title": "Externalize configuration with Azure App Configuration",
"time": "30 min",
"level": "Core",
"objective": "Store labeled application settings and feature flags in App Configuration, reference Key Vault secrets, and reload configuration with a sentinel key.",
"exam": [
 "<b>App Configuration</b> is for non-secret settings, feature flags and central configuration; <b>Key Vault</b> is for secrets, keys and certificates. Do not store raw secrets as App Configuration values.",
 "<b>Labels</b> separate environments or rings: the same key can have label <code>dev</code>, <code>test</code> and <code>prod</code> with different values.",
 "Feature flags are first-class App Configuration entries and can be labeled just like key-values.",
 "A <b>Key Vault reference</b> stores the secret URI in App Configuration. The app resolves the secret at runtime and needs <b>Key Vault Secrets User</b> on the vault.",
 "Dynamic configuration can use a watched <b>sentinel key</b> for coherent App Configuration reloads. Rotation of a versionless Key Vault secret is independent: configure <code>secret_refresh_interval</code> and call <code>refresh()</code> during application activity.",
],
"prereq": "An App Configuration store and a Key Vault secret from Lab 4.1. For Python: <code>pip install \"azure-appconfiguration-provider&gt;=2.5.0,&lt;3\" azure-identity</code>.",
"portal": [
 "##Create the store",
 "Azure portal \u2192 search <b>App Configuration</b> \u2192 <b>+ Create</b>. RG <code>rg-ai200-secure</code>, name <code>ai200appcfg&lt;unique&gt;</code>, region near the app.",
 "Store \u2192 <b>Access control (IAM)</b> \u2192 assign your user <b>App Configuration Data Owner</b> for lab writes and the app identity <b>App Configuration Data Reader</b> for runtime reads.",
 "##Add labeled key-values",
 "Store \u2192 <b>Operations \u2192 Configuration explorer</b> \u2192 <b>+ Create \u2192 Key-value</b>. Add <code>Settings:ModelDeployment</code> with label <code>dev</code> and value <code>gpt-4o-mini</code>.",
 "Add the same key with label <code>prod</code> and value <code>gpt-4o</code>. Add <code>Settings:Sentinel</code> with label <code>dev</code> and value <code>1</code>.",
 "##Feature flags and Key Vault references",
 "Store \u2192 <b>Operations \u2192 Feature manager</b> \u2192 <b>+ Create</b>. Feature flag <code>BetaChat</code>, label <code>dev</code>, enabled.",
 "Configuration explorer \u2192 <b>+ Create \u2192 Key vault reference</b>. Key <code>Secrets:OpenAIKey</code>, label <code>dev</code>, select the Key Vault secret URI.",
 "Grant the consuming app identity <b>Key Vault Secrets User</b> on the vault; App Configuration stores only the reference and cannot bypass Key Vault authorization.",
 "##Refresh safely",
 "Change one or more labeled settings, then update <code>Settings:Sentinel</code>. Clients watching that sentinel reload the whole selected configuration set.",
],
"cli": r"""RG=rg-ai200-secure
LOC=eastus
APPCFG=ai200appcfg$RANDOM
KV="<your-keyvault-name>"

az group create -n $RG -l $LOC
az appconfig create -g $RG -n $APPCFG -l $LOC --sku Standard

STORE_ID=$(az appconfig show -g $RG -n $APPCFG --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)

# Data Owner can write key-values through Entra ID auth.
az role assignment create \
  --assignee $ME \
  --role "App Configuration Data Owner" \
  --scope $STORE_ID

sleep 60

# --- Same key, different labels for environment-specific values -----
az appconfig kv set --name $APPCFG --auth-mode login \
  --key Settings:ModelDeployment --label dev --value gpt-4o-mini --yes

az appconfig kv set --name $APPCFG --auth-mode login \
  --key Settings:ModelDeployment --label prod --value gpt-4o --yes

# Sentinel: clients refresh all selected settings when this changes.
az appconfig kv set --name $APPCFG --auth-mode login \
  --key Settings:Sentinel --label dev --value 1 --yes

# --- Feature flag ---------------------------------------------------
az appconfig feature set --name $APPCFG --auth-mode login \
  --feature BetaChat --label dev --yes

az appconfig feature enable --name $APPCFG --auth-mode login \
  --feature BetaChat --label dev --yes

# --- Key Vault reference: reference only, not the secret value -------
# Key Vault returns a versioned ID; remove the final /<version> segment.
VERSIONED_SECRET_ID=$(az keyvault secret show --vault-name "$KV" \
  --name openai-api-key --query id -o tsv)
SECRET_URI="${VERSIONED_SECRET_ID%/*}"

az appconfig kv set-keyvault --name $APPCFG --auth-mode login \
  --key Secrets:OpenAIKey --label dev \
  --secret-identifier "$SECRET_URI" --yes

az appconfig kv list --name $APPCFG --auth-mode login \
  --label dev -o table

# The identity resolving configuration needs data access to both services.
APP_PRINCIPAL_ID="<app-managed-identity-object-id>"
VAULT_ID=$(az keyvault show -g "$RG" -n "$KV" --query id -o tsv)

az role assignment create \
  --assignee-object-id "$APP_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "App Configuration Data Reader" \
  --scope "$STORE_ID"

az role assignment create \
  --assignee-object-id "$APP_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope "$VAULT_ID"
""",
"code": r"""# pip install "azure-appconfiguration-provider>=2.5.0,<3" azure-identity

import os

from azure.appconfiguration.provider import SettingSelector, WatchKey, load
from azure.identity import DefaultAzureCredential

endpoint = os.environ["APPCONFIG_ENDPOINT"]
label = os.environ.get("APPCONFIG_LABEL", "dev")
credential = DefaultAzureCredential()

config = load(
    endpoint=endpoint,
    credential=credential,
    selects=[
        SettingSelector(key_filter="Settings:*", label_filter=label),
        SettingSelector(key_filter="Secrets:*", label_filter=label),
    ],
    trim_prefixes=["Settings:", "Secrets:"],

    # Resolve Key Vault references with the same identity.
    keyvault_credential=credential,

    # Re-resolve versionless secrets when refresh() is called after this interval,
    # even when no App Configuration key-value changed.
    secret_refresh_interval=300,

    # WatchKey uses the original key and label.
    refresh_on=[WatchKey("Settings:Sentinel", label)],
    refresh_interval=30,
    refresh_enabled=True,

    feature_flag_enabled=True,
    feature_flag_selectors=[
        SettingSelector(key_filter="BetaChat", label_filter=label),
    ],
    feature_flag_refresh_enabled=True,
)


def current_values():
    # Call during application activity. Before an interval expires this returns
    # without issuing the corresponding service request.
    config.refresh()

    flags = config["feature_management"]["feature_flags"]
    beta_enabled = next(
        (flag["enabled"] for flag in flags if flag["id"] == "BetaChat"),
        False,
    )

    # Resolve the secret but never print or copy it into app settings.
    openai_key = config["OpenAIKey"]
    return config["ModelDeployment"], beta_enabled, openai_key


model, beta_enabled, openai_key = current_values()
print(model, "beta=", beta_enabled)""",
"code_label": "Python / SDK",
"traps": [
 "Labels are not hierarchy. <code>Settings:ModelDeployment</code> with label <code>prod</code> is a different setting version than the same key with label <code>dev</code>.",
 "App Configuration <b>access keys</b> work, but managed identity + <b>App Configuration Data Reader</b> is the secure answer for Azure-hosted apps.",
 "A Key Vault reference failing at runtime is usually a missing <b>Key Vault Secrets User</b> assignment for the app identity, not an App Configuration problem.",
 "A sentinel detects App Configuration changes; it does not by itself detect rotation behind an unchanged Key Vault reference. Use a <b>versionless</b> secret URI, <code>secret_refresh_interval</code>, and activity-driven <code>refresh()</code> calls.",
 "Feature flags live in App Configuration; Key Vault is not a feature-management service.",
],
"cleanup": r"""# Deferred: retain the App Configuration store through Lab 4.3.
# Run the consolidated secure-resource cleanup after Lab 4.3.""",
},
# ---------------------------------------------------------------- 4.3
{
"id": "4.3",
"title": "Access Azure services without secrets using managed identity",
"time": "30 min",
"level": "Core",
"objective": "Enable system- and user-assigned managed identities, grant data-plane RBAC, and use Azure SDK credentials without storing service keys.",
"exam": [
 "<b>Managed identity</b> gives an Azure resource an Entra identity. <b>System-assigned</b> is tied to one resource lifecycle; <b>user-assigned</b> is reusable across resources.",
 "<code>DefaultAzureCredential</code> uses managed identity when running in Azure and developer credentials such as <code>az login</code> locally. The same code can run in both places.",
 "Identity is only authentication. You still must grant <b>data-plane RBAC</b>, such as <b>Key Vault Secrets User</b> or <b>Cosmos DB Built-in Data Reader</b>.",
 "For user-assigned managed identity, pass its <b>client ID</b> to the credential or set <code>AZURE_CLIENT_ID</code>; otherwise the platform cannot choose among multiple identities.",
 "Service keys, connection strings and client secrets are distractors when the scenario says 'no secrets in code' or 'rotate credentials centrally'.",
],
"prereq": "An Azure-hosted app resource such as App Service, Container Apps, Functions or VM. Optional Cosmos DB for NoSQL account for the data-reader example.",
"portal": [
 "##Enable the identities",
 "App Service / Function / Container App \u2192 <b>Identity</b> \u2192 <b>System assigned</b> \u2192 On \u2192 Save. Copy the <b>Object (principal) ID</b>.",
 "For shared identity, portal \u2192 search <b>Managed identities</b> \u2192 <b>+ Create</b> user-assigned identity, then attach it from the app's <b>User assigned</b> identity tab.",
 "##Grant Key Vault data-plane access",
 "Key Vault \u2192 <b>Access control (IAM)</b> \u2192 <b>+ Add role assignment</b> \u2192 <b>Key Vault Secrets User</b> \u2192 select the managed identity.",
 "Do not add a vault access policy unless the vault is explicitly using the legacy access-policy model.",
 "##Grant Cosmos DB data-plane access",
 "Cosmos DB account \u2192 <b>Access control (IAM)</b> controls management-plane access; for NoSQL data access use the account's <b>Data Explorer / Role assignments</b> or the CLI SQL role assignment.",
 "Assign <b>Cosmos DB Built-in Data Reader</b> at scope <code>/</code> to the app identity for read-only SDK queries. If you run the optional query locally, assign the same role separately to your signed-in developer identity. Use Data Contributor only if the app writes items.",
 "##Run locally and in Azure",
 "Local developer machine: run <code>az login</code> and grant that developer the required data-plane roles. Azure runtime: no login command and no secret; the SDK requests a token from the managed identity endpoint. Authentication never substitutes for authorization.",
],
"cli": r"""LAB_RG=rg-ai200-secure
APP_RG="<resource-group-containing-your-webapp>"
COSMOS_RG="" # Optional: set to the resource group from Lab 2.1.
APP="<your-webapp-name>"
KV="<your-keyvault-name>"
COSMOS="" # Optional: set to the account from Lab 2.1.
UAMI=id-ai200-reader

VAULT_ID=$(az keyvault show -g "$LAB_RG" -n "$KV" --query id -o tsv)

# --- System-assigned managed identity ------------------------------
az webapp identity assign -g "$APP_RG" -n "$APP"
SYSTEM_PRINCIPAL_ID=$(az webapp identity show -g "$APP_RG" -n "$APP" \
  --query principalId -o tsv)

az role assignment create \
  --assignee-object-id "$SYSTEM_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope "$VAULT_ID"

# --- User-assigned identity selected by AZURE_CLIENT_ID -------------
az identity create -g "$LAB_RG" -n "$UAMI"
UAMI_ID=$(az identity show -g "$LAB_RG" -n "$UAMI" --query id -o tsv)
UAMI_CLIENT_ID=$(az identity show -g "$LAB_RG" -n "$UAMI" \
  --query clientId -o tsv)
UAMI_PRINCIPAL_ID=$(az identity show -g "$LAB_RG" -n "$UAMI" \
  --query principalId -o tsv)

az webapp identity assign -g "$APP_RG" -n "$APP" \
  --identities "$UAMI_ID"

az webapp config appsettings set -g "$APP_RG" -n "$APP" \
  --settings AZURE_CLIENT_ID="$UAMI_CLIENT_ID"

# The selected UAMI, not only the system identity, must read secrets.
az role assignment create \
  --assignee-object-id "$UAMI_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" \
  --scope "$VAULT_ID"

# --- Optional Cosmos DB for NoSQL data-plane RBAC -------------------
COSMOS_ROLE_ASSIGNMENT_ID=""
COSMOS_LOCAL_ROLE_ASSIGNMENT_ID=""
if [[ -n "$COSMOS_RG" && -n "$COSMOS" ]]; then
  # Reproducible UUIDv5 values prevent duplicate assignments on reruns.
  # The deployed app uses the user-assigned identity.
  COSMOS_ROLE_ASSIGNMENT_ID=$(python -c "import uuid; print(uuid.uuid5(uuid.NAMESPACE_URL, 'ai200-cosmos:$COSMOS:$UAMI_PRINCIPAL_ID:reader'))")
  az cosmosdb sql role assignment create \
    -g "$COSMOS_RG" -a "$COSMOS" \
    --role-assignment-id "$COSMOS_ROLE_ASSIGNMENT_ID" \
    --role-definition-name "Cosmos DB Built-in Data Reader" \
    --scope "/" \
    --principal-id "$UAMI_PRINCIPAL_ID"

  # Local DefaultAzureCredential uses the signed-in developer, not the UAMI.
  LOCAL_USER_ID=$(az ad signed-in-user show --query id -o tsv)
  COSMOS_LOCAL_ROLE_ASSIGNMENT_ID=$(python -c "import uuid; print(uuid.uuid5(uuid.NAMESPACE_URL, 'ai200-cosmos:$COSMOS:$LOCAL_USER_ID:reader'))")
  az cosmosdb sql role assignment create \
    -g "$COSMOS_RG" -a "$COSMOS" \
    --role-assignment-id "$COSMOS_LOCAL_ROLE_ASSIGNMENT_ID" \
    --role-definition-name "Cosmos DB Built-in Data Reader" \
    --scope "/" \
    --principal-id "$LOCAL_USER_ID"

  echo "Save for cleanup:"
  echo "COSMOS_ROLE_ASSIGNMENT_ID=$COSMOS_ROLE_ASSIGNMENT_ID"
  echo "COSMOS_LOCAL_ROLE_ASSIGNMENT_ID=$COSMOS_LOCAL_ROLE_ASSIGNMENT_ID"
fi
sleep 60""",
"code": r"""# pip install azure-identity azure-keyvault-secrets azure-cosmos
# One credential object, no service keys. In Azure this uses managed identity;
# locally it falls through to Azure CLI / developer credentials after az login.

import os

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

managed_identity_client_id = os.getenv("AZURE_CLIENT_ID")  # required for user-assigned MI

credential = DefaultAzureCredential(
    managed_identity_client_id=managed_identity_client_id,
)

vault = SecretClient(
    vault_url=os.environ["KEY_VAULT_URL"],
    credential=credential,
)

secret = vault.get_secret("openai-api-key")
print("Loaded secret version", secret.properties.version)

# Optional: if Lab 2.1's endpoint is configured, read its existing container.
cosmos_endpoint = os.getenv("COSMOS_ENDPOINT")
if cosmos_endpoint:
    cosmos = CosmosClient(cosmos_endpoint, credential=credential)
    container = cosmos.get_database_client("appdb").get_container_client("documents")
    for item in container.query_items(
        query="SELECT TOP 5 c.id, c.title FROM c",
        enable_cross_partition_query=True,
    ):
        print(item)


# If you want to fail fast unless the code is running in Azure, use this
# instead of DefaultAzureCredential. It will NOT use az login locally.
azure_only_credential = ManagedIdentityCredential(
    client_id=managed_identity_client_id,
)""",
"code_label": "Python / SDK",
"traps": [
 "A managed identity existing on the app is not enough. Missing <b>data-plane</b> roles cause 403 errors even though token acquisition succeeds.",
 "<b>Reader</b> on the resource group is management-plane read access, not permission to read Key Vault secret values or Cosmos DB items.",
 "With multiple user-assigned identities attached, <code>DefaultAzureCredential</code> needs the client ID. Object ID and client ID are different values.",
 "Local <code>az login</code> selects the developer identity but does not authorize it; that developer needs its own data-plane roles. It also grants the deployed app nothing, so the app principal needs separate assignments.",
 "Connection strings are the wrong answer when the requirement says no credential rotation burden or no secrets in code.",
],
"cleanup": r"""# Run only after Labs 4.1-4.3 are complete.
# If AZURE_CLIENT_ID existed before this lab, restore its previous value instead.
az webapp config appsettings delete \
  -g "$APP_RG" -n "$APP" --setting-names AZURE_CLIENT_ID

if [[ -n "${COSMOS_ROLE_ASSIGNMENT_ID:-}" ]]; then
  az cosmosdb sql role assignment delete \
    -g "$COSMOS_RG" -a "$COSMOS" \
    --role-assignment-id "$COSMOS_ROLE_ASSIGNMENT_ID" --yes
fi

if [[ -n "${COSMOS_LOCAL_ROLE_ASSIGNMENT_ID:-}" ]]; then
  az cosmosdb sql role assignment delete \
    -g "$COSMOS_RG" -a "$COSMOS" \
    --role-assignment-id "$COSMOS_LOCAL_ROLE_ASSIGNMENT_ID" --yes
fi

az webapp identity remove \
  -g "$APP_RG" -n "$APP" --identities "$UAMI_ID"

# Disable the system identity only if this lab originally enabled it:
# az webapp identity remove -g "$APP_RG" -n "$APP" --identities '[system]'

# Confirm this group contains only lab-created resources before deleting it.
az resource list -g "$LAB_RG" -o table
az group delete -n "$LAB_RG" --yes --no-wait

# The purge-protected vault remains soft-deleted for its 90-day retention and
# cannot be purged early. App Configuration is also soft-deleted.""",
},
# ---------------------------------------------------------------- 4.4
{
"id": "4.4",
"title": "Distributed tracing with OpenTelemetry and Azure Monitor",
"time": "35 min",
"level": "Advanced",
"objective": "Instrument a Python service with OpenTelemetry, export spans as request/dependency telemetry and Python logs as trace telemetry, and correlate them in Application Insights.",
"exam": [
 "An OpenTelemetry distributed trace consists of <b>spans</b>. In Application Insights, spans map primarily to <code>requests</code>/<code>dependencies</code>; Python logging records map to <code>traces</code>/<code>AppTraces</code>.",
 "The Azure Monitor distro is <code>azure-monitor-opentelemetry</code>. Calling <code>configure_azure_monitor()</code> wires exporters and common auto-instrumentation.",
 "Application Insights ingestion uses <code>APPLICATIONINSIGHTS_CONNECTION_STRING</code>, not the old instrumentation key-only pattern.",
 "Trace context propagates through W3C <code>traceparent</code> headers so downstream services and HTTP dependencies share the same operation / trace.",
 "Application Insights correlates request/dependency spans, application logs and exceptions through operation and parent identifiers.",
],
"prereq": "An Azure Monitor Application Insights resource. For Python: <code>pip install azure-monitor-opentelemetry flask requests</code>.",
"portal": [
 "##Create Application Insights",
 "Azure portal \u2192 <b>Application Insights</b> \u2192 <b>+ Create</b>. Use a workspace-based resource connected to a Log Analytics workspace.",
 "Open the resource \u2192 <b>Overview</b> \u2192 copy the <b>Connection String</b>. Set it as <code>APPLICATIONINSIGHTS_CONNECTION_STRING</code> in your app settings.",
 "##Instrument and run",
 "Add <code>configure_azure_monitor()</code> at app startup before the framework begins handling requests.",
 "Create custom spans around important AI calls, storage calls or orchestration steps; add attributes that help troubleshooting and filtering.",
 "The bundled Requests instrumentation creates the HTTP client span and injects W3C context automatically. Use manual injection only for an uninstrumented transport\u2014do not do both.",
 "##Inspect correlation",
 "Application Insights \u2192 <b>Investigate \u2192 Search</b> \u2192 select a request or dependency \u2192 open its end-to-end transaction details.",
 "Application Insights \u2192 <b>Application map</b> shows caller / dependency relationships. <b>Failures</b> highlights failed requests and dependency failures.",
 "Application Insights \u2192 <b>Logs</b> \u2192 query request/dependency spans in <code>requests</code>/<code>dependencies</code>, application logs in <code>traces</code>, and errors in <code>exceptions</code> by <code>operation_Id</code>.",
],
"cli": r"""MONITOR_RG=rg-ai200-monitor
APP_RG="<resource-group-containing-your-webapp>"
LOC=eastus
LAW=law-ai200-$RANDOM
AI=appi-ai200-$RANDOM
APP="<your-webapp-name>"

az group create -n "$MONITOR_RG" -l "$LOC"

# Workspace-based Application Insights is the modern Azure Monitor pattern.
az monitor log-analytics workspace create \
  -g "$MONITOR_RG" -n "$LAW" -l "$LOC"
LAW_ID=$(az monitor log-analytics workspace show -g "$MONITOR_RG" -n "$LAW" \
  --query id -o tsv)

az extension add -n application-insights --upgrade
az monitor app-insights component create \
  --app "$AI" \
  --location "$LOC" \
  --resource-group "$MONITOR_RG" \
  --workspace "$LAW_ID" \
  --application-type web

CONN=$(az monitor app-insights component show -g "$MONITOR_RG" --app "$AI" \
  --query connectionString -o tsv)

# App Service deployment:
az webapp config appsettings set -g "$APP_RG" -n "$APP" \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="$CONN"

# Local alternative:
export APPLICATIONINSIGHTS_CONNECTION_STRING="$CONN"

APP_ID=$(az monitor app-insights component show -g "$MONITOR_RG" --app "$AI" \
  --query appId -o tsv)

az monitor app-insights query --app "$APP_ID" \
  --analytics-query 'requests | where timestamp > ago(30m) | summarize requests=sum(itemCount) by bin(timestamp, 5m)'""",
"code": r"""# pip install azure-monitor-opentelemetry flask requests
# Set APPLICATIONINSIGHTS_CONNECTION_STRING before starting the process.

import logging
import os

import requests
from azure.monitor.opentelemetry import configure_azure_monitor
from flask import Flask, jsonify
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

configure_azure_monitor(
    logger_name=__name__,
    # Keep correlated logs only when their trace is retained by sampling.
    enable_trace_based_sampling_for_logs=True,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
tracer = trace.get_tracer(__name__)
app = Flask(__name__)

INVENTORY_URL = os.environ.get(
    "INVENTORY_URL",
    "https://inventory.contoso.internal",
)


@app.get("/checkout/<order_id>")
def checkout(order_id):
    with tracer.start_as_current_span("checkout") as span:
        span.set_attribute("app.order_id", order_id)
        span.set_attribute("app.route", "/checkout/{order_id}")

        with tracer.start_as_current_span("reserve_inventory") as child:
            child.set_attribute("app.dependency", "inventory")
            logger.info(
                "Reserving inventory",
                extra={"order_id": order_id},
            )

            # Requests auto-instrumentation creates the HTTP client span and
            # injects traceparent/tracestate while this child span is current.
            response = requests.post(
                f"{INVENTORY_URL}/reserve",
                json={"orderId": order_id},
                timeout=5,
            )
            response.raise_for_status()

            logger.info(
                "Inventory reserved",
                extra={
                    "order_id": order_id,
                    "status_code": response.status_code,
                },
            )

        return jsonify(ok=True, orderId=order_id)


@app.get("/healthz")
def healthz():
    trace.get_current_span().set_attribute("health.probe", True)
    return "ok"


@app.errorhandler(Exception)
def record_exception(exc):
    span = trace.get_current_span()
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))
    logger.error(
        "Checkout failed",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return jsonify(error="internal_error"), 500""",
"code_label": "Python / SDK",
"traps": [
 "Do not use connection strings, API keys or secrets as span attributes. Telemetry is searchable and retained.",
 "If no telemetry appears, check the exact app setting name: <code>APPLICATIONINSIGHTS_CONNECTION_STRING</code>. The deprecated instrumentation-key-only approach is a distractor.",
 "A trace broken between services usually means the downstream call did not receive / forward <code>traceparent</code> headers or uses a non-instrumented transport.",
 "<code>traces</code>/<code>AppTraces</code> rows are application log records, not OpenTelemetry spans. Distributed-trace spans appear primarily as request and dependency telemetry.",
 "High-cardinality attributes such as full prompts or raw user text can explode cost and leak data; use stable identifiers and sanitized dimensions.",
],
"cleanup": r"""# Deferred: Lab 4.5 needs this Application Insights resource and workspace.
# Run the consolidated monitoring cleanup after Lab 4.5.""",
},
# ---------------------------------------------------------------- 4.5
{
"id": "4.5",
"title": "Analyze logs and metrics with KQL in Log Analytics / Application Insights",
"time": "30 min",
"level": "Core",
"objective": "Use KQL to find failures, calculate sampling-aware request volume and p95 latency, correlate telemetry, and translate between Application Insights and workspace schemas.",
"exam": [
 "KQL flows left to right through pipes: source table \u2192 <code>where</code> filters \u2192 <code>summarize</code> aggregations \u2192 <code>project</code> shape \u2192 <code>order by</code> / <code>render</code>.",
 "Use <code>bin(timestamp, 1h)</code> before <code>summarize</code> to group time-series data into chartable buckets.",
 "Application Insights <b>resource-scoped</b> Logs uses lowercase tables such as <code>requests</code>, <code>dependencies</code>, <code>traces</code> and <code>exceptions</code>. The connected workspace uses PascalCase <code>AppRequests</code>, <code>AppDependencies</code>, <code>AppTraces</code> and <code>AppExceptions</code>.",
 "Latency questions often use <code>percentile(duration, 95)</code> for p95, not average duration.",
 "Application Insights metrics are not sampled, but trace telemetry can be. Use <code>sum(itemCount)</code> and <code>sumif(itemCount, condition)</code> for sampling-aware request, dependency and failure volume.",
 "Correlation uses <code>operation_Id</code> across telemetry tables; parent/child relationships use <code>operation_ParentId</code> and request/dependency <code>id</code> values.",
],
"prereq": "An Application Insights resource with traffic from Lab 4.4 or any app that emits request, dependency, trace and exception telemetry.",
"portal": [
 "##Open Logs",
 "Application Insights \u2192 <b>Monitoring \u2192 Logs</b>. Close sample-query popups and use the lowercase app-scoped query variants below.",
 "Set the time range to <b>Last 24 hours</b>. Run a simple <code>requests | take 10</code> first to confirm data exists.",
 "##Find failures",
 "Run the failed-requests query. Use the <b>Chart</b> view when the query includes <code>render timechart</code>.",
 "Open one failed request from <b>Investigate \u2192 Search</b> and copy its <code>operation_Id</code> for correlation.",
 "##Measure latency",
 "Run the p95 query grouped by <code>bin(timestamp, 5m)</code> and request <code>name</code>. Compare p95 to average to spot tail latency.",
 "##Correlate telemetry",
 "Run the join / union queries to bring requests, dependencies, traces and exceptions into one timeline for a single operation.",
 "For workspace scope, open the linked workspace \u2192 <b>Logs</b> and translate to the PascalCase <code>App*</code> schema; lowercase resource-scoped queries do not run there unchanged.",
],
"cli": r"""RG=rg-ai200-monitor
AI="<application-insights-name>"
LAW="<log-analytics-workspace-name>"

APP_ID=$(az monitor app-insights component show -g "$RG" --app "$AI" \
  --query appId -o tsv)

# --- Application Insights query by appId ----------------------------
az monitor app-insights query --app "$APP_ID" \
  --offset 1d \
  --analytics-query "requests | summarize failures=sumif(itemCount, success == false) by bin(timestamp, 1h), name, resultCode | order by timestamp desc"

# p95 latency: percentile beats average for tail-latency questions.
az monitor app-insights query --app "$APP_ID" \
  --offset 1d \
  --analytics-query "requests | summarize requests=sum(itemCount), p95_ms=percentile(duration, 95) / 1ms by bin(timestamp, 5m), name | order by timestamp asc"

# --- Workspace query by Log Analytics customerId --------------------
WORKSPACE_ID=$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" \
  --query customerId -o tsv)

az monitor log-analytics query -w "$WORKSPACE_ID" \
  --analytics-query "AppTraces | where TimeGenerated > ago(1h) | summarize logs=sum(ItemCount) by SeverityLevel" \
  --timespan P1D""",
"code": r"""// APPLICATION INSIGHTS RESOURCE-SCOPED LOGS
// 1) Sampling-aware request and failure volume with p95 latency.
requests
| where timestamp > ago(24h)
| summarize
    requests = sum(itemCount),
    failures = sumif(itemCount, success == false),
    p95_ms = percentile(duration, 95) / 1ms
  by bin(timestamp, 15m), name
| extend failure_rate_pct =
    iff(requests == 0, 0.0, round(100.0 * failures / requests, 2))
| order by timestamp asc
| render timechart

// 2) Slow or failing dependencies, grouped by target service.
dependencies
| where timestamp > ago(24h)
| where success == false or duration > 1s
| summarize
    calls = sum(itemCount),
    failures = sumif(itemCount, success == false),
    p95_ms = percentile(duration, 95) / 1ms
  by target, name, type
| order by failures desc, p95_ms desc

// 3) Join failed requests to application log records on operation_Id.
requests
| where timestamp > ago(24h)
| where success == false
| project operation_Id, request_id = id, request_time = timestamp,
          request_name = name, resultCode, duration
| join kind=leftouter (
    traces
    | where timestamp > ago(24h)
    | project operation_Id, trace_time = timestamp, severityLevel, message
) on operation_Id
| order by request_time desc, trace_time asc

// 4) One correlated timeline. AppTraces/traces are log records, not spans.
let operation = "<paste-operation_Id-here>";
union withsource=table requests, dependencies, traces, exceptions
| where operation_Id == operation
| project timestamp, table, operation_Id, operation_ParentId, id,
          name, message, type, resultCode, success, duration
| order by timestamp asc

// WORKSPACE-SCOPED EQUIVALENT FOR QUERY 1
AppRequests
| where TimeGenerated > ago(24h)
| summarize
    Requests = sum(ItemCount),
    Failures = sumif(ItemCount, Success == false),
    P95DurationMs = percentile(DurationMs, 95)
  by bin(TimeGenerated, 15m), Name
| extend FailureRatePct =
    iff(Requests == 0, 0.0, round(100.0 * Failures / Requests, 2))
| order by TimeGenerated asc
| render timechart""",
"code_label": "KQL",
"traps": [
 "<code>where</code> filters rows; <code>project</code> selects / renames columns; <code>summarize</code> collapses rows. Mixing those up is a common KQL distractor.",
 "Without <code>bin(timestamp, ...)</code>, a time-series <code>summarize</code> can group by every unique timestamp and produce useless charts.",
 "Average latency can hide user pain. If the question asks for slowest 5% or tail latency, use <code>percentile(duration, 95)</code>.",
 "Choose the schema that matches query scope: lowercase tables and columns for Application Insights resource-scoped Logs; <code>App*</code> tables and PascalCase columns for workspace-scoped Logs.",
 "<code>count()</code> and <code>countif()</code> count stored rows. With trace sampling, use <code>sum(itemCount)</code> and <code>sumif(itemCount, condition)</code> for represented event volume.",
 "<code>operation_Id</code> correlates the end-to-end transaction; <code>id</code> identifies one request/dependency span. Do not join only on timestamp.",
 "Application Insights and Log Analytics use KQL, but CLI targets differ: <code>az monitor app-insights query --app</code> uses an App Insights appId; <code>az monitor log-analytics query -w</code> uses a workspace ID.",
],
"cleanup": r"""# Remove any alert created from the query if it exists.
az monitor metrics alert delete \
  -g rg-ai200-monitor -n ai200-high-failure-rate 2>/dev/null || true

# Lab 4.5 is the final consumer of the monitoring resources.
az group delete -n rg-ai200-monitor --yes --no-wait""",
},
]
