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
 "Modern Key Vault authorization is <b>Azure RBAC</b>, not vault access policies. Read secrets with <b>Key Vault Secrets User</b>; create / rotate them with <b>Key Vault Secrets Officer</b>.",
 "A secret update creates a <b>new version</b>. Apps that call <code>get_secret(name)</code> receive the latest enabled version; apps pinned to a version keep using that version until changed.",
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

# Reader role for an app / managed identity: can get/list secret values.
az role assignment create \
  --assignee <app-principal-id> \
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

# Read the latest enabled version.
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
"cleanup": r"""az group delete -n rg-ai200-secure --yes --no-wait""",
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
 "Dynamic refresh uses a watched <b>sentinel key</b>: update many settings, then change <code>Settings:Sentinel</code> so clients reload as one coherent batch.",
],
"prereq": "An App Configuration store and a Key Vault secret from Lab 4.1. For Python: <code>pip install azure-identity azure-appconfiguration azure-keyvault-secrets</code>.",
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
KV=<your-keyvault-name>

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
SECRET_ID=$(az keyvault secret show --vault-name $KV \
  --name openai-api-key --query id -o tsv)

az appconfig kv set-keyvault --name $APPCFG --auth-mode login \
  --key Secrets:OpenAIKey --label dev \
  --secret-identifier "$SECRET_ID" --yes

az appconfig kv list --name $APPCFG --auth-mode login \
  --label dev -o table

# Runtime app identity needs read access to BOTH services.
az role assignment create --assignee <app-principal-id> \
  --role "App Configuration Data Reader" --scope $STORE_ID
az role assignment create --assignee <app-principal-id> \
  --role "Key Vault Secrets User" \
  --scope $(az keyvault show -n $KV --query id -o tsv)""",
"code": r"""# pip install azure-identity azure-appconfiguration azure-keyvault-secrets
# This is the sentinel refresh pattern without storing secrets in App Config.

import json
import os
from urllib.parse import urlparse

from azure.appconfiguration import AzureAppConfigurationClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

endpoint = os.environ["APPCONFIG_ENDPOINT"]   # e.g. https://name.azconfig.io
label = os.environ.get("APPCONFIG_LABEL", "dev")

credential = DefaultAzureCredential()
client = AzureAppConfigurationClient(base_url=endpoint, credential=credential)

_config = {}
_sentinel_etag = None


def _read_key_vault_reference(setting):
    # App Configuration stores JSON like {"uri":"https://vault.vault.azure.net/secrets/name/version"}.
    uri = json.loads(setting.value)["uri"]
    parsed = urlparse(uri)
    parts = [p for p in parsed.path.split("/") if p]
    vault_url = f"{parsed.scheme}://{parsed.netloc}"
    secret_name = parts[1]
    secret_version = parts[2] if len(parts) > 2 else None
    return SecretClient(vault_url, credential).get_secret(secret_name, secret_version).value


def load_all():
    global _config, _sentinel_etag

    values = {}
    for setting in client.list_configuration_settings(
        key_filter="Settings:*",
        label_filter=label,
    ):
        short_key = setting.key.removeprefix("Settings:")
        values[short_key] = setting.value

    secret_ref = client.get_configuration_setting(
        key="Secrets:OpenAIKey",
        label=label,
    )
    values["OpenAIKey"] = _read_key_vault_reference(secret_ref)

    flag = client.get_configuration_setting(
        key=".appconfig.featureflag/BetaChat",
        label=label,
    )
    values["BetaChat"] = json.loads(flag.value)["enabled"]

    sentinel = client.get_configuration_setting(
        key="Settings:Sentinel",
        label=label,
    )
    _sentinel_etag = sentinel.etag
    _config = values
    return values


def refresh_if_needed():
    # Cheap check: one watched key. If unchanged, keep the cached config.
    global _sentinel_etag
    sentinel = client.get_configuration_setting(
        key="Settings:Sentinel",
        label=label,
    )
    if sentinel.etag != _sentinel_etag:
        return load_all()
    return _config


