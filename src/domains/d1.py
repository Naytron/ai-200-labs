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
 "ACR SKUs \u2014 <b>Basic / Standard / Premium</b>. Only <b>Premium</b> adds geo-replication, private link, content-trust and larger throughput. Geo-replication is a common distractor answer for Basic/Standard.",
 "<code>az acr build</code> runs the Docker build <i>in the cloud</i> using an ACR Task \u2014 you do <b>not</b> need a local Docker daemon. This is the exam's preferred answer when the question says 'no Docker installed'.",
 "Authentication order of preference: <b>Microsoft Entra token</b> (<code>az acr login</code>) &gt; repository-scoped tokens &gt; <b>admin user</b>. The admin account is disabled by default and is for testing only.",
 "A tag is mutable by default; the same tag can be re-pushed. Use <code>az acr repository update --write-enabled false</code> or image <b>lock</b> to make a specific version immutable.",
 "Pulling an image needs the <b>AcrPull</b> role; pushing needs <b>AcrPush</b>. Don't hand out Contributor just to pull.",
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
 "Registry \u2192 <b>Access keys</b> \u2192 note the <b>Login server</b> (<code>ai200acr&lt;unique&gt;.azurecr.io</code>). Leave <b>Admin user</b> <i>disabled</i>.",
],
"cli": r"""RG=rg-ai200-containers
LOC=eastus
ACR=ai200acr$RANDOM          # must be globally unique, lowercase alphanumerics

az group create -n $RG -l $LOC

# --- Create the registry (Standard SKU) ----------------------------
az acr create -g $RG -n $ACR --sku Standard

# --- Build IN THE CLOUD (no local Docker daemon needed) ------------
# Run from a folder that contains a Dockerfile:
az acr build -r $ACR -t api:v1 -t api:latest .

# --- Authenticate & list ------------------------------------------
az acr login -n $ACR                       # uses your Entra token
az acr repository list -n $ACR -o table
az acr repository show-tags -n $ACR --repository api -o table

# --- Inspect the manifest / digest --------------------------------
az acr manifest list-metadata -r $ACR -n api -o table
az acr repository show -n $ACR --image api:v1

# --- Version a second build & make v1 immutable -------------------
az acr build -r $ACR -t api:v2 .
az acr repository update -n $ACR --image api:v1 --write-enabled false

# --- Grant least-privilege pull to a service principal ------------
ACR_ID=$(az acr show -n $ACR --query id -o tsv)
az role assignment create --assignee <sp-app-id> --role AcrPull --scope $ACR_ID""",
"code": r"""# Dockerfile - a minimal Python API image that ACR will build for you.
# `az acr build` ships THIS context to the registry and runs the build there.

FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# App Service & Container Apps route to whatever you EXPOSE / listen on.
ENV PORT=8000
EXPOSE 8000

# Use a non-root user (exam favours least privilege in containers too)
RUN useradd -m appuser
USER appuser

CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]""",
"code_label": "Dockerfile",
"traps": [
 "<code>az acr build</code> vs <code>docker build</code>: if the question says 'the developer has no Docker Desktop / build agent', the answer is <b>az acr build</b> (server-side Task), not 'install Docker'.",
 "Registry <b>name</b> is alphanumeric only and globally unique; the <b>login server</b> is always <code>&lt;name&gt;.azurecr.io</code>. You cannot rename a registry.",
 "Geo-replication, private endpoints and content trust require <b>Premium</b>. Selecting Standard and expecting geo-replication is a classic wrong answer.",
 "Enabling the <b>admin user</b> to let an app pull is the <i>wrong</i> answer \u2014 assign <b>AcrPull</b> to the app's managed identity instead.",
],
"cleanup": r"""az group delete -n rg-ai200-containers --yes --no-wait""",
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
 "A task can auto-rebuild when the <b>base image</b> it derives <code>FROM</code> gets patched \u2014 this is the headline feature for keeping images CVE-free. Trigger type <code>--base-image-trigger-enabled</code>.",
 "Git triggers need a <b>PAT</b> (repo access token) passed with <code>--git-access-token</code>; commit and pull-request triggers are separate toggles.",
 "Multi-step tasks (<code>acr-task.yaml</code>) express <code>build</code>, <code>push</code> and <code>cmd</code> steps \u2014 <code>cmd</code> runs an arbitrary container (e.g. to run tests) between build and push.",
 "Tasks honour <code>--platform linux/arm64</code> etc. for cross-arch builds without a matching local machine.",
],
"prereq": "Lab 1.1 registry. For the Git trigger, a GitHub repo with a Dockerfile and a PAT with <code>repo</code> scope.",
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
  # 1) Build the image (not pushed yet)
  - build: -t $Registry/api:$ID .
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
 "'Keep the image patched when the OS base image is updated' \u2192 the answer is an <b>ACR Task with a base-image trigger</b>, not a scheduled pipeline or manual rebuild.",
 "Multi-step <code>cmd</code> steps run a container \u2014 use them for tests/scans <i>between</i> build and push. A test failure stops the push; that gate is the point.",
 "Git commit triggers require a PAT; a fine-grained token missing <code>repo</code> scope silently never fires.",
 "<code>{{.Run.ID}}</code> gives every build a unique immutable tag \u2014 preferred over reusing <code>latest</code> for traceability.",
],
},
# ---------------------------------------------------------------- 1.3
{
"id": "1.3",
"title": "Deploy a container to Azure App Service with env vars and secrets",
"time": "30 min",
"level": "Core",
"objective": "Run your ACR image as a Web App for Containers, supply configuration through app settings, and pull secrets from Key Vault via a managed identity + Key Vault reference.",
"exam": [
 "<b>Web App for Containers</b> runs a single container on App Service. App settings become <b>environment variables</b> in the container \u2014 this is how you inject config without rebaking the image.",
 "App Service must be told which port your container listens on via the <code>WEBSITES_PORT</code> app setting when it isn't 80/8080.",
 "To pull from ACR without a password, turn on the web app's <b>system-assigned managed identity</b> and give it <b>AcrPull</b> \u2014 set <code>acrUseManagedIdentityCreds</code>. Storing ACR admin credentials in config is the wrong answer.",
 "<b>Key Vault references</b> in app settings use the syntax <code>@Microsoft.KeyVault(SecretUri=...)</code>; the app's managed identity needs <b>Key Vault Secrets User</b> (RBAC) or a <b>get</b> access policy. The secret value is never stored in App Service.",
 "Deployment slots let you warm up a new revision and <b>swap</b> with zero downtime; slot settings marked 'sticky' don't travel during a swap.",
],
"prereq": "Labs 1.1 image and a Key Vault (Lab 4.1 covers Key Vault creation). Azure CLI 2.x.",
"portal": [
 "##Create the Web App for Containers",
 "Portal \u2192 <b>App Services</b> \u2192 <b>+ Create</b> \u2192 <b>Web App</b>. Publish <b>Container</b>, OS <b>Linux</b>, Plan a Linux <b>B1</b>.",
 "<b>Container</b> tab: Image Source <b>Azure Container Registry</b>, pick your registry, image <code>api</code>, tag <code>v1</code>. <b>Review + create</b>.",
 "##Let the app pull from ACR with an identity",
 "App \u2192 <b>Identity</b> \u2192 System assigned \u2192 <b>On</b>. Copy the object ID.",
 "Registry \u2192 <b>Access control (IAM)</b> \u2192 <b>+ Add role assignment</b> \u2192 <b>AcrPull</b> \u2192 assign to the web app's identity.",
 "App \u2192 <b>Deployment Center</b> \u2192 set <b>Authentication</b> to <b>Managed identity</b>.",
 "##Configuration & secrets",
 "App \u2192 <b>Settings \u2192 Environment variables</b> \u2192 <b>App settings</b> \u2192 add <code>WEBSITES_PORT</code> = <code>8000</code> and <code>MODEL_DEPLOYMENT</code> = <code>gpt-4o</code>.",
 "Add a secret-backed setting: name <code>OPENAI_KEY</code>, value <code>@Microsoft.KeyVault(SecretUri=https://&lt;vault&gt;.vault.azure.net/secrets/openai-key/)</code>.",
 "Grant the app <b>Key Vault Secrets User</b> on the vault (IAM). Restart the app and confirm the reference resolves (green tick on the setting).",
 "##Zero-downtime release",
 "App \u2192 <b>Deployment slots</b> \u2192 <b>+ Add slot</b> <code>staging</code> \u2192 point it at tag <code>v2</code> \u2192 test \u2192 <b>Swap</b>.",
],
"cli": r"""RG=rg-ai200-containers
ACR=<your-acr-name>
APP=ai200-api-$RANDOM
PLAN=plan-ai200
VAULT=<your-keyvault-name>

# --- Plan + Web App for Containers --------------------------------
az appservice plan create -g $RG -n $PLAN --is-linux --sku B1
az webapp create -g $RG -p $PLAN -n $APP \
  --deployment-container-image-name $ACR.azurecr.io/api:v1

# --- Pull from ACR using the app's managed identity (no passwords) -
az webapp identity assign -g $RG -n $APP
PRINCIPAL=$(az webapp identity show -g $RG -n $APP --query principalId -o tsv)
ACR_ID=$(az acr show -n $ACR --query id -o tsv)
az role assignment create --assignee $PRINCIPAL --role AcrPull --scope $ACR_ID
az webapp config set -g $RG -n $APP --generic-configurations '{"acrUseManagedIdentityCreds": true}'

# --- App settings become container environment variables ----------
az webapp config appsettings set -g $RG -n $APP --settings \
  WEBSITES_PORT=8000 \
  MODEL_DEPLOYMENT=gpt-4o

# --- Key Vault reference: secret stays in the vault ---------------
az role assignment create --assignee $PRINCIPAL \
  --role "Key Vault Secrets User" \
  --scope $(az keyvault show -n $VAULT --query id -o tsv)

az webapp config appsettings set -g $RG -n $APP --settings \
  "OPENAI_KEY=@Microsoft.KeyVault(SecretUri=https://$VAULT.vault.azure.net/secrets/openai-key/)"

# --- Zero-downtime slot swap --------------------------------------
az webapp deployment slot create -g $RG -n $APP --slot staging
az webapp config container set -g $RG -n $APP --slot staging \
  --docker-custom-image-name $ACR.azurecr.io/api:v2
az webapp deployment slot swap -g $RG -n $APP --slot staging --target-slot production""",
"code": r"""# app.py - the containerised API. Notice it reads ALL config from the
# environment: App Service app settings and Key Vault references land here,
# so the SAME image runs in dev/stage/prod with no rebuild.
import os
from flask import Flask, jsonify

app = Flask(__name__)

MODEL      = os.environ["MODEL_DEPLOYMENT"]          # from an app setting
OPENAI_KEY = os.environ["OPENAI_KEY"]                # from a Key Vault reference
PORT       = int(os.environ.get("PORT", "8000"))     # matches WEBSITES_PORT

@app.get("/healthz")
def health():
    # never echo the secret - just prove it resolved
    return jsonify(status="ok", model=MODEL, key_loaded=bool(OPENAI_KEY))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)""",
"code_label": "Python app",
"traps": [
 "Container starts but the site shows 'Application Error' \u2192 usually the listen port. Set <code>WEBSITES_PORT</code> to the port your app binds, or make the app read <code>$PORT</code>.",
 "Image pull fails after enabling identity \u2192 you also must set <code>acrUseManagedIdentityCreds=true</code> and grant <b>AcrPull</b>; identity alone isn't enough.",
 "A Key Vault reference showing a red error is almost always a missing <b>Key Vault Secrets User</b> role or a wrong <code>SecretUri</code> (trailing slash / version).",
 "Slot settings you want to <i>stay put</i> during a swap must be marked <b>Deployment slot setting</b> (sticky) \u2014 otherwise they follow the swap.",
 "App Service runs <b>one</b> container per app. If the question needs multiple containers or sidecars with independent scaling, that's <b>Container Apps</b> or <b>AKS</b>, not Web App for Containers.",
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
 "A Container Apps <b>environment</b> is the security/network boundary; apps in the same environment share a Log Analytics workspace and can talk over the internal network.",
 "<b>Revisions</b> are immutable snapshots of an app's config + image. <b>Single</b> revision mode keeps only the latest active; <b>Multiple</b> revision mode lets several run at once for traffic splitting / canary / blue-green.",
 "A change to a <b>revision-scope</b> property (image tag, env vars, scale rules) creates a <b>new revision</b>. An <b>application-scope</b> change (secrets, ingress, traffic split) does <b>not</b>.",
 "<b>Ingress</b> can be <b>external</b> (public FQDN) or <b>internal</b> (only within the environment). Target port must match the container's listen port.",
 "Traffic is split by <b>percentage</b> across revisions with <code>--traffic-weight</code>; use <code>latest=</code> or <code>revision-name=</code> labels. Weights must total 100.",
],
"prereq": "Lab 1.1 image. Azure CLI with the <code>containerapp</code> extension (<code>az extension add -n containerapp</code>) and the <code>Microsoft.App</code> / <code>Microsoft.OperationalInsights</code> providers registered.",
"portal": [
 "##Create the environment + app",
 "Portal \u2192 <b>Container Apps</b> \u2192 <b>+ Create</b>. RG <code>rg-ai200-containers</code>, App name <code>ca-api</code>.",
 "Create a new <b>Container Apps Environment</b> (Consumption plan). It provisions a Log Analytics workspace for you.",
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
ACR=<your-acr-name>
ENV=cae-ai200
APP=ca-api

az extension add -n containerapp --upgrade
az provider register -n Microsoft.App
az provider register -n Microsoft.OperationalInsights

# --- Environment (network + logging boundary) ---------------------
az containerapp env create -g $RG -n $ENV -l eastus

# --- Deploy the app with external ingress on the container's port --
az containerapp create -g $RG -n $APP --environment $ENV \
  --image $ACR.azurecr.io/api:v1 \
  --registry-server $ACR.azurecr.io --registry-identity system \
  --target-port 8000 --ingress external \
  --min-replicas 1 --max-replicas 5 \
  --env-vars MODEL_DEPLOYMENT=gpt-4o

az containerapp show -g $RG -n $APP --query properties.configuration.ingress.fqdn -o tsv

# --- Switch to multiple-revision mode -----------------------------
az containerapp revision set-mode -g $RG -n $APP --mode multiple

# --- Create a new revision from a new image tag (canary) ----------
az containerapp update -g $RG -n $APP \
  --image $ACR.azurecr.io/api:v2 --revision-suffix v2

az containerapp revision list -g $RG -n $APP -o table

# --- Split traffic 90/10, then cut over 100% ----------------------
az containerapp ingress traffic set -g $RG -n $APP \
  --revision-weight <app>--v1=90 <app>--v2=10

az containerapp ingress traffic set -g $RG -n $APP \
  --revision-weight latest=100""",
"code": r"""# containerapp.yaml - declarative deployment (az containerapp create --yaml).
# Everything under template.* is REVISION-scoped: change it and you get a new
# revision. configuration.* (ingress, secrets, traffic) is APPLICATION-scoped.
properties:
  managedEnvironmentId: /subscriptions/<sub>/resourceGroups/rg-ai200-containers/providers/Microsoft.App/managedEnvironments/cae-ai200
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
        keyVaultUrl: https://<vault>.vault.azure.net/secrets/openai-key
        identity: system
    registries:
      - server: <acr>.azurecr.io
        identity: system                    # managed-identity pull, no password
  template:
    containers:
      - image: <acr>.azurecr.io/api:v2
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
 "<code>--min-replicas 0</code> lets the app scale to zero (cheap, but adds cold-start latency). If the question needs no cold start, min must be \u2265 1.",
 "App Service vs Container Apps vs AKS: choose <b>Container Apps</b> for serverless microservices with event scaling and no cluster to manage; choose <b>AKS</b> only when you need full Kubernetes control.",
],
"cleanup": r"""az containerapp delete -g rg-ai200-containers -n ca-api --yes
az containerapp env delete -g rg-ai200-containers -n cae-ai200 --yes""",
},
# ---------------------------------------------------------------- 1.5
{
"id": "1.5",
"title": "Event-driven scaling in Container Apps with KEDA",
"time": "30 min",
"level": "Advanced",
"objective": "Add a KEDA scale rule so a Container App scales out on Azure Service Bus queue depth (and scales to zero when idle), using a managed-identity auth reference.",
"exam": [
 "Container Apps' autoscaling <b>is</b> KEDA \u2014 you don't install it, you declare <b>scale rules</b>. Rule types: <b>HTTP</b> (concurrent requests), <b>TCP</b>, and <b>custom</b> (any KEDA scaler: Service Bus, Storage Queue, Kafka, Event Hubs, CPU/memory, cron\u2026).",
 "Event-driven (queue) rules can scale <b>to zero</b> replicas when the queue is empty \u2014 the killer feature for spiky back-end workers. HTTP apps can also scale to zero.",
 "A scale rule sets the <b>metric</b> and a <b>target</b> (e.g. <code>messageCount=5</code> \u2192 one replica per 5 queued messages) plus the app's <b>min/max replicas</b> ceiling.",
 "Scaler <b>authentication</b> is wired with <code>--scale-rule-auth</code> pointing a trigger parameter (e.g. <code>connection</code>) at a <b>secret</b>, or better, a <b>managed identity</b>.",
 "KEDA polls on an interval and honours a <b>cooldown</b> before scaling back down; scale-to-zero only happens after the cooldown with no events.",
],
"prereq": "Lab 1.4 Container App and a Service Bus namespace + queue (Lab 3.1). CLI <code>containerapp</code> extension.",
"portal": [
 "##Add a custom (Service Bus) scale rule",
 "App \u2192 <b>Scale and replicas</b> \u2192 edit the app \u2192 <b>Scale rule</b> \u2192 <b>+ Add</b>.",
 "Name <code>sb-queue</code>, Type <b>Custom</b>, Custom rule type <code>azure-servicebus</code>.",
 "Metadata: <code>queueName</code> = <code>jobs</code>, <code>messageCount</code> = <code>5</code>, <code>namespace</code> = your SB namespace.",
 "<b>Authentication</b>: reference a secret that holds the SB connection string, or select the app's <b>managed identity</b>. Save (creates a new revision).",
 "##Set the replica ceiling",
 "Same blade: <b>Min replicas</b> = <code>0</code>, <b>Max replicas</b> = <code>20</code>. Save.",
 "##Prove it",
 "Send a burst of messages to the <code>jobs</code> queue (Service Bus \u2192 queue \u2192 <b>Service Bus Explorer</b> \u2192 send, or the CLI in the code tab).",
 "App \u2192 <b>Revision management</b> \u2192 watch the <b>replica count</b> climb, then fall back to 0 after the queue drains and cooldown elapses.",
],
"cli": r"""RG=rg-ai200-containers
APP=ca-worker
SBNS=<servicebus-namespace>
ENV=cae-ai200

# Store the Service Bus connection as a Container App secret
SB_CONN=$(az servicebus namespace authorization-rule keys list \
  -g $RG --namespace-name $SBNS -n RootManageSharedAccessKey \
  --query primaryConnectionString -o tsv)

az containerapp secret set -g $RG -n $APP \
  --secrets sb-conn="$SB_CONN"

# --- KEDA Service Bus scale rule: 1 replica per 5 queued messages --
az containerapp update -g $RG -n $APP \
  --min-replicas 0 --max-replicas 20 \
  --scale-rule-name sb-queue \
  --scale-rule-type azure-servicebus \
  --scale-rule-metadata "queueName=jobs" "messageCount=5" "namespace=$SBNS" \
  --scale-rule-auth "connection=sb-conn"

# --- Generate load to trigger scale-out ---------------------------
for i in $(seq 1 100); do
  az servicebus queue send -g $RG --namespace-name $SBNS \
    --queue-name jobs --body "job-$i" 2>/dev/null || true
done

# Watch replicas react
watch -n 5 "az containerapp replica list -g $RG -n $APP -o table"

# HTTP concurrency rule (alternative scaler) -----------------------
az containerapp update -g $RG -n ca-api \
  --scale-rule-name http-rule --scale-rule-type http \
  --scale-rule-http-concurrency 50""",
"code": r"""# scale section of containerapp.yaml - the KEDA rule in declarative form.
# A queue scaler that scales to ZERO when 'jobs' is empty.
template:
  scale:
    minReplicas: 0          # scale to zero when idle - core exam point
    maxReplicas: 20
    rules:
      - name: sb-queue
        custom:
          type: azure-servicebus     # any KEDA scaler name goes here
          metadata:
            queueName: jobs
            messageCount: "5"        # target backlog per replica
            namespace: <servicebus-namespace>
          auth:
            - secretRef: sb-conn      # or use managed identity
              triggerParameter: connection
      # You can stack rules; KEDA scales to satisfy the MOST demanding one.
      - name: cpu-rule
        custom:
          type: cpu
          metadata:
            type: Utilization
            value: "70" """,
"code_label": "scale YAML",
"traps": [
 "Only <b>event-driven</b> and HTTP apps scale to zero. A rule left at <code>minReplicas: 1</code> will never reach zero no matter how empty the queue.",
 "<code>messageCount</code> is the backlog <i>per replica</i>, not a total \u2014 <code>messageCount=5</code> with 100 messages targets ~20 replicas (capped by maxReplicas).",
 "Missing / wrong <b>scale-rule-auth</b> is the #1 reason a custom scaler never fires \u2014 the scaler can't read the queue length without credentials.",
 "When multiple rules exist, KEDA takes the <b>maximum</b> replica count any rule demands, not the sum.",
 "Scale-down waits for the <b>cooldown</b>; don't expect instant return to zero the moment the queue empties.",
],
},
# ---------------------------------------------------------------- 1.6
{
"id": "1.6",
"title": "Deploy, monitor and troubleshoot an app on AKS with manifests",
"time": "40 min",
"level": "Advanced",
"objective": "Stand up an AKS cluster attached to ACR, deploy an app with Deployment + Service manifests, then diagnose a failing pod using logs, events and connectivity checks.",
"exam": [
 "Attach ACR to AKS with <code>az aks create --attach-acr</code> (or <code>update --attach-acr</code>) so the kubelet identity gets <b>AcrPull</b> automatically \u2014 no imagePullSecrets needed. <b>ImagePullBackOff</b> almost always means this is missing or the tag is wrong.",
 "A <b>Deployment</b> manages replicas via a ReplicaSet; a <b>Service</b> of type <b>LoadBalancer</b> gets a public IP, <b>ClusterIP</b> is internal-only, <b>NodePort</b> opens a port on each node.",
 "Troubleshooting order: <code>kubectl get pods</code> (status) \u2192 <code>kubectl describe pod</code> (<b>Events</b>: scheduling, pull, probe failures) \u2192 <code>kubectl logs</code> (app stdout) \u2192 <code>kubectl exec</code> / port-forward (connectivity).",
 "<b>CrashLoopBackOff</b> = container starts then exits repeatedly \u2192 read <code>kubectl logs --previous</code>. <b>Pending</b> = can't schedule (resources/quota/taints). <b>ImagePullBackOff</b> = registry auth/tag.",
 "<b>Readiness</b> probe failing takes the pod out of Service endpoints (no traffic) without restarting it; <b>liveness</b> probe failing <i>restarts</i> the container. Container Insights (Azure Monitor for containers) surfaces this in the portal.",
],
"prereq": "Lab 1.1 image in ACR. Azure CLI with <code>kubectl</code> (<code>az aks install-cli</code>).",
"portal": [
 "##Create the cluster attached to ACR",
 "Portal \u2192 <b>Kubernetes services</b> \u2192 <b>+ Create</b> \u2192 <b>Kubernetes cluster</b>. RG <code>rg-ai200-containers</code>, name <code>aks-ai200</code>, node size a small B-series, node count 2.",
 "<b>Integrations</b> tab \u2192 <b>Container registry</b> \u2192 select your ACR (this grants AcrPull to the kubelet identity). Enable <b>Container monitoring</b> (Azure Monitor) \u2192 <b>Create</b>.",
 "##Get credentials & deploy",
 "Cluster \u2192 <b>Connect</b> shows the <code>az aks get-credentials</code> command; run it in Cloud Shell, then <code>kubectl apply -f deploy.yaml</code> (see code tab).",
 "##Observe",
 "Cluster \u2192 <b>Workloads</b> \u2192 see the <b>Deployment</b> and its pods; <b>Services and ingresses</b> shows the LoadBalancer's external IP.",
 "Cluster \u2192 <b>Monitoring \u2192 Insights</b> \u2192 <b>Containers</b> for CPU/memory and per-container logs; <b>Events</b> shows scheduling/pull/probe messages.",
 "##Troubleshoot",
 "If a pod is unhealthy, open it \u2192 <b>Events</b> and <b>Live logs</b>. Match the status (<i>ImagePullBackOff / CrashLoopBackOff / Pending</i>) to the fix in the traps below.",
],
"cli": r"""RG=rg-ai200-containers
ACR=<your-acr-name>
AKS=aks-ai200

az aks install-cli   # if kubectl/kubelogin not present

# --- Cluster with ACR attached + monitoring add-on ----------------
az aks create -g $RG -n $AKS \
  --node-count 2 --node-vm-size Standard_B2s \
  --attach-acr $ACR \
  --enable-addons monitoring \
  --generate-ssh-keys

az aks get-credentials -g $RG -n $AKS   # writes kubeconfig

# --- Deploy from manifests ----------------------------------------
kubectl apply -f deploy.yaml
kubectl get deploy,pods,svc -o wide
kubectl get svc api-svc -w        # wait for the LoadBalancer EXTERNAL-IP

# --- TROUBLESHOOTING WORKFLOW -------------------------------------
kubectl get pods                       # 1) status column tells the story
kubectl describe pod <pod>             # 2) scroll to Events (pull/schedule/probe)
kubectl logs <pod>                     # 3) app stdout/stderr
kubectl logs <pod> --previous          # crash loop: logs of the last dead container
kubectl exec -it <pod> -- sh           # 4) poke around inside
kubectl port-forward <pod> 8080:8000   # test the app locally, bypassing the Service
kubectl get events --sort-by=.lastTimestamp

# Fix a forgotten ACR attach after the fact:
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
          image: <acr>.azurecr.io/api:v1     # AcrPull comes from --attach-acr
          ports:
            - containerPort: 8000
          env:
            - name: MODEL_DEPLOYMENT
              value: gpt-4o
          resources:                          # required or Pending on tight quota
            requests: { cpu: "100m", memory: "128Mi" }
            limits:   { cpu: "500m", memory: "256Mi" }
          readinessProbe:                      # gates traffic; failing = no endpoints
            httpGet: { path: /healthz, port: 8000 }
            initialDelaySeconds: 5
          livenessProbe:                       # failing = container RESTART
            httpGet: { path: /healthz, port: 8000 }
            initialDelaySeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: api-svc
spec:
  type: LoadBalancer      # public IP; use ClusterIP for internal-only
  selector: { app: api }
  ports:
    - port: 80
      targetPort: 8000""",
"code_label": "YAML manifest",
"traps": [
 "<b>ImagePullBackOff</b> \u2192 ACR not attached (<code>--attach-acr</code>) or a typo'd tag. Fix with <code>az aks update --attach-acr</code>; do NOT hand-craft imagePullSecrets when integration exists.",
 "<b>CrashLoopBackOff</b> \u2192 app is exiting; the useful log is <code>kubectl logs &lt;pod&gt; --previous</code>, not the current (already-dead) container.",
 "<b>Pending</b> forever \u2192 no schedulable node: insufficient CPU/memory <code>requests</code>, node quota, or a taint with no matching toleration. <code>kubectl describe pod</code> Events say which.",
 "Liveness vs readiness: a failing <b>liveness</b> probe restarts the container (can mask a slow start \u2014 tune <code>initialDelaySeconds</code>); a failing <b>readiness</b> probe just removes it from the Service until healthy.",
 "<code>Service</code> type <b>ClusterIP</b> has no external IP by design \u2014 if you expected a public endpoint you wanted <b>LoadBalancer</b> (or an Ingress).",
],
"cleanup": r"""az aks delete -g rg-ai200-containers -n aks-ai200 --yes --no-wait
# or nuke everything from this domain:
az group delete -n rg-ai200-containers --yes --no-wait""",
},
]
