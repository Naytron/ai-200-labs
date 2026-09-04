# -*- coding: utf-8 -*-
# Domain 1 - Develop containerized solutions on Azure (20-25%)

DOMAIN = {
    "key": "containers",
    "name": "Develop Containerized Solutions on Azure",
    "weight": "20\u201325%",
    "blurb": "Azure Container Registry (build, store, version, Tasks), and the three ways to run a container: App Service for Containers, Azure Container Apps (with KEDA event-driven scaling and revisions) and AKS with manifest files. Expect 'which host fits this workload' questions, revision/traffic-split questions, and 'why won't my container start' troubleshooting.",
}

LABS = [
# ---------------------------------------------------------------- 1.1
{
"id": "1.1",
"title": "Build, store, version and manage images in Azure Container Registry",
"time": "25 min",
"level": "Foundational",
"objective": "Create an ACR, build and push a versioned image, tag it for release, and inspect repositories and manifests.",
"exam": [
 "ACR SKUs are <b>Basic / Standard / Premium</b>. Premium adds capabilities such as geo-replication, private endpoints, customer-managed keys, zone redundancy in supported regions, and higher limits. Geo-replication is a common distractor for Basic/Standard.",
 "<code>az acr build</code> runs the Docker build <i>in the cloud</i> using an ACR Task \u2014 you do <b>not</b> need a local Docker daemon. This is the exam's preferred answer when the question says 'no Docker installed'.",
 "Authentication order of preference: <b>Microsoft Entra token</b> (<code>az acr login</code>) &gt; repository-scoped tokens &gt; <b>admin user</b>. The admin account is disabled by default and is for testing only.",
 "A tag is mutable by default; the same tag can be re-pushed. Use <code>az acr repository update --write-enabled false</code> or image <b>lock</b> to make a specific version immutable.",
 "On a registry using classic registry-wide RBAC, pull and push use <b>AcrPull</b>/<b>AcrPush</b>. On an ABAC-enabled registry, use repository-scoped roles such as <b>Container Registry Repository Reader</b> or <b>Writer</b>; <code>AcrPull</code>/<code>AcrPush</code> are not honored.",
 "Read the actual <b>loginServer</b> property instead of constructing <code>&lt;name&gt;.azurecr.io</code>. Registries with domain-name-label protection use a hashed login server.",
 "Docker Content Trust is deprecated in ACR. If image-signing integrity is required, recognize current Notary Project / Notation guidance and verify the exact support status and rollout requirements.",
],
"prereq": "An Azure subscription and Azure CLI 2.x. No local Docker required if you use <code>az acr build</code>.",
"portal": [
 "##Create the registry",
 "Azure portal \u2192 search <b>Container registries</b> \u2192 <b>+ Create</b>.",
 "Resource group <code>rg-ai200-containers</code>, Registry name <code>ai200acr&lt;unique&gt;</code> (5\u201350 alphanumerics, globally unique), SKU <b>Standard</b>.",
 "<b>Review + create</b> \u2192 <b>Create</b>.",
 "##Build an image in the cloud",
 "Open the registry \u2192 <b>Quick start</b> reads the commands, but the build itself is easiest from Cloud Shell: click the <b>&gt;_</b> Cloud Shell icon.",
 "In a folder with a <code>Dockerfile</code> (see the code tab), run <code>az acr build -r ai200acr&lt;unique&gt; -t api:v1 .</code>.",
 "##Version and inspect",
 "Registry \u2192 <b>Repositories</b> \u2192 <code>api</code> \u2192 you'll see tag <code>v1</code>. Open it to read the <b>manifest digest</b>, size and architecture.",
 "Registry \u2192 <b>Repositories</b> \u2192 <code>api</code> \u2192 <b>...</b> \u2192 <b>Lock</b> a tag to prevent overwrite/delete.",
 "Registry \u2192 <b>Access keys</b> \u2192 note the exact <b>Login server</b>. With domain-name-label protection it includes a hash and must not be inferred from the registry name. Leave <b>Admin user</b> <i>disabled</i>.",
],
"cli": r"""RG=rg-ai200-containers
LOC=eastus
ACR=ai200acr$RANDOM          # must be globally unique, lowercase alphanumerics

az group create -n $RG -l $LOC

# --- Create the registry (Standard SKU) ----------------------------
az acr create -g $RG -n $ACR --sku Standard
LOGIN_SERVER=$(az acr show -g $RG -n $ACR --query loginServer -o tsv)

# --- Build IN THE CLOUD (no local Docker daemon needed) ------------
# Run from a folder that contains a Dockerfile:
az acr build -r $ACR -t api:v1 -t api:latest .

# --- List without a local Docker daemon ----------------------------
# Do not run plain `az acr login` in this workflow: it calls Docker by default.
az acr repository list -n $ACR -o table
az acr repository show-tags -n $ACR --repository api -o table

# --- Inspect the manifest / digest (manifest commands are Preview) -
az acr manifest list-metadata -r $ACR -n api -o table
az acr repository show -n $ACR --image api:v1

# --- Version a second build & make v1 immutable -------------------
az acr build -r $ACR -t api:v2 .
az acr repository update -n $ACR --image api:v1 --write-enabled false

# --- Grant least-privilege pull to a service principal ------------
ACR_ID=$(az acr show -n $ACR --query id -o tsv)
# For a classic RBAC registry:
az role assignment create \
  --assignee-object-id <service-principal-object-id> \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull --scope $ACR_ID

# For an ABAC-enabled registry, use the repository role instead:
# --role "Container Registry Repository Reader"

echo "Use this endpoint for image references: $LOGIN_SERVER"
""",
"code": r"""# Dockerfile - a minimal Python API image that ACR will build for you.
# `az acr build` ships THIS context to the registry and runs the build there.

FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# EXPOSE is image metadata only. Configure the Azure host's target/listen port.
ENV PORT=8000
EXPOSE 8000

# Use a non-root user (exam favours least privilege in containers too)
RUN useradd -m appuser
USER appuser

CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]""",
"code_label": "Dockerfile",
"traps": [
 "<code>az acr build</code> vs <code>docker build</code>: if the question says 'the developer has no Docker Desktop / build agent', the answer is <b>az acr build</b> (server-side Task), not 'install Docker'.",
 "Registry <b>name</b> is alphanumeric only and globally unique, but a DNL-protected <b>login server</b> includes a hash. Query <code>loginServer</code>; do not concatenate the endpoint.",
 "Geo-replication and private endpoints require <b>Premium</b>. Docker Content Trust is deprecated; do not treat it as a current Premium design recommendation.",
 "Enabling the <b>admin user</b> to let an app pull is the wrong answer. Assign the least-privilege registry role to the app identity, choosing classic or ABAC repository roles to match the registry mode.",
 "A tag that happens to be unique is not immutable. Lock the manifest/tag or deploy by digest when immutability is required.",
],
"cleanup": r"""# Deferred: every remaining Domain 1 lab reuses this registry/group.
# Run the consolidated resource-group cleanup after Lab 1.6.""",
},
# ---------------------------------------------------------------- 1.2
{
"id": "1.2",
"title": "Automate builds with Azure Container Registry Tasks",
"time": "25 min",
"level": "Core",
"objective": "Run a quick task, create a Git-triggered build task, and a multi-step task that builds, tests and pushes \u2014 plus base-image update automation.",
"exam": [
 "ACR Tasks run <b>in Azure</b> on managed build agents \u2014 no build infrastructure to manage. Three flavours: <b>quick task</b> (<code>az acr build</code>), <b>automatically triggered task</b> (source commit / base-image update / schedule), and <b>multi-step task</b> (YAML).",
 "A task can auto-rebuild when a tracked <b>base image</b> changes. That refreshes the derived image; it does not prove the result is vulnerability-free, so scanning and patch governance are still required.",
 "Git triggers need a supported GitHub <b>classic PAT</b> passed with <code>--git-access-token</code>. Private repositories need <code>repo</code>; public repositories need <code>repo:status</code> and <code>public_repo</code>. Commit and pull-request triggers are separate toggles.",
 "Multi-step tasks (<code>acr-task.yaml</code>) express <code>build</code>, <code>push</code> and <code>cmd</code> steps \u2014 <code>cmd</code> runs an arbitrary container (e.g. to run tests) between build and push.",
 "Tasks honour <code>--platform linux/arm64</code> etc. for cross-arch builds without a matching local machine.",
],
"prereq": "Lab 1.1 registry. For the Git trigger, a GitHub repo with a Dockerfile and a supported classic PAT: <code>repo</code> for private repositories, or <code>repo:status</code> plus <code>public_repo</code> for public repositories.",
"portal": [
 "##Quick task",
 "Registry \u2192 <b>Quick start</b> shows the <code>az acr build</code> quick-task command \u2014 it is itself a one-off Task run.",
 "##Triggered task from Git",
 "Registry \u2192 <b>Tasks</b> \u2192 <b>+ Add</b> (portal exposes basic tasks; multi-step needs the CLI/YAML).",
 "Name <code>build-on-commit</code>, Source location = your GitHub repo URL, Image <code>api:{{.Run.ID}}</code>, Dockerfile <code>Dockerfile</code>.",
 "Toggle <b>Commit</b> trigger on, paste the <b>PAT</b>, enable <b>Base image trigger</b> = <i>Runtime and build-time</i>. <b>Create</b>.",
 "##Run & watch",
 "Select the task \u2192 <b>Run</b> \u2192 open <b>Runs</b> to stream the build log; a successful run pushes the tag automatically.",
 "Registry \u2192 <b>Repositories</b> confirm the new tag appeared.",
],
"cli": r"""RG=rg-ai200-containers
ACR=<your-acr-name>

# --- Quick task (one-off, same engine as a Task) ------------------
az acr build -r $ACR -t api:{{.Run.ID}} .

# --- Auto-triggered task: rebuild on git commit AND base-image patch
az acr task create \
  -r $ACR -n build-on-commit \
  --image api:{{.Run.ID}} \
  --context https://github.com/<you>/<repo>.git#main \
  --file Dockerfile \
  --git-access-token <github-PAT> \
  --commit-trigger-enabled true \
  --base-image-trigger-enabled true \
  --base-image-trigger-type All

# Run it now and stream logs
az acr task run  -r $ACR -n build-on-commit
az acr task logs -r $ACR -n build-on-commit

# --- Multi-step task from YAML (build -> test -> push) ------------
az acr task create \
  -r $ACR -n build-test-push \
  --context https://github.com/<you>/<repo>.git#main \
  --file acr-task.yaml \
  --git-access-token <github-PAT> \
  --commit-trigger-enabled true

# --- Cross-architecture build without matching hardware -----------
az acr build -r $ACR -t api:arm64 --platform linux/arm64 .

az acr task list -r $ACR -o table""",
"code": r"""# acr-task.yaml - a multi-step Task: build, run tests, then push only if tests pass.
version: v1.1.0
steps:
  # 1) Build both local tags; neither is pushed yet.
  - build: -t $Registry/api:$ID -t $Registry/api:latest .
    id: build-image

  # 2) Run the unit tests INSIDE the freshly built image.
  #    If this container exits non-zero, the task fails and nothing is pushed.
  - cmd: $Registry/api:$ID pytest -q
    id: run-tests
    when: ['build-image']

  # 3) Only now push the validated image
  - push:
      - $Registry/api:$ID
      - $Registry/api:latest
    when: ['run-tests']

# $Registry, $ID and $Run.* are Task run variables injected by ACR.""",
"code_label": "acr-task.yaml",
"traps": [
 "'Rebuild when a tracked base image changes' \u2192 choose an <b>ACR Task with a base-image trigger</b>. Do not infer that a successful rebuild guarantees zero CVEs; scan the result and manage remediation separately.",
 "Multi-step <code>cmd</code> steps run a container \u2014 use them for tests/scans <i>between</i> build and push. A test failure stops the push; that gate is the point.",
 "Git commit triggers require documented classic-PAT scopes. Fine-grained PATs do not have a classic <code>repo</code> scope and should not be described as merely 'missing' it.",
 "<code>{{.Run.ID}}</code> gives each build a unique traceable tag, but uniqueness is not an immutability control. Lock it or deploy by digest if overwrite prevention is required.",
 "Every image named in a <code>push</code> step must have been built or tagged first. Build both <code>$ID</code> and <code>latest</code> before pushing them.",
],
"cleanup": r"""az acr task delete -r <your-acr-name> -n build-on-commit --yes
az acr task delete -r <your-acr-name> -n build-test-push --yes
# Keep the registry for Labs 1.3-1.6.""",
},
# ---------------------------------------------------------------- 1.3
{
"id": "1.3",
"title": "Deploy a container to Azure App Service with env vars and secrets",
"time": "30 min",
"level": "Core",
"objective": "Run an ACR image as the main container in a sidecar-enabled App Service app, supply app settings, resolve a Key Vault reference, and configure a staging slot with identity parity.",
"exam": [
 "A sidecar-enabled Linux App Service app has one <b>main</b> container and can run supporting sidecars in the same network namespace. Only the main container receives external traffic; the containers scale together.",
 "App settings become <b>environment variables</b> without rebaking the image. In classic custom-container mode, routing defaults to port 80 and <code>WEBSITES_PORT</code> overrides it. In sidecar mode, configure the main container's <b>target port</b>; <code>WEBSITES_PORT</code> does not apply.",
 "For passwordless ACR pull, enable a managed identity, grant <b>AcrPull</b> for classic RBAC or <b>Container Registry Repository Reader</b> for ABAC, and ensure the registry accepts ARM-audience tokens. Classic mode uses <code>acrUseManagedIdentityCreds</code>; sidecar configuration uses a SystemIdentity/UserAssigned auth type.",
 "<b>Key Vault references</b> in app settings use the syntax <code>@Microsoft.KeyVault(SecretUri=...)</code>; the app's managed identity needs <b>Key Vault Secrets User</b> (RBAC) or a <b>get</b> access policy. The secret value is never stored in App Service.",
 "A versionless Key Vault reference follows the current version; a versioned reference is valid and intentionally pinned. Deployment slots are supported on Standard, Premium and Isolated tiers, and each slot has its own system-assigned identity and role assignments.",
],
"prereq": "Labs 1.1 image and a Key Vault (Lab 4.1 covers Key Vault creation). Azure CLI 2.x.",
"portal": [
 "##Create the Web App for Containers",
 "Portal \u2192 <b>App Services</b> \u2192 <b>+ Create</b> \u2192 <b>Web App</b>. Publish <b>Container</b>, OS <b>Linux</b>, enable sidecar support, and use at least a <b>Standard S1</b> plan for deployment slots.",
 "<b>Container</b> tab: Image Source <b>Azure Container Registry</b>, choose the exact registry login server, image <code>api:v1</code>, and set the main-container target port to <code>8000</code>. <b>Review + create</b>.",
 "##Let the app pull from ACR with an identity",
 "App \u2192 <b>Identity</b> \u2192 System assigned \u2192 <b>On</b>. Copy the object ID.",
 "Registry \u2192 <b>Access control (IAM)</b> \u2192 <b>+ Add role assignment</b> \u2192 <b>AcrPull</b> \u2192 assign to the web app's identity.",
 "App \u2192 <b>Deployment Center \u2192 Containers</b> \u2192 set registry authentication to <b>Managed identity</b>. Sidecars, if added, communicate with the main container over <code>localhost:&lt;port&gt;</code>.",
 "##Configuration & secrets",
 "App \u2192 <b>Settings \u2192 Environment variables</b> \u2192 <b>App settings</b> \u2192 add <code>MODEL_DEPLOYMENT</code> = <code>gpt-4o</code>. For a sidecar-enabled app, set port 8000 on the main container configuration, not with <code>WEBSITES_PORT</code>.",
 "Add a secret-backed setting: name <code>OPENAI_KEY</code>, value <code>@Microsoft.KeyVault(SecretUri=https://&lt;vault&gt;.vault.azure.net/secrets/openai-api-key/)</code>.",
 "Grant the app <b>Key Vault Secrets User</b> on the vault (IAM). Restart the app and confirm the reference resolves (green tick on the setting).",
 "##Zero-downtime release",
 "App \u2192 <b>Deployment slots</b> \u2192 <b>+ Add slot</b> <code>staging</code> and clone production settings. Enable the staging slot's identity, grant it ACR/Key Vault roles, point its main container at <code>api:v2</code>, test, then <b>Swap</b>.",
],
"cli": r"""RG=rg-ai200-containers
ACR="<your-acr-name>"
APP=ai200-api-$RANDOM
PLAN=plan-ai200
VAULT="<your-keyvault-name>"
ACR_ROLE="AcrPull" # Use Container Registry Repository Reader for ABAC.

# --- Standard plan + sidecar-enabled web app -----------------------
az appservice plan create -g "$RG" -n "$PLAN" --is-linux --sku S1
az webapp create -g "$RG" -p "$PLAN" -n "$APP" --sitecontainers-app

LOGIN_SERVER=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv)
ACR_ID=$(az acr show -g "$RG" -n "$ACR" --query id -o tsv)
VAULT_ID=$(az keyvault show -n "$VAULT" --query id -o tsv)

# --- Production identity: ACR pull + Key Vault read ----------------
az webapp identity assign -g "$RG" -n "$APP"
PRINCIPAL_ID=$(az webapp identity show -g "$RG" -n "$APP" \
  --query principalId -o tsv)

az role assignment create \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "$ACR_ROLE" --scope "$ACR_ID"

az role assignment create \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" --scope "$VAULT_ID"

# Managed-identity image pulls require the registry's ARM audience policy.
az acr config authentication-as-arm show -r "$ACR" -o table
az acr config authentication-as-arm update -r "$ACR" --status enabled
sleep 60

# The main container receives traffic on its configured target port.
az webapp sitecontainers create -g "$RG" -n "$APP" \
  --container-name api \
  --image "$LOGIN_SERVER/api:v1" \
  --target-port 8000 \
  --is-main true \
  --system-assigned-identity true

# App settings become environment variables in the main and sidecars.
az webapp config appsettings set -g "$RG" -n "$APP" --settings \
  MODEL_DEPLOYMENT=gpt-4o \
  "OPENAI_KEY=@Microsoft.KeyVault(SecretUri=https://$VAULT.vault.azure.net/secrets/openai-api-key/)"

# --- Staging has its own identity and RBAC assignments -------------
az webapp deployment slot create -g "$RG" -n "$APP" \
  --slot staging --configuration-source "$APP"

az webapp identity assign -g "$RG" -n "$APP" --slot staging
SLOT_PRINCIPAL_ID=$(az webapp identity show -g "$RG" -n "$APP" \
  --slot staging --query principalId -o tsv)

az role assignment create \
  --assignee-object-id "$SLOT_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "$ACR_ROLE" --scope "$ACR_ID"

az role assignment create \
  --assignee-object-id "$SLOT_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" --scope "$VAULT_ID"

sleep 60
az webapp sitecontainers update -g "$RG" -n "$APP" --slot staging \
  --container-name api \
  --image "$LOGIN_SERVER/api:v2" \
  --target-port 8000 \
  --is-main true \
  --system-assigned-identity true

az webapp deployment slot swap -g "$RG" -n "$APP" \
  --slot staging --target-slot production""",
"code": r"""# app.py - the containerised API. Notice it reads ALL config from the
# environment: App Service app settings and Key Vault references land here,
# so the SAME image runs in dev/stage/prod with no rebuild.
import os
from flask import Flask, jsonify

app = Flask(__name__)

MODEL      = os.environ["MODEL_DEPLOYMENT"]          # from an app setting
OPENAI_KEY = os.environ["OPENAI_KEY"]                # from a Key Vault reference
PORT       = int(os.environ.get("PORT", "8000"))     # matches the configured target port

@app.get("/healthz")
def health():
    # never echo the secret - just prove it resolved
    return jsonify(status="ok", model=MODEL, key_loaded=bool(OPENAI_KEY))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)""",
"code_label": "Python app",
"traps": [
 "Container starts but the site fails \u2192 verify the app listens on <code>0.0.0.0</code> and the right port. Classic mode defaults to 80 and uses <code>WEBSITES_PORT</code>; sidecar mode uses the main container's target-port setting.",
 "Image pull fails after enabling identity \u2192 also grant the role that matches classic RBAC versus ABAC, configure the container's identity auth, and ensure ACR permits ARM-audience tokens.",
 "A Key Vault reference showing a red error usually means missing vault data-plane permission or a wrong URI. Both versionless and versioned secret URIs are valid; the latter intentionally pins a version.",
 "Slot settings you want to <i>stay put</i> during a swap must be marked <b>Deployment slot setting</b> (sticky) \u2014 otherwise they follow the swap.",
 "Production and staging system-assigned identities are different principals. Cloning configuration does not eliminate the need to grant the slot its own ACR and Key Vault roles.",
 "App Service supports trusted sidecars, but all containers share networking, environment and scale. Choose Container Apps or AKS for independently deployed services or richer orchestration.",
],
"cleanup": r"""az webapp delete -g rg-ai200-containers -n <app-name>
az appservice plan delete -g rg-ai200-containers -n plan-ai200 --yes""",
},
# ---------------------------------------------------------------- 1.4
{
"id": "1.4",
"title": "Deploy to Azure Container Apps with revisions and traffic splitting",
"time": "30 min",
"level": "Core",
"objective": "Create a Container Apps environment, deploy the image, roll out a new revision, and split traffic between revisions for a canary release.",
"exam": [
 "A Container Apps <b>environment</b> is a deployment and networking boundary. Apps in it share the environment network and configured log destination; Log Analytics is optional, not inherent.",
 "<b>Revisions</b> are immutable snapshots of an app's config + image. <b>Single</b> revision mode keeps only the latest active; <b>Multiple</b> revision mode lets several run at once for traffic splitting / canary / blue-green.",
 "A change to a <b>revision-scope</b> property (image tag, env vars, scale rules) creates a <b>new revision</b>. An <b>application-scope</b> change (secrets, ingress, traffic split) does <b>not</b>.",
 "<b>Ingress</b> can be <b>external</b> to the environment or <b>internal</b>. External ingress is internet-reachable in a public environment, but can be limited to an external virtual network in an internal environment. Target port must match the container's listen port.",
 "Traffic is split by percentage across active revisions with <code>az containerapp ingress traffic set --revision-weight</code> or stable labels with <code>--label-weight</code>. Weights must total 100.",
],
"prereq": "Lab 1.1 image. Azure CLI with the <code>containerapp</code> extension (<code>az extension add -n containerapp</code>) and the <code>Microsoft.App</code> / <code>Microsoft.OperationalInsights</code> providers registered.",
"portal": [
 "##Create the environment + app",
 "Portal \u2192 <b>Container Apps</b> \u2192 <b>+ Create</b>. RG <code>rg-ai200-containers</code>, App name <code>ca-api</code>.",
 "Create a new <b>Container Apps Environment</b> (Consumption workload profile). Choose a log destination explicitly: Log Analytics, Azure Monitor, or none.",
 "<b>Container</b> tab: uncheck 'Use quickstart', Image source <b>Azure Container Registry</b>, image <code>api:v1</code>.",
 "<b>Ingress</b>: Enabled, <b>External</b>, Target port <code>8000</code>. <b>Create</b>. Browse the app FQDN.",
 "##Enable multiple-revision mode",
 "App \u2192 <b>Revision management</b> \u2192 set <b>Revision mode</b> to <b>Multiple</b> \u2192 Save.",
 "##Roll out a new revision",
 "App \u2192 <b>Revision management</b> \u2192 <b>+ Create new revision</b> \u2192 change the image tag to <code>api:v2</code>, add a suffix <code>v2</code> \u2192 <b>Create</b>.",
 "##Split traffic (canary)",
 "On <b>Revision management</b>, set the traffic weights: <code>v1 = 90%</code>, <code>v2 = 10%</code> \u2192 Save. Refresh the FQDN repeatedly to see the split.",
 "Once happy, shift to <code>v2 = 100%</code> and <b>Deactivate</b> the old revision.",
],
"cli": r"""RG=rg-ai200-containers
ACR="<your-acr-name>"
ENV=cae-ai200
APP=ca-api

az extension add -n containerapp --upgrade
az provider register -n Microsoft.App
az provider register -n Microsoft.OperationalInsights

# --- Environment (network + logging boundary) ---------------------
az containerapp env create -g $RG -n $ENV -l eastus
LOGIN_SERVER=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv)

# --- Deploy the app with external ingress on the container's port --
az containerapp create -g $RG -n $APP --environment $ENV \
  --image "$LOGIN_SERVER/api:v1" \
  --registry-server "$LOGIN_SERVER" --registry-identity system \
  --target-port 8000 --ingress external \
  --min-replicas 1 --max-replicas 5 \
  --env-vars MODEL_DEPLOYMENT=gpt-4o \
  --revision-suffix v1

az containerapp show -g $RG -n $APP --query properties.configuration.ingress.fqdn -o tsv

# --- Switch to multiple-revision mode -----------------------------
az containerapp revision set-mode -g $RG -n $APP --mode multiple

# --- Create a new revision from a new image tag (canary) ----------
az containerapp update -g $RG -n $APP \
  --image "$LOGIN_SERVER/api:v2" --revision-suffix v2

az containerapp revision list -g $RG -n $APP -o table

# --- Split traffic 90/10, then cut over 100% ----------------------
az containerapp ingress traffic set -g $RG -n $APP \
  --revision-weight "${APP}--v1=90" "${APP}--v2=10"

az containerapp ingress traffic set -g $RG -n $APP \
  --revision-weight "${APP}--v1=0" "${APP}--v2=100"
""",
"code": r"""# containerapp.yaml - declarative deployment (az containerapp create --yaml).
# Everything under template.* is REVISION-scoped: change it and you get a new
# revision. configuration.* (ingress, secrets, traffic) is APPLICATION-scoped.
identity:
  type: SystemAssigned
properties:
  environmentId: /subscriptions/<sub>/resourceGroups/rg-ai200-containers/providers/Microsoft.App/managedEnvironments/cae-ai200
  configuration:
    activeRevisionsMode: Multiple           # required for traffic splitting
    ingress:
      external: true
      targetPort: 8000
      traffic:
        - revisionName: ca-api--v1
          weight: 90
        - latestRevision: true
          weight: 10
    secrets:
      - name: openai-key
        keyVaultUrl: https://<vault>.vault.azure.net/secrets/openai-api-key
        identity: system
    registries:
      - server: <registry-login-server>
        identity: system                    # managed-identity pull, no password
  template:
    containers:
      - image: <registry-login-server>/api:v2
        name: api
        env:
          - name: MODEL_DEPLOYMENT
            value: gpt-4o
          - name: OPENAI_KEY
            secretRef: openai-key
        resources:
          cpu: 0.5
          memory: 1Gi
    scale:
      minReplicas: 1
      maxReplicas: 5""",
"code_label": "containerapp.yaml",
"traps": [
 "Traffic splitting silently does nothing in <b>Single</b> revision mode \u2014 you must switch to <b>Multiple</b> first.",
 "Changing <b>ingress</b> or a <b>secret</b> does NOT create a new revision (application-scope). Changing the <b>image</b>, <b>env vars</b> or <b>scale rules</b> does (revision-scope). Exam loves this distinction.",
 "Traffic weights must sum to <b>100</b>; a set that totals 90 is rejected.",
 "Revision names are generated from the app name plus suffix. Set a known suffix or query <code>az containerapp revision list</code>; do not invent revision names in a traffic command.",
 "External ingress does not always mean public internet. In an internal Container Apps environment, it is external to the app environment but reachable only from the environment's virtual network.",
 "<code>--min-replicas 0</code> lets the app scale to zero (cheap, but adds cold-start latency). If the question needs no cold start, min must be \u2265 1.",
 "App Service vs Container Apps vs AKS: choose <b>Container Apps</b> for serverless microservices with event scaling and no cluster to manage; choose <b>AKS</b> only when you need full Kubernetes control.",
],
"cleanup": r"""# Deferred: Lab 1.5 reuses this environment and API app.
# Run the consolidated Container Apps cleanup after Lab 1.5.""",
},
# ---------------------------------------------------------------- 1.5
{
"id": "1.5",
"title": "Event-driven scaling in Container Apps with KEDA",
"time": "30 min",
"level": "Advanced",
"objective": "Deploy a real Service Bus queue worker, grant its system identity data-plane access, and scale it from zero with the managed-identity KEDA scaler.",
"exam": [
 "Container Apps autoscaling uses <b>KEDA</b>. You declare HTTP, TCP, or custom event rules; you do not install KEDA yourself.",
 "HTTP, TCP and custom event-driven rules can scale to zero when <code>minReplicas</code> is 0. Keep at least one replica when the workload cannot tolerate cold starts.",
 "A queue rule sets a target such as <code>messageCount=5</code>, interpreted as approximate backlog per replica, and min/max replica bounds cap the result.",
 "Prefer <code>--scale-rule-identity system</code> or a user-assigned identity over a connection-string secret. The same principal needs an Azure Service Bus data-plane role that lets both the scaler inspect the queue and the worker receive messages.",
 "The polling interval governs checks while at zero. The KEDA cooldown period applies when scaling from one replica to zero; ordinary one-to-many scale-down is controlled by the replica/HPA behavior.",
 "For an event worker that does not receive revision-routed HTTP traffic, use <b>Single</b> revision mode unless you intentionally want multiple active worker revisions consuming concurrently.",
],
"prereq": "Lab 1.4 environment, Lab 1.1 ACR, and the Service Bus namespace from Lab 3.1. Run the code tab to create the complete worker build context before the CLI steps.",
"portal": [
 "##Deploy the worker and grant access",
 "Run the code-tab script to create <code>worker.py</code>, <code>requirements.txt</code> and <code>Dockerfile</code>. Build that context as <code>worker:v1</code>, then create <code>ca-worker</code> in the Lab 1.4 environment with no ingress and a system-assigned identity.",
 "Service Bus namespace \u2192 <b>Access control (IAM)</b> \u2192 assign the worker identity <b>Azure Service Bus Data Receiver</b>. Wait for RBAC propagation.",
 "##Add a custom Service Bus scale rule",
 "Managed-identity authentication for a Container Apps scale rule cannot currently be configured in the portal. Use the CLI/ARM step in the CLI tab to add rule <code>sb-queue</code>, type <code>azure-servicebus</code>, with the system identity.",
 "Rule metadata: <code>queueName</code> = <code>jobs</code>, <code>messageCount</code> = <code>5</code>, <code>namespace</code> = your SB namespace. No Service Bus connection string is needed.",
 "##Set the replica range and inspect",
 "The CLI update sets <b>Min replicas</b> = <code>0</code> and <b>Max replicas</b> = <code>20</code>. To edit the range in the portal, use Worker app \u2192 <b>Scale \u2192 Edit and deploy \u2192 Scale and replicas</b>.",
 "After deployment, return to <b>Revisions and replicas</b> to inspect the new revision created by the scale-rule change.",
 "##Prove it",
 "Send a burst with Service Bus \u2192 queue \u2192 <b>Service Bus Explorer</b>. Azure CLI manages Service Bus resources but has no <code>az servicebus queue send</code> data-plane command.",
 "Worker app \u2192 <b>Monitoring \u2192 Log stream</b> confirms messages are completed. Use <b>Revisions and replicas</b> to watch replicas rise, then return to zero after the queue drains and cooldown expires.",
],
"cli": r"""RG=rg-ai200-containers
SB_RG=rg-ai200-connect
ACR="<your-acr-name>"
APP=ca-worker
SBNS="<servicebus-namespace>"
ENV=cae-ai200
QUEUE=jobs

# Create the lab queue in the existing namespace.
az servicebus queue create -g "$SB_RG" \
  --namespace-name "$SBNS" -n "$QUEUE"

# First run the code tab from this working directory. It creates ./worker
# with the Python source, dependency manifest and worker-specific Dockerfile.
az acr build -r "$ACR" -t worker:v1 ./worker

LOGIN_SERVER=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv)

# Create a no-ingress worker with a system identity for ACR and Service Bus.
az containerapp create -g "$RG" -n "$APP" --environment "$ENV" \
  --image "$LOGIN_SERVER/worker:v1" \
  --registry-server "$LOGIN_SERVER" --registry-identity system \
  --system-assigned \
  --min-replicas 0 --max-replicas 20 \
  --env-vars \
    SERVICE_BUS_FQDN="$SBNS.servicebus.windows.net" \
    SERVICE_BUS_QUEUE="$QUEUE"

PRINCIPAL_ID=$(az containerapp identity show -g "$RG" -n "$APP" \
  --query principalId -o tsv)
SB_ID=$(az servicebus namespace show -g "$SB_RG" -n "$SBNS" \
  --query id -o tsv)

az role assignment create \
  --assignee-object-id "$PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --role "Azure Service Bus Data Receiver" \
  --scope "$SB_ID"

sleep 60
az containerapp revision set-mode -g "$RG" -n "$APP" --mode single

# Managed-identity scaler: no --scale-rule-auth or connection secret.
az containerapp update -g "$RG" -n "$APP" \
  --min-replicas 0 --max-replicas 20 \
  --scale-rule-name sb-queue \
  --scale-rule-type azure-servicebus \
  --scale-rule-metadata \
    "queueName=$QUEUE" "messageCount=5" "namespace=$SBNS" \
  --scale-rule-identity system

# Azure CLI cannot send messages. Use Service Bus Explorer or an SDK producer.
az containerapp logs show -g "$RG" -n "$APP" --type console --follow false
az containerapp revision list -g "$RG" -n "$APP" -o table
az containerapp replica list -g "$RG" -n "$APP" -o table""",
"code": r"""# Run once from your working directory to create the complete build context.
mkdir -p worker

cat > worker/requirements.txt <<'EOF'
azure-identity>=1.17,<2
azure-servicebus>=7.12,<8
aiohttp>=3.9,<4
EOF

cat > worker/Dockerfile <<'EOF'
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py .

RUN useradd --create-home --uid 10001 appuser
USER appuser

CMD ["python", "worker.py"]
EOF

cat > worker/worker.py <<'PY'
import asyncio
import logging
import os

from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

fully_qualified_namespace = os.environ["SERVICE_BUS_FQDN"]
queue_name = os.environ.get("SERVICE_BUS_QUEUE", "jobs")


async def process_messages():
    credential = DefaultAzureCredential()

    async with credential:
        async with ServiceBusClient(
            fully_qualified_namespace=fully_qualified_namespace,
            credential=credential,
        ) as client:
            receiver = client.get_queue_receiver(queue_name=queue_name)

            async with receiver:
                while True:
                    messages = await receiver.receive_messages(
                        max_message_count=10,
                        max_wait_time=20,
                    )
                    if not messages:
                        continue

                    for message in messages:
                        try:
                            logger.info(
                                "Processing message_id=%s",
                                message.message_id,
                            )
                            # Replace this line with idempotent business logic.
                            await receiver.complete_message(message)
                        except Exception:
                            logger.exception(
                                "Processing failed for message_id=%s",
                                message.message_id,
                            )
                            await receiver.abandon_message(message)


if __name__ == "__main__":
    asyncio.run(process_messages())
PY""",
"code_label": "Worker build context (Bash)",
"traps": [
 "HTTP, TCP and custom event-driven scalers can reach zero when <code>minReplicas: 0</code>. Any app left at <code>minReplicas: 1</code> stays warm regardless of queue depth.",
 "<code>messageCount</code> is the backlog <i>per replica</i>, not a total \u2014 <code>messageCount=5</code> with 100 messages targets ~20 replicas (capped by maxReplicas).",
 "With managed identity, use <code>--scale-rule-identity</code>, not <code>--scale-rule-auth</code>. A missing Service Bus data-plane role means neither scaling nor message consumption succeeds.",
 "The current Container Apps CLI marks <code>--scale-rule-identity</code> as Preview even though managed-identity authentication is the recommended design; validate extension/version support in automation.",
 "Scaling replicas without a long-running receiver only produces idle containers. The image must actually receive and settle queue messages.",
 "When multiple rules exist, KEDA takes the <b>maximum</b> replica count any rule demands, not the sum.",
 "KEDA cooldown specifically delays the one-to-zero transition. Do not apply that statement indiscriminately to every scale-down step.",
 "Multiple revision mode can leave several worker revisions consuming at once. Prefer single revision mode for queue workers unless that concurrency is deliberate.",
],
"cleanup": r"""az role assignment delete \
  --assignee "$PRINCIPAL_ID" \
  --role "Azure Service Bus Data Receiver" \
  --scope "$SB_ID"

az containerapp delete -g rg-ai200-containers -n ca-worker --yes
az servicebus queue delete -g "$SB_RG" \
  --namespace-name "$SBNS" -n jobs
az containerapp delete -g rg-ai200-containers -n ca-api --yes
az containerapp env delete -g rg-ai200-containers -n cae-ai200 --yes""",
},
# ---------------------------------------------------------------- 1.6
{
"id": "1.6",
"title": "Deploy, monitor and troubleshoot an app on AKS with manifests",
"time": "40 min",
"level": "Advanced",
"objective": "Stand up an AKS cluster attached to ACR, deploy an app with Deployment + Service manifests, then diagnose a failing pod using logs, events and connectivity checks.",
"exam": [
 "For a classic-RBAC registry, <code>az aks create/update --attach-acr</code> grants the kubelet identity <b>AcrPull</b>, so no imagePullSecret is needed. For an ABAC-enabled registry, do not use that integration path; grant <b>Container Registry Repository Reader</b> manually.",
 "A <b>Deployment</b> manages replicas via a ReplicaSet. An AKS <b>LoadBalancer</b> Service is public by default but can be internal with the Azure annotation; <b>ClusterIP</b> is internal-only, and <b>NodePort</b> opens a port on each node.",
 "Troubleshooting order: <code>kubectl get</code> status \u2192 <code>describe</code> events \u2192 current/<code>--previous</code> logs \u2192 Service/EndpointSlice checks \u2192 an in-cluster DNS/HTTP probe \u2192 network policy, ingress, load balancer and DNS.",
 "<b>CrashLoopBackOff</b> means repeated exits; <b>Pending</b> means unschedulable or unbound; <b>ImagePullBackOff</b> can mean a bad image reference, registry role, identity mismatch, network/DNS/firewall restriction, or ACR integration mode.",
 "<b>Startup</b> protects slow initialization; <b>readiness</b> gates Service traffic without restarting; <b>liveness</b> restarts a stuck container.",
 "Resource <b>requests</b> drive scheduling and reserve capacity; <b>limits</b> cap usage. CPU over its limit is throttled, while memory over its limit can terminate the container with OOMKilled.",
 "<b>Container Insights</b> collects container logs, inventory and performance data; <b>managed Prometheus</b> collects Prometheus metrics; AKS <b>diagnostic settings</b> route control-plane resource logs. They are complementary, not synonyms.",
],
"prereq": "Lab 1.1 image in ACR. Azure CLI with <code>kubectl</code> (<code>az aks install-cli</code>).",
"portal": [
 "##Create the cluster attached to ACR",
 "Portal \u2192 <b>Kubernetes services</b> \u2192 <b>+ Create</b> \u2192 <b>Kubernetes cluster</b>. RG <code>rg-ai200-containers</code>, name <code>aks-ai200</code>, system node size <code>Standard_D4s_v5</code>, node count 2.",
 "<b>Integrations</b> tab \u2192 select your ACR for a classic-RBAC registry. For ABAC, grant the kubelet identity <b>Container Registry Repository Reader</b> manually instead.",
 "Enable <b>Container Insights</b> for logs/inventory/performance. Configure <b>Azure Monitor managed service for Prometheus</b> separately for Prometheus metrics, and diagnostic settings when control-plane logs must be retained.",
 "##Get credentials & deploy",
 "Cluster \u2192 <b>Connect</b> shows the <code>az aks get-credentials</code> command; run it in Cloud Shell, then <code>kubectl apply -f deploy.yaml</code> (see code tab).",
 "##Observe",
 "Cluster \u2192 <b>Workloads</b> \u2192 see the <b>Deployment</b> and its pods; <b>Services and ingresses</b> shows the LoadBalancer's external IP.",
 "Cluster \u2192 <b>Monitoring \u2192 Insights</b> for Container Insights. Use the Azure Monitor workspace / Grafana path for managed Prometheus, and <b>Diagnostic settings</b> for control-plane categories.",
 "##Troubleshoot",
 "If a pod is unhealthy, open it \u2192 <b>Events</b> and <b>Live logs</b>. Match the status (<i>ImagePullBackOff / CrashLoopBackOff / Pending</i>) to the fix in the traps below.",
],
"cli": r"""RG=rg-ai200-containers
ACR="<your-acr-name>"
AKS=aks-ai200

az aks install-cli   # if kubectl/kubelogin not present

# --- Cluster with ACR attached + monitoring add-on ----------------
az aks create -g $RG -n $AKS \
  --node-count 2 --node-vm-size Standard_D4s_v5 \
  --enable-managed-identity \
  --attach-acr $ACR \
  --enable-addons monitoring \
  --generate-ssh-keys

az aks get-credentials -g $RG -n $AKS   # writes kubeconfig
LOGIN_SERVER=$(az acr show -g "$RG" -n "$ACR" --query loginServer -o tsv)
az aks check-acr -g "$RG" -n "$AKS" --acr "$LOGIN_SERVER"

# --- Deploy from manifests ----------------------------------------
kubectl apply -f deploy.yaml
kubectl get deploy,pods,svc -o wide
kubectl get svc api-svc -w        # wait for the LoadBalancer EXTERNAL-IP

# --- TROUBLESHOOTING WORKFLOW -------------------------------------
kubectl get pods                       # 1) status column tells the story
kubectl describe pod <pod>             # 2) scroll to Events (pull/schedule/probe)
kubectl logs <pod>                     # 3) app stdout/stderr
kubectl logs <pod> --previous          # crash loop: logs of the last dead container
kubectl get svc api-svc -o wide
kubectl get endpointslice -l kubernetes.io/service-name=api-svc

# 4) Test DNS and Service routing from inside the cluster.
kubectl run netcheck --rm -it --restart=Never \
  --image=busybox:1.36 -- sh
# Inside the temporary pod:
# nslookup api-svc
# wget -S -O- http://api-svc/healthz

# 5) Resolve a backing pod through the Service and tunnel directly to it.
# This bypasses ingress, the load balancer and ClusterIP/kube-proxy routing.
kubectl port-forward service/api-svc 8080:80
kubectl get events --sort-by=.metadata.creationTimestamp

# Classic-RBAC registry only. For ABAC, grant Repository Reader manually.
az aks update -g $RG -n $AKS --attach-acr $ACR""",
"code": r"""# deploy.yaml - Deployment + Service with probes (apply with `kubectl apply -f`).
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  selector:
    matchLabels: { app: api }
  template:
    metadata:
      labels: { app: api }
    spec:
      containers:
        - name: api
          image: <registry-login-server>/api:v1  # query ACR loginServer
          ports:
            - containerPort: 8000
          env:
            - name: MODEL_DEPLOYMENT
              value: gpt-4o
          resources:                          # requests schedule; limits constrain runtime
            requests: { cpu: "100m", memory: "128Mi" }
            limits:   { cpu: "500m", memory: "256Mi" }
          startupProbe:                        # protects slow startup from liveness restarts
            httpGet: { path: /healthz, port: 8000 }
            periodSeconds: 5
            failureThreshold: 30
          readinessProbe:                      # gates traffic; failing = no endpoints
            httpGet: { path: /healthz, port: 8000 }
            periodSeconds: 5
          livenessProbe:                       # failing = container RESTART
            httpGet: { path: /healthz, port: 8000 }
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: api-svc
spec:
  type: LoadBalancer      # public by default; an Azure annotation makes it internal
  selector: { app: api }
  ports:
    - port: 80
      targetPort: 8000""",
"code_label": "YAML manifest",
"traps": [
 "<b>ImagePullBackOff</b> is broader than a missing attach: verify the complete login server/repository/tag or digest, kubelet identity and role, ABAC mode, private endpoint/firewall/DNS path, and node reachability. Use <code>az aks check-acr</code>.",
 "<b>CrashLoopBackOff</b> \u2192 app is exiting; the useful log is <code>kubectl logs &lt;pod&gt; --previous</code>, not the current (already-dead) container.",
 "<b>Pending</b> forever \u2192 no schedulable node: insufficient CPU/memory <code>requests</code>, node quota, or a taint with no matching toleration. <code>kubectl describe pod</code> Events say which.",
 "Requests are not caps: CPU can burst above a request until constrained, and memory usage over the limit can be OOM-killed. A startup probe is safer than inflating liveness delays for slow initialization.",
 "Liveness vs readiness: a failing <b>liveness</b> probe restarts the container; a failing <b>readiness</b> probe removes it from Service endpoints until healthy.",
 "<code>Service</code> type <b>ClusterIP</b> has no external IP by design \u2014 if you expected a public endpoint you wanted <b>LoadBalancer</b> (or an Ingress).",
 "Port-forward proves a local-to-pod/Service path but not cluster DNS, pod-to-Service networking, ingress, load balancer health, public DNS or client reachability. Test from the inside out.",
 "Container Insights, managed Prometheus and control-plane diagnostic settings solve different observability needs; enabling one does not automatically enable the other two.",
],
"cleanup": r"""az aks delete -g rg-ai200-containers -n aks-ai200 --yes --no-wait
# or nuke everything from this domain:
az group delete -n rg-ai200-containers --yes --no-wait""",
},
]