config = load_all()
print(config["ModelDeployment"], "beta=", config["BetaChat"])""",
"code_label": "Python / SDK",
"traps": [
 "Labels are not hierarchy. <code>Settings:ModelDeployment</code> with label <code>prod</code> is a different setting version than the same key with label <code>dev</code>.",
 "App Configuration <b>access keys</b> work, but managed identity + <b>App Configuration Data Reader</b> is the secure answer for Azure-hosted apps.",
 "A Key Vault reference failing at runtime is usually a missing <b>Key Vault Secrets User</b> assignment for the app identity, not an App Configuration problem.",
 "Refreshing every key on every request is wasteful. Watch a <b>sentinel key</b>, then reload the full config only when its ETag changes.",
 "Feature flags live in App Configuration; Key Vault is not a feature-management service.",
],
"cleanup": r"""az appconfig delete -g rg-ai200-secure -n <app-configuration-name> --yes""",
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
 "Assign <b>Cosmos DB Built-in Data Reader</b> at scope <code>/</code> for read-only SDK queries. Use Data Contributor only if the app writes items.",
 "##Run locally and in Azure",
 "Local developer machine: run <code>az login</code>. Azure runtime: no login command and no secret; the SDK requests a token from the managed identity endpoint.",
],
"cli": r"""RG=rg-ai200-secure
APP=<your-webapp-name>
KV=<your-keyvault-name>
COSMOS=<your-cosmos-account>
UAMI=id-ai200-reader

# --- System-assigned managed identity ------------------------------
az webapp identity assign -g $RG -n $APP
SYSTEM_PRINCIPAL=$(az webapp identity show -g $RG -n $APP \
  --query principalId -o tsv)

VAULT_ID=$(az keyvault show -g $RG -n $KV --query id -o tsv)
az role assignment create \
  --assignee $SYSTEM_PRINCIPAL \
  --role "Key Vault Secrets User" \
  --scope $VAULT_ID

# --- User-assigned managed identity --------------------------------
az identity create -g $RG -n $UAMI
UAMI_ID=$(az identity show -g $RG -n $UAMI --query id -o tsv)
UAMI_CLIENT_ID=$(az identity show -g $RG -n $UAMI --query clientId -o tsv)
UAMI_PRINCIPAL_ID=$(az identity show -g $RG -n $UAMI --query principalId -o tsv)

az webapp identity assign -g $RG -n $APP --identities $UAMI_ID

# Tell Azure Identity which user-assigned identity to use at runtime.
az webapp config appsettings set -g $RG -n $APP \
  --settings AZURE_CLIENT_ID=$UAMI_CLIENT_ID

# --- Cosmos DB for NoSQL data-plane RBAC ----------------------------
# Reader role can query items but cannot write. This is NOT the same as ARM Reader.
ROLE_ID=$(az cosmosdb sql role definition list -g $RG -a $COSMOS \
  --query "[?roleName=='Cosmos DB Built-in Data Reader'].id | [0]" -o tsv)

az cosmosdb sql role assignment create -g $RG -a $COSMOS \
  --scope "/" \
  --principal-id $UAMI_PRINCIPAL_ID \
  --role-definition-id $ROLE_ID

# Local development fallback: same code, developer token from Azure CLI.
az login
az account show -o table""",
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

cosmos = CosmosClient(
    os.environ["COSMOS_ENDPOINT"],
    credential=credential,
)

container = cosmos.get_database_client("appdb").get_container_client("requests")
for item in container.query_items(
    query="SELECT TOP 5 c.id, c.status FROM c",
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
 "Local <code>az login</code> proves the credential chain works locally, but it does not grant your deployed app anything. The app's principal needs its own role assignments.",
 "Connection strings are the wrong answer when the requirement says no credential rotation burden or no secrets in code.",
],
"cleanup": r"""az identity delete -g rg-ai200-secure -n id-ai200-reader""",
},
# ---------------------------------------------------------------- 4.4
{
"id": "4.4",
"title": "Distributed tracing with OpenTelemetry and Azure Monitor",
"time": "35 min",
"level": "Advanced",
"objective": "Instrument a Python service with OpenTelemetry, export spans to Application Insights, and correlate requests, dependencies and traces.",
"exam": [
 "OpenTelemetry creates <b>traces</b> made of <b>spans</b>. A span should carry useful attributes such as operation name, model deployment, tenant or order ID \u2014 not secret values.",
 "The Azure Monitor distro is <code>azure-monitor-opentelemetry</code>. Calling <code>configure_azure_monitor()</code> wires exporters and common auto-instrumentation.",
 "Application Insights ingestion uses <code>APPLICATIONINSIGHTS_CONNECTION_STRING</code>, not the old instrumentation key-only pattern.",
 "Trace context propagates through W3C <code>traceparent</code> headers so downstream services and HTTP dependencies share the same operation / trace.",
 "Correlation in Application Insights joins <code>requests</code>, <code>dependencies</code>, <code>traces</code> and <code>exceptions</code> by operation identifiers.",
],
"prereq": "An Azure Monitor Application Insights resource. For Python: <code>pip install azure-monitor-opentelemetry flask requests</code>.",
"portal": [
 "##Create Application Insights",
 "Azure portal \u2192 <b>Application Insights</b> \u2192 <b>+ Create</b>. Use a workspace-based resource connected to a Log Analytics workspace.",
 "Open the resource \u2192 <b>Overview</b> \u2192 copy the <b>Connection String</b>. Set it as <code>APPLICATIONINSIGHTS_CONNECTION_STRING</code> in your app settings.",
 "##Instrument and run",
 "Add <code>configure_azure_monitor()</code> at app startup before the framework begins handling requests.",
 "Create custom spans around important AI calls, storage calls or orchestration steps; add attributes that help troubleshooting and filtering.",
 "For HTTP calls to other services, keep the auto-instrumented <code>requests</code> library or manually inject context headers so traces stay connected.",
 "##Inspect correlation",
 "Application Insights \u2192 <b>Transaction search</b> \u2192 open one request \u2192 inspect the end-to-end transaction waterfall.",
 "Application Insights \u2192 <b>Application map</b> shows caller / dependency relationships. <b>Failures</b> highlights failed requests and dependency failures.",
 "Application Insights \u2192 <b>Logs</b> \u2192 query <code>requests</code>, <code>dependencies</code>, <code>traces</code> and <code>exceptions</code> by <code>operation_Id</code>.",
],
"cli": r"""RG=rg-ai200-monitor
LOC=eastus
LAW=law-ai200-$RANDOM
AI=appi-ai200-$RANDOM
APP=<your-webapp-name>

az group create -n $RG -l $LOC

# Workspace-based Application Insights is the modern Azure Monitor pattern.
az monitor log-analytics workspace create -g $RG -n $LAW -l $LOC
LAW_ID=$(az monitor log-analytics workspace show -g $RG -n $LAW \
  --query id -o tsv)

az extension add -n application-insights --upgrade
az monitor app-insights component create \
  --app $AI \
  --location $LOC \
  --resource-group $RG \
  --workspace $LAW_ID \
  --application-type web

CONN=$(az monitor app-insights component show -g $RG --app $AI \
  --query connectionString -o tsv)

# App code reads this variable when configure_azure_monitor() starts.
az webapp config appsettings set -g $RG -n $APP \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="$CONN"

# Quick smoke query after traffic flows.
APP_ID=$(az monitor app-insights component show -g $RG --app $AI \
  --query appId -o tsv)

az monitor app-insights query --app $APP_ID \
  --analytics-query 'requests | where timestamp > ago(30m) | summarize count() by bin(timestamp, 5m)'""",
"code": r"""# pip install azure-monitor-opentelemetry flask requests
# Set APPLICATIONINSIGHTS_CONNECTION_STRING before the process starts.

import os

import requests
from azure.monitor.opentelemetry import configure_azure_monitor
from flask import Flask, jsonify, request
from opentelemetry import trace
from opentelemetry.propagate import inject

# Exam point: one call configures Azure Monitor exporters and common
# auto-instrumentation for frameworks/libraries that are installed.
configure_azure_monitor()

tracer = trace.get_tracer(__name__)
app = Flask(__name__)

INVENTORY_URL = os.environ.get("INVENTORY_URL", "https://inventory.contoso.internal")


@app.get("/checkout/<order_id>")
def checkout(order_id):
    with tracer.start_as_current_span("checkout") as span:
        span.set_attribute("app.order_id", order_id)
        span.set_attribute("app.route", "/checkout/{order_id}")

        headers = {}
        inject(headers)  # writes W3C traceparent/tracestate for the next service

        with tracer.start_as_current_span("reserve_inventory") as child:
            response = requests.post(
                f"{INVENTORY_URL}/reserve",
                json={"orderId": order_id},
                headers=headers,
                timeout=5,
            )
            child.set_attribute("http.status_code", response.status_code)
            child.set_attribute("dependency.name", "inventory")
            response.raise_for_status()

        return jsonify(ok=True, orderId=order_id)


@app.get("/healthz")
def healthz():
    current = trace.get_current_span()
    current.set_attribute("health.probe", True)
    return "ok"


@app.errorhandler(Exception)
def record_exception(exc):
    span = trace.get_current_span()
    span.record_exception(exc)
    span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
    return jsonify(error=type(exc).__name__), 500""",
"code_label": "Python / SDK",
"traps": [
 "Do not use connection strings, API keys or secrets as span attributes. Telemetry is searchable and retained.",
 "If no telemetry appears, check the exact app setting name: <code>APPLICATIONINSIGHTS_CONNECTION_STRING</code>. The deprecated instrumentation-key-only approach is a distractor.",
 "A trace broken between services usually means the downstream call did not receive / forward <code>traceparent</code> headers or uses a non-instrumented transport.",
 "Logs alone are not distributed tracing. The exam expects spans, parent/child relationships, dependency telemetry and correlation IDs.",
 "High-cardinality attributes such as full prompts or raw user text can explode cost and leak data; use stable identifiers and sanitized dimensions.",
],
"cleanup": r"""az group delete -n rg-ai200-monitor --yes --no-wait""",
},
# ---------------------------------------------------------------- 4.5
{
"id": "4.5",
"title": "Analyze logs and metrics with KQL in Log Analytics / Application Insights",
"time": "30 min",
"level": "Core",
"objective": "Use KQL to find failed requests, calculate p95 latency, correlate traces, and run the same queries from Azure CLI.",
"exam": [
 "KQL flows left to right through pipes: source table \u2192 <code>where</code> filters \u2192 <code>summarize</code> aggregations \u2192 <code>project</code> shape \u2192 <code>order by</code> / <code>render</code>.",
 "Use <code>bin(timestamp, 1h)</code> before <code>summarize</code> to group time-series data into chartable buckets.",
 "Application Insights tables commonly tested: <code>requests</code>, <code>dependencies</code>, <code>traces</code> and <code>exceptions</code>.",
 "Latency questions often use <code>percentile(duration, 95)</code> for p95, not average duration.",
 "Correlation uses <code>operation_Id</code> across telemetry tables; parent/child relationships use <code>operation_ParentId</code> and request/dependency <code>id</code> values.",
],
"prereq": "An Application Insights resource with traffic from Lab 4.4 or any app that emits request, dependency, trace and exception telemetry.",
"portal": [
 "##Open Logs",
 "Application Insights \u2192 <b>Monitoring \u2192 Logs</b>. Close sample-query popups so you can paste the KQL tab queries.",
 "Set the time range to <b>Last 24 hours</b>. Run a simple <code>requests | take 10</code> first to confirm data exists.",
 "##Find failures",
 "Run the failed-requests query. Use the <b>Chart</b> view when the query includes <code>render timechart</code>.",
 "Open one failed request in <b>Transaction search</b> and copy its <code>operation_Id</code> for correlation.",
 "##Measure latency",
 "Run the p95 query grouped by <code>bin(timestamp, 5m)</code> and request <code>name</code>. Compare p95 to average to spot tail latency.",
 "##Correlate telemetry",
 "Run the join / union queries to bring requests, dependencies, traces and exceptions into one timeline for a single operation.",
 "Switch to the Log Analytics workspace if your resource is workspace-based; the same KQL works there when the App Insights tables are present.",
],
"cli": r"""RG=rg-ai200-monitor
AI=<application-insights-name>
LAW=<log-analytics-workspace-name>

APP_ID=$(az monitor app-insights component show -g $RG --app $AI \
  --query appId -o tsv)

# --- Application Insights query by appId ----------------------------
az monitor app-insights query --app $APP_ID \
  --offset 1d \
  --analytics-query "requests | where success == false | summarize failures=count() by bin(timestamp, 1h), name, resultCode | order by timestamp desc"

# p95 latency: percentile beats average for tail-latency questions.
az monitor app-insights query --app $APP_ID \
  --offset 1d \
  --analytics-query "requests | summarize p95_ms=percentile(duration, 95), avg_ms=avg(duration), count() by bin(timestamp, 5m), name | order by timestamp asc"

# --- Workspace query by Log Analytics customerId --------------------
WORKSPACE_ID=$(az monitor log-analytics workspace show -g $RG -n $LAW \
  --query customerId -o tsv)

az monitor log-analytics query -w $WORKSPACE_ID \
  --analytics-query "traces | where timestamp > ago(1h) | summarize count() by severityLevel" \
  --timespan P1D""",
"code": r"""// 1) Failed requests per hour, by operation and result code.
requests
| where timestamp > ago(24h)
| where success == false
| summarize failures = count() by bin(timestamp, 1h), name, resultCode
| order by timestamp desc
| render timechart

// 2) p95 latency by request name. p95 is the common exam metric for tail latency.
requests
| where timestamp > ago(24h)
| summarize
    requests = count(),
    avg_ms = avg(duration),
    p95_ms = percentile(duration, 95)
  by bin(timestamp, 5m), name
| order by timestamp asc
| render timechart

// 3) Slow or failing dependencies, grouped by target service.
dependencies
| where timestamp > ago(24h)
| summarize
    calls = count(),
    failures = countif(success == false),
    p95_ms = percentile(duration, 95)
  by target, name, type
| order by failures desc, p95_ms desc

// 4) Join failed requests to trace messages on operation_Id.
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

// 5) One correlated timeline across requests, dependencies, traces and exceptions.
let operation = "<paste-operation_Id-here>";
union withsource=table requests, dependencies, traces, exceptions
| where operation_Id == operation
| project timestamp, table, operation_Id, operation_ParentId, id,
          name, message, type, resultCode, success, duration
| order by timestamp asc""",
"code_label": "KQL",
"traps": [
 "<code>where</code> filters rows; <code>project</code> selects / renames columns; <code>summarize</code> collapses rows. Mixing those up is a common KQL distractor.",
 "Without <code>bin(timestamp, ...)</code>, a time-series <code>summarize</code> can group by every unique timestamp and produce useless charts.",
 "Average latency can hide user pain. If the question asks for slowest 5% or tail latency, use <code>percentile(duration, 95)</code>.",
 "<code>operation_Id</code> correlates the end-to-end transaction; <code>id</code> identifies one request/dependency span. Do not join only on timestamp.",
 "Application Insights and Log Analytics use KQL, but CLI targets differ: <code>az monitor app-insights query --app</code> uses an App Insights appId; <code>az monitor log-analytics query -w</code> uses a workspace ID.",
],
},
]
