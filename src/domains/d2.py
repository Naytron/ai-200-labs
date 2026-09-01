# -*- coding: utf-8 -*-
# Domain 2 - Develop AI solutions by using Azure data management services (25-30%)

DOMAIN = {
    "key": "data",
    "name": "Develop AI Solutions with Azure Data Services",
    "weight": "25\u201330%",
    "blurb": "Cosmos DB for NoSQL, Azure Database for PostgreSQL + pgvector, and Azure Managed Redis back AI apps that need vector search, RAG, change feed processing, caching and RU/query optimisation; expect service-selection questions plus sharp details about partition keys, indexing policies, consistency, vector indexes, connection pooling and invalidation.",
}

LABS = [
# ---------------------------------------------------------------- 2.1
{
"id": "2.1",
"title": "Connect to Azure Cosmos DB for NoSQL and run queries",
"time": "30 min",
"level": "Foundational",
"objective": "Create a Cosmos DB for NoSQL account, database and partitioned container, then insert and query items with the Python SDK.",
"exam": [
 "Cosmos DB for NoSQL stores JSON <b>items</b> in <b>containers</b>. The partition key is the scale boundary; pick a high-cardinality field such as <code>/tenantId</code>, not <code>/category</code> with only a few values.",
 "Use the <b>azure-cosmos</b> SDK: <code>CosmosClient</code> \u2192 <code>DatabaseProxy</code> \u2192 <code>ContainerProxy</code>. Point reads use <code>read_item(id, partition_key)</code>; queries use SQL text plus parameters.",
 "A query that includes the partition key and passes <code>partition_key=...</code> is single-partition and cheaper. Omitting the partition key means <b>cross-partition</b> fan-out and requires <code>enable_cross_partition_query=True</code>.",
 "Parameterized queries (<code>@tenantId</code>) are preferred for safety and plan reuse; string concatenation is both insecure and a poor exam answer.",
 "Keys work for labs, but production answers should prefer <b>Microsoft Entra ID + Cosmos DB built-in data roles</b> or managed identity when the question asks for least privilege.",
],
"prereq": "Azure subscription, Azure CLI 2.x and Python 3.10+. Install the SDK with <code>pip install azure-cosmos</code>.",
"portal": [
 "##Create the account",
 "Portal \u2192 <b>Azure Cosmos DB</b> \u2192 <b>+ Create</b> \u2192 API = <b>Azure Cosmos DB for NoSQL</b>.",
 "Resource group <code>rg-ai200-data</code>, account name <code>ai200cosmos&lt;unique&gt;</code>, region <code>East US</code>, capacity mode <b>Provisioned throughput</b>, consistency <b>Session</b>.",
 "##Create database and container",
 "Account \u2192 <b>Data Explorer</b> \u2192 <b>New Container</b>. Database id <code>appdb</code>, container id <code>documents</code>, partition key <code>/tenantId</code>, throughput <code>400</code> RU/s.",
 "Add a few JSON items with fields <code>id</code>, <code>tenantId</code>, <code>category</code>, <code>title</code> and <code>content</code>.",
 "##Query and inspect",
 "Data Explorer \u2192 <b>New SQL Query</b> \u2192 run <code>SELECT * FROM c WHERE c.tenantId = 'contoso' AND c.category = 'policy'</code>.",
 "Open <b>Settings</b> for the query and notice the difference between single-partition and cross-partition execution.",
 "Account \u2192 <b>Keys</b> shows the endpoint and keys for a lab connection string; in production use RBAC/managed identity instead.",
],
"cli": r"""RG=rg-ai200-data
LOC=eastus
COSMOS=ai200cosmos$RANDOM       # lowercase, globally unique
DB=appdb
CONTAINER=documents

az group create -n $RG -l $LOC

# --- NoSQL account with Session consistency (default for many apps) --
az cosmosdb create -g $RG -n $COSMOS --kind GlobalDocumentDB \
  --locations regionName=$LOC failoverPriority=0 isZoneRedundant=False \
  --default-consistency-level Session

# --- Database + partitioned container -------------------------------
az cosmosdb sql database create -g $RG -a $COSMOS -n $DB
az cosmosdb sql container create -g $RG -a $COSMOS -d $DB -n $CONTAINER \
  --partition-key-path "/tenantId" --throughput 400

# --- Values used by the Python SDK ----------------------------------
export COSMOS_ENDPOINT=$(az cosmosdb show -g $RG -n $COSMOS --query documentEndpoint -o tsv)
export COSMOS_KEY=$(az cosmosdb keys list -g $RG -n $COSMOS --type keys --query primaryMasterKey -o tsv)

az cosmosdb sql container show -g $RG -a $COSMOS -d $DB -n $CONTAINER \
  --query '{id:id, partitionKey:resource.partitionKey.paths, throughput:options.throughput}'""",
"code": r"""# pip install azure-cosmos
# This is the SDK shape the exam expects: client -> database -> container.
import os
from azure.cosmos import CosmosClient, PartitionKey

ENDPOINT = os.environ["COSMOS_ENDPOINT"]
KEY = os.environ["COSMOS_KEY"]

client = CosmosClient(ENDPOINT, credential=KEY)
db = client.create_database_if_not_exists(id="appdb")
container = db.create_container_if_not_exists(
    id="documents",
    partition_key=PartitionKey(path="/tenantId"),
    offer_throughput=400,
)

items = [
    {
        "id": "doc-001",
        "tenantId": "contoso",
        "category": "policy",
        "title": "Expense policy",
        "content": "Meals over $50 require manager approval.",
    },
    {
        "id": "doc-002",
        "tenantId": "contoso",
        "category": "faq",
        "title": "Travel FAQ",
        "content": "Use the travel portal before booking flights.",
    },
]
for item in items:
    container.upsert_item(item)

# Cheapest query shape: the SQL predicate and the request both target one PK.
query = '''
SELECT c.id, c.title, c.category
FROM c
WHERE c.tenantId = @tenantId AND c.category = @category
'''
params = [
    {"name": "@tenantId", "value": "contoso"},
    {"name": "@category", "value": "policy"},
]
for row in container.query_items(query=query, parameters=params, partition_key="contoso"):
    print("single partition", row)

# Cross-partition query: valid, but fans out and generally costs more RUs.
for row in container.query_items(
    query="SELECT c.id, c.tenantId, c.title FROM c WHERE c.category = @category",
    parameters=[{"name": "@category", "value": "policy"}],
    enable_cross_partition_query=True,
):
    print("cross partition", row)

# Point reads need both id and partition key; this is not a SQL query.
print(container.read_item(item="doc-001", partition_key="contoso"))""",
"code_label": "Python / SDK",
"traps": [
 "<code>id</code> is unique only within a logical partition unless you design otherwise; the item address is really <code>(id, partition key)</code>.",
 "A SQL query missing the partition key may work in Data Explorer but cost far more RUs in production. Exam wording like 'reduce RU charge' usually points to a better partition key or single-partition query.",
 "The partition key path is immutable after container creation. If you choose the wrong path, you create a new container and migrate data.",
 "Data Explorer queries are not the same as point reads. <code>read_item</code> is faster/cheaper when you know <code>id</code> and partition key.",
],
"cleanup": r"""az group delete -n rg-ai200-data --yes --no-wait""",
},
# ---------------------------------------------------------------- 2.2
{
"id": "2.2",
"title": "Optimize Cosmos DB RU cost with indexing policies and consistency",
"time": "35 min",
"level": "Core",
"objective": "Tune throughput, indexing policy and consistency level, then measure RU charge from SDK response headers.",
"exam": [
 "RUs pay for CPU, IO and memory for every operation. <b>Point reads</b> are cheapest; broad scans, cross-partition queries and over-indexed writes are common RU drains.",
 "Provisioned throughput can be fixed RU/s or <b>autoscale</b> max RU/s. Autoscale is good for bursty traffic; fixed throughput is cheaper for steady traffic you can predict.",
 "Cosmos DB indexes all properties by default. Excluding large or never-filtered paths such as <code>/content/*</code> or vectors lowers write RU; include paths you filter/order by.",
 "Consistency levels from strongest to weakest: <b>Strong</b> \u2192 <b>Bounded Staleness</b> \u2192 <b>Session</b> \u2192 <b>Consistent Prefix</b> \u2192 <b>Eventual</b>. Stronger consistency generally raises read latency and RU cost, especially across regions.",
 "The SDK exposes request charge in <code>x-ms-request-charge</code>; measuring it is the concrete way to prove an optimization.",
],
"prereq": "Lab 2.1 account/container and <code>pip install azure-cosmos</code>. Use non-production data before replacing an indexing policy.",
"portal": [
 "##Review throughput",
 "Cosmos account \u2192 <b>Data Explorer</b> \u2192 database/container \u2192 <b>Scale &amp; Settings</b>. Compare manual <code>400</code> RU/s with autoscale <code>4000</code> max RU/s.",
 "##Edit indexing policy",
 "In <b>Scale &amp; Settings</b>, open <b>Indexing Policy</b>. Keep <code>indexingMode</code> = <code>consistent</code> and <code>automatic</code> = <code>true</code>.",
 "Include paths used by predicates/sorts such as <code>/tenantId/?</code>, <code>/category/?</code> and <code>/createdAt/?</code>; exclude bulky fields such as <code>/content/*</code> if you never query them directly.",
 "Save the policy and wait for index transformation progress to complete before comparing latency/RU.",
 "##Change consistency deliberately",
 "Account \u2192 <b>Default consistency</b> \u2192 compare <b>Session</b>, <b>Consistent Prefix</b> and <b>Eventual</b>. Do not choose <b>Strong</b> unless the scenario requires linearizable reads.",
 "##Measure",
 "Run the SDK code tab before/after the indexing policy change and record <code>x-ms-request-charge</code> for point reads, single-partition queries and cross-partition queries.",
],
"cli": r"""RG=rg-ai200-data
COSMOS=<your-cosmos-account>
DB=appdb
CONTAINER=documents

# --- Autoscale for bursty workloads; fixed RU/s for steady workloads -
az cosmosdb sql container throughput migrate -g $RG -a $COSMOS -d $DB -n $CONTAINER \
  --throughput-type autoscale
az cosmosdb sql container throughput update -g $RG -a $COSMOS -d $DB -n $CONTAINER \
  --max-throughput 4000

# --- indexing-policy.json -------------------------------------------
cat > indexing-policy.json <<'JSON'
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    { "path": "/tenantId/?" },
    { "path": "/category/?" },
    { "path": "/createdAt/?" },
    { "path": "/metadata/*" }
  ],
  "excludedPaths": [
    { "path": "/\"_etag\"/?" },
    { "path": "/content/*" },
    { "path": "/embedding/*" }
  ]
}
JSON

az cosmosdb sql container update -g $RG -a $COSMOS -d $DB -n $CONTAINER \
  --idx @indexing-policy.json

# --- Account-level consistency trade-off ----------------------------
az cosmosdb update -g $RG -n $COSMOS --default-consistency-level Session
# Bounded staleness requires both values:
az cosmosdb update -g $RG -n $COSMOS --default-consistency-level BoundedStaleness \
  --max-interval 10 --max-staleness-prefix 100
# Lower latency / weaker read guarantee example:
az cosmosdb update -g $RG -n $COSMOS --default-consistency-level Eventual""",
"code": r"""# pip install azure-cosmos
# Measure RU charge instead of guessing. The response hook exposes headers.
import os
from azure.cosmos import CosmosClient, PartitionKey

client = CosmosClient(os.environ["COSMOS_ENDPOINT"], credential=os.environ["COSMOS_KEY"])
db = client.get_database_client("appdb")
container = db.get_container_client("documents")

def charge(label):
    def hook(headers, _body):
        print(f"{label}: {headers.get('x-ms-request-charge')} RU")
        metrics = headers.get("x-ms-documentdb-query-metrics")
        if metrics:
            print(f"{label} metrics: {metrics[:180]}...")
    return hook

# Point read: the baseline cheapest read when id + partition key are known.
container.read_item(
    item="doc-001",
    partition_key="contoso",
    response_hook=charge("point read"),
)

# Single-partition query: pass partition_key as a request option.
list(container.query_items(
    query="SELECT c.id, c.title FROM c WHERE c.tenantId = @tenantId AND c.category = @category",
    parameters=[
        {"name": "@tenantId", "value": "contoso"},
        {"name": "@category", "value": "policy"},
    ],
    partition_key="contoso",
    populate_query_metrics=True,
    response_hook=charge("single partition query"),
))

# Cross-partition fan-out: valid, but compare the RU charge.
list(container.query_items(
    query="SELECT c.id, c.tenantId FROM c WHERE c.category = @category",
    parameters=[{"name": "@category", "value": "policy"}],
    enable_cross_partition_query=True,
    populate_query_metrics=True,
    response_hook=charge("cross partition query"),
))

# Apply an indexing policy from code when infrastructure-as-code is not used.
# Excluding large fields reduces write RU only if queries do not need those paths.
indexing_policy = {
    "indexingMode": "consistent",
    "automatic": True,
    "includedPaths": [
        {"path": "/tenantId/?"},
        {"path": "/category/?"},
        {"path": "/createdAt/?"},
        {"path": "/metadata/*"},
    ],
    "excludedPaths": [
        {"path": "/\"_etag\"/?"},
        {"path": "/content/*"},
        {"path": "/embedding/*"},
    ],
}
# db.replace_container(container, partition_key=PartitionKey(path="/tenantId"), indexing_policy=indexing_policy)
print("Indexing policy ready; uncomment replace_container only after testing on a dev container.")""",
"code_label": "Python / SDK",
"traps": [
 "Excluding a path from indexing can make filters/sorts on that path fail or scan. Do not exclude fields used by <code>WHERE</code>, <code>ORDER BY</code> or vector search.",
 "Autoscale max RU/s is not the same as current RU/s; billing and minimums are tied to the max. It is not magically free when idle.",
 "Strong consistency across multiple write regions is not available, and Strong/Bounded Staleness can cost about twice the read RUs compared with weaker consistency in multi-region accounts.",
 "Changing consistency at the account default does not fix a bad query shape. Partition key targeting usually saves more RUs than weakening consistency.",
],
"cleanup": r"""# Revert to the inexpensive lab default if you keep the account.
az cosmosdb update -g rg-ai200-data -n <your-cosmos-account> --default-consistency-level Session
az cosmosdb sql container throughput migrate -g rg-ai200-data -a <your-cosmos-account> \
  -d appdb -n documents --throughput-type manual
az cosmosdb sql container throughput update -g rg-ai200-data -a <your-cosmos-account> \
  -d appdb -n documents --throughput 400""",
},
# ---------------------------------------------------------------- 2.3
{
"id": "2.3",
"title": "Vector similarity search in Cosmos DB for NoSQL",
"time": "40 min",
"level": "Advanced",
"objective": "Create a vector-enabled Cosmos DB container, store embeddings, and retrieve semantically similar items with VectorDistance().",
"exam": [
 "Cosmos DB for NoSQL vector search needs two container-level settings: a <b>vector embedding policy</b> describing path/dimensions/data type/distance function and a <b>vector index</b> in the indexing policy.",
 "Common vector index types are <code>flat</code>, <code>quantizedFlat</code> and <code>diskANN</code>. <code>flat</code> is exact but expensive at scale; <code>quantizedFlat</code>/<code>diskANN</code> trade small recall loss for lower latency/RU.",
 "Store embeddings as numeric arrays on the configured path, e.g. <code>/embedding</code>. The query vector must have the <b>same dimensions</b> and compatible distance function.",
 "Semantic retrieval uses <code>VectorDistance(c.embedding, @queryVector)</code>, usually with <code>TOP N</code>, metadata filters and <code>ORDER BY</code> distance.",
 "Vector search is still Cosmos DB: partition keys, indexing policy and RU throughput determine latency/cost. Filtering by tenant before ranking avoids noisy cross-tenant retrieval.",
],
"prereq": "A Cosmos DB for NoSQL account with vector search capability enabled, plus embeddings from Azure OpenAI or another model. SDK: <code>pip install azure-cosmos</code>.",
"portal": [
 "##Enable vector search",
 "When creating the account, enable the <b>Vector Search for NoSQL API</b> capability if shown. Existing accounts may require enabling the capability before creating vector containers.",
 "##Create the vector container",
 "Data Explorer \u2192 <b>New Container</b>: database <code>appdb</code>, container <code>kb_vectors</code>, partition key <code>/tenantId</code>.",
 "Open the container's JSON policy editor (or use CLI) and define a vector embedding policy for <code>/embedding</code>: data type <code>float32</code>, dimensions matching the embedding model, distance <code>cosine</code>.",
 "Add a vector index on <code>/embedding</code>; choose <code>diskANN</code> for larger corpora or <code>quantizedFlat</code> for a simpler approximate index.",
 "##Load and query",
 "Insert items containing <code>id</code>, <code>tenantId</code>, <code>content</code>, <code>source</code>, metadata and <code>embedding</code>.",
 "Run a SQL query using <code>ORDER BY VectorDistance(c.embedding, @queryVector)</code> and confirm the top results are semantically related, not just keyword matches.",
],
"cli": r"""RG=rg-ai200-data
LOC=eastus
COSMOS=ai200vec$RANDOM
DB=appdb
CONTAINER=kb_vectors

az group create -n $RG -l $LOC

# Vector search must be enabled at the account level before vector containers.
az cosmosdb create -g $RG -n $COSMOS --kind GlobalDocumentDB \
  --locations regionName=$LOC failoverPriority=0 isZoneRedundant=False \
  --capabilities EnableNoSQLVectorSearch \
  --default-consistency-level Session

az cosmosdb sql database create -g $RG -a $COSMOS -n $DB

cat > vector-embedding-policy.json <<'JSON'
{
  "vectorEmbeddings": [
    {
      "path": "/embedding",
      "dataType": "float32",
      "dimensions": 1536,
      "distanceFunction": "cosine"
    }
  ]
}
JSON

cat > vector-indexing-policy.json <<'JSON'
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    { "path": "/*" }
  ],
  "excludedPaths": [
    { "path": "/\"_etag\"/?" }
  ],
  "vectorIndexes": [
    { "path": "/embedding", "type": "diskANN" }
  ]
}
JSON

az cosmosdb sql container create -g $RG -a $COSMOS -d $DB -n $CONTAINER \
  --partition-key-path "/tenantId" --throughput 1000 \
  --vector-embeddings @vector-embedding-policy.json \
  --idx @vector-indexing-policy.json

export COSMOS_ENDPOINT=$(az cosmosdb show -g $RG -n $COSMOS --query documentEndpoint -o tsv)
export COSMOS_KEY=$(az cosmosdb keys list -g $RG -n $COSMOS --type keys --query primaryMasterKey -o tsv)""",
"code": r"""# pip install azure-cosmos
# Embeddings normally come from Azure OpenAI; short vectors below keep the lab readable.
# Change dimensions to 1536/3072/etc. to match your embedding model.
import os
from azure.cosmos import CosmosClient, PartitionKey

DIMENSIONS = 4
client = CosmosClient(os.environ["COSMOS_ENDPOINT"], credential=os.environ["COSMOS_KEY"])
db = client.create_database_if_not_exists("appdb")

vector_embedding_policy = {
    "vectorEmbeddings": [
        {
            "path": "/embedding",
            "dataType": "float32",
            "dimensions": DIMENSIONS,
            "distanceFunction": "cosine",
        }
    ]
}
indexing_policy = {
    "indexingMode": "consistent",
    "automatic": True,
    "includedPaths": [{"path": "/*"}],
    "excludedPaths": [{"path": "/\"_etag\"/?"}],
    "vectorIndexes": [{"path": "/embedding", "type": "quantizedFlat"}],
}

container = db.create_container_if_not_exists(
    id="kb_vectors_dev",
    partition_key=PartitionKey(path="/tenantId"),
    offer_throughput=1000,
    vector_embedding_policy=vector_embedding_policy,
    indexing_policy=indexing_policy,
)

docs = [
    ("hr-1", "contoso", "Benefits", "Employees can enroll in health benefits after 30 days.", [0.12, 0.03, 0.91, 0.22]),
    ("hr-2", "contoso", "Expenses", "Meals over $50 require manager approval.", [0.10, 0.82, 0.09, 0.18]),
    ("it-1", "contoso", "VPN", "Reset your MFA device before using VPN overseas.", [0.88, 0.10, 0.08, 0.03]),
]
for doc_id, tenant, title, content, embedding in docs:
    container.upsert_item({
        "id": doc_id,
        "tenantId": tenant,
        "title": title,
        "content": content,
        "source": "handbook.pdf",
        "metadata": {"department": title.lower()},
        "embedding": embedding,
    })

query_vector = [0.11, 0.78, 0.11, 0.20]  # roughly similar to the expenses document
query = '''
SELECT TOP 3
    c.id, c.title, c.content,
    VectorDistance(c.embedding, @queryVector) AS distance
FROM c
WHERE c.tenantId = @tenantId
ORDER BY VectorDistance(c.embedding, @queryVector)
'''
params = [
    {"name": "@tenantId", "value": "contoso"},
    {"name": "@queryVector", "value": query_vector},
]

for row in container.query_items(
    query=query,
    parameters=params,
    partition_key="contoso",
    populate_query_metrics=True,
):
    print(row)""",
"code_label": "Python / SDK",
"traps": [
 "Vector policy and vector index are container design decisions; do not assume you can turn a normal container into a vector-optimized one after loading production data.",
 "Dimensions must match exactly. A 1536-dimension query vector cannot search a 3072-dimension embedding path.",
 "Do not exclude the vector path without adding a <code>vectorIndexes</code> entry; normal range indexes are not vector indexes.",
 "Vector search returns nearest vectors, not grounded answers. RAG still needs metadata filtering, prompt grounding and citations from the retrieved documents.",
],
"cleanup": r"""az group delete -n rg-ai200-data --yes --no-wait""",
},
# ---------------------------------------------------------------- 2.4
{
"id": "2.4",
"title": "Process new and updated items with the Cosmos DB change feed",
"time": "40 min",
"level": "Advanced",
"objective": "Use the Cosmos DB change feed to react to inserts and updates, with leases/checkpoints for reliable processing.",
"exam": [
 "The change feed is an ordered feed of item changes within a logical partition. It is used to trigger downstream AI work such as embedding generation, enrichment and cache invalidation.",
 "Default/latest-version mode shows creates and updates; <b>all versions and deletes</b> mode is required when the scenario explicitly needs deletes or intermediate versions.",
 "A <b>change feed processor</b> uses a lease container to coordinate workers and checkpoint progress. Without leases/checkpoints, multiple workers can duplicate work or miss restart position.",
 "Azure Functions <b>Cosmos DB trigger</b> is the managed change feed processor option: the platform owns polling, leases, scaling and retry behavior.",
 "The pull model (<code>query_items_change_feed</code>) is useful when you want manual control over partition/feed ranges and checkpoint storage.",
],
"prereq": "Lab 2.1 Cosmos account. For the Functions option, Azure Functions v4 Python and a storage account for the function app.",
"portal": [
 "##Create the lease container",
 "Cosmos account \u2192 Data Explorer \u2192 <b>New Container</b>. Database <code>appdb</code>, container <code>leases</code>, partition key <code>/id</code>. Keep it small; it stores checkpoints, not business data.",
 "##Choose a processing model",
 "For managed serverless processing, create an <b>Azure Function</b> with a <b>Cosmos DB trigger</b> bound to <code>appdb/documents</code> and lease container <code>leases</code>.",
 "For custom worker control, use the Python SDK pull model and persist continuation tokens/feed-range checkpoints yourself.",
 "##Generate changes",
 "Insert a new item and then update the same item in <code>documents</code>. The processor should see both as changes in latest-version mode, with the current item body.",
 "##Operate",
 "Monitor Function logs or worker logs. If processing calls an embedding model, make the handler idempotent because retries can re-deliver a batch after failures.",
],
"cli": r"""RG=rg-ai200-data
LOC=eastus
COSMOS=<your-cosmos-account>
DB=appdb
SOURCE=documents
LEASES=leases
FUNC=ai200-cf-$RANDOM
STG=ai200cf$RANDOM

# --- Lease container used by Functions / change feed processors ------
az cosmosdb sql container create -g $RG -a $COSMOS -d $DB -n $LEASES \
  --partition-key-path "/id" --throughput 400

# --- Connection string for local settings or Function app settings ----
COSMOS_CONN=$(az cosmosdb keys list -g $RG -n $COSMOS --type connection-strings \
  --query "connectionStrings[0].connectionString" -o tsv)

# Managed Azure Functions option (deploy code from the code tab separately).
az storage account create -g $RG -n $STG -l $LOC --sku Standard_LRS
az functionapp create -g $RG -n $FUNC --storage-account $STG \
  --consumption-plan-location $LOC --runtime python --runtime-version 3.11 \
  --functions-version 4
az functionapp config appsettings set -g $RG -n $FUNC --settings \
  CosmosConnection="$COSMOS_CONN" CosmosDatabase=$DB CosmosContainer=$SOURCE CosmosLeaseContainer=$LEASES

# Generate an insert/update for the feed by running the SDK code or Data Explorer.
# For local Functions Core Tools:
# func azure functionapp publish $FUNC""",
"code": r"""# Option A: Azure Functions v2 programming model - managed change feed processor.
# function_app.py
import json
import logging
import azure.functions as func

app = func.FunctionApp()

@app.cosmos_db_trigger(
    arg_name="documents",
    database_name="%CosmosDatabase%",
    container_name="%CosmosContainer%",
    connection="CosmosConnection",
    lease_container_name="%CosmosLeaseContainer%",
    create_lease_container_if_not_exists=False,
)
def on_documents_changed(documents: func.DocumentList) -> None:
    for document in documents:
        item = json.loads(document.to_json())
        logging.info("changed id=%s tenant=%s", item["id"], item.get("tenantId"))
        # Exam-relevant pattern: idempotently enqueue embedding/enrichment work here.
        # Store a processed version or use the item's _etag to avoid duplicate side effects.


# Option B: SDK pull model - you own checkpoint persistence.
# pip install azure-cosmos
import os
from azure.cosmos import CosmosClient

client = CosmosClient(os.environ["COSMOS_ENDPOINT"], credential=os.environ["COSMOS_KEY"])
container = client.get_database_client("appdb").get_container_client("documents")

# Pull changes for one logical partition. Use read_feed_ranges() to parallelize workers.
changes = container.query_items_change_feed(
    partition_key="contoso",
    start_time="Beginning",
    mode="LatestVersion",
    max_item_count=100,
)
for item in changes:
    print("changed", item["id"], item.get("_ts"), item.get("_etag"))

# Production pull workers persist continuation tokens/feed-range checkpoints externally.
# Azure Functions does this for you with the lease container.""",
"code_label": "Python / SDK",
"traps": [
 "Change feed is not a full audit log in latest-version mode; deletes and every intermediate version require <b>AllVersionsAndDeletes</b> and the account/features that support it.",
 "Lease container partition key should be <code>/id</code>. Do not reuse the monitored container as the lease container.",
 "The trigger can deliver batches more than once after retries. Make embedding generation, outbound messages and writes idempotent.",
 "Change feed order is guaranteed within a logical partition key, not globally across every partition in a large container.",
],
"cleanup": r"""az functionapp delete -g rg-ai200-data -n <function-app-name>
az storage account delete -g rg-ai200-data -n <storage-account-name> --yes
az cosmosdb sql container delete -g rg-ai200-data -a <your-cosmos-account> -d appdb -n leases --yes""",
},
# ---------------------------------------------------------------- 2.5
{
"id": "2.5",
"title": "Connect to Azure Database for PostgreSQL and model schema/indexing",
"time": "35 min",
"level": "Core",
"objective": "Provision Azure Database for PostgreSQL Flexible Server, connect with psycopg, and create relational/JSON/text indexes for low-latency queries.",
"exam": [
 "AI-200 names <b>Azure Database for PostgreSQL Flexible Server</b>, not Single Server. Flexible Server is the current managed PostgreSQL target for new workloads.",
 "Use the right data types: <code>uuid</code> for ids, <code>timestamptz</code> for time, <code>jsonb</code> for metadata, <code>text</code> for chunks and generated <code>tsvector</code> for full-text search.",
 "Index to match access patterns: <b>B-tree</b> for equality/range/sort, <b>GIN</b> for <code>jsonb</code> containment and full-text search. Every extra index speeds reads but slows writes and consumes storage.",
 "Measure with <code>EXPLAIN (ANALYZE, BUFFERS)</code>; do not assume an index is used. Stale statistics or a nonselective predicate can still choose a sequential scan.",
 "Connection strings require TLS (<code>sslmode=require</code>). For production, prefer Microsoft Entra authentication/managed identity when supported instead of embedded passwords.",
],
"prereq": "Azure CLI, <code>psql</code> or Cloud Shell, and Python package <code>psycopg[binary]</code> for the SDK sample.",
"portal": [
 "##Create Flexible Server",
 "Portal \u2192 <b>Azure Database for PostgreSQL flexible servers</b> \u2192 <b>+ Create</b>. Workload <b>Development</b> or <b>Production</b> as appropriate, PostgreSQL 16, region <code>East US</code>.",
 "Choose compute tier based on workload; for a schema/indexing lab a small General Purpose server is enough. Enable storage autogrow for production-like tests.",
 "Networking: use private access for production; for a lab, public access plus your client IP firewall rule is simplest.",
 "##Create the app database",
 "Open the server \u2192 <b>Databases</b> \u2192 <b>+ Add</b> database <code>aiapp</code>.",
 "##Connect and build schema",
 "Server \u2192 <b>Connect</b> shows the <code>psql</code> command with host <code>&lt;server&gt;.postgres.database.azure.com</code> and port <code>5432</code>.",
 "Run the SQL tab to create tables and indexes, then run the Python snippet to insert/query sample chunks.",
 "Use <b>Query Performance Insight</b> / <b>Performance recommendations</b> after load to identify slow queries and missing indexes.",
],
"cli": r"""RG=rg-ai200-data
LOC=eastus
PG=ai200pg$RANDOM
DB=aiapp
ADMIN=pgadmin
PASSWORD='Use-a-long-random-password-123!'

az group create -n $RG -l $LOC

# Flexible Server is the current Azure PostgreSQL deployment model.
az postgres flexible-server create -g $RG -n $PG -l $LOC \
  --version 16 --tier GeneralPurpose --sku-name Standard_D2ds_v5 \
  --storage-size 128 --storage-auto-grow Enabled \
  --admin-user $ADMIN --admin-password $PASSWORD \
  --public-access 0.0.0.0

az postgres flexible-server db create -g $RG -s $PG -d $DB

# Narrow this to your real public IP for labs outside Cloud Shell.
az postgres flexible-server firewall-rule create -g $RG -n allow-client -s $PG \
  --start-ip-address <your-ip> --end-ip-address <your-ip>

export PGHOST=$PG.postgres.database.azure.com
export PGDATABASE=$DB
export PGUSER=$ADMIN
export PGPASSWORD=$PASSWORD
export PGSSLMODE=require

psql "host=$PGHOST port=5432 dbname=$PGDATABASE user=$PGUSER password=$PGPASSWORD sslmode=require" \
  -f schema.sql""",
"code": r"""-- schema.sql - relational + JSONB + full-text indexes for AI document chunks.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS documents (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   text NOT NULL,
    source_uri  text NOT NULL,
    title       text NOT NULL,
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id   text NOT NULL,
    chunk_no    integer NOT NULL CHECK (chunk_no >= 0),
    content     text NOT NULL,
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
    search_text tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(content, ''))
    ) STORED,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_no)
);

-- B-tree: equality/range/sort predicates used by app queries.
CREATE INDEX IF NOT EXISTS ix_documents_tenant_created
    ON documents (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_chunks_tenant_document
    ON chunks (tenant_id, document_id, chunk_no);

-- GIN: JSONB containment and full-text search.
CREATE INDEX IF NOT EXISTS ix_documents_metadata_gin
    ON documents USING gin (metadata jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_chunks_search_gin
    ON chunks USING gin (search_text);

INSERT INTO documents (tenant_id, source_uri, title, metadata)
VALUES ('contoso', 'https://storage/handbook.pdf', 'Employee handbook', '{"department":"hr"}')
RETURNING id;

-- After inserting chunks, prove the plan and latency with BUFFERS.
EXPLAIN (ANALYZE, BUFFERS)
SELECT c.id, c.chunk_no, ts_rank(c.search_text, plainto_tsquery('english', 'meal approval')) AS rank
FROM chunks c
WHERE c.tenant_id = 'contoso'
  AND c.search_text @@ plainto_tsquery('english', 'meal approval')
ORDER BY rank DESC
LIMIT 5;

-- psycopg v3 connection shape used by applications:
-- import psycopg, os
-- conn = psycopg.connect(host=os.environ['PGHOST'], dbname=os.environ['PGDATABASE'],
--                        user=os.environ['PGUSER'], password=os.environ['PGPASSWORD'],
--                        sslmode='require')""",
"code_label": "SQL",
"traps": [
 "Do not model everything as <code>text</code> or <code>jsonb</code>. Relational columns with B-tree indexes are faster for common filters such as tenant, source and created date.",
 "A GIN index on <code>jsonb</code> helps containment (<code>@&gt;</code>), not arbitrary string searches inside JSON. Use the right operator for the index.",
 "Firewall/networking failures look like authentication problems. Check public access/private endpoint and firewall rules before rotating passwords.",
 "Indexing every column is not optimisation. It increases write latency and storage, which matters when ingestion pipelines chunk large document sets.",
],
"cleanup": r"""az postgres flexible-server delete -g rg-ai200-data -n <postgres-server-name> --yes
# or delete the whole lab group if it contains only lab resources:
az group delete -n rg-ai200-data --yes --no-wait""",
},
# ---------------------------------------------------------------- 2.6
{
"id": "2.6",
"title": "pgvector similarity search and RAG on PostgreSQL",
"time": "45 min",
"level": "Advanced",
"objective": "Enable pgvector on Azure Database for PostgreSQL, store embeddings, index them, and run metadata-filtered semantic retrieval for RAG.",
"exam": [
 "On Azure Database for PostgreSQL Flexible Server, allow-list extensions with server parameter <code>azure.extensions</code> before running <code>CREATE EXTENSION vector</code> in the database.",
 "pgvector stores embeddings in <code>vector(n)</code>. Operators matter: <code>&lt;-&gt;</code> = L2 distance, <code>&lt;#&gt;</code> = negative inner product, <code>&lt;=&gt;</code> = cosine distance.",
 "Use <b>HNSW</b> for strong recall/latency without a training step; use <b>IVFFlat</b> when you can tune lists/probes after loading representative data. Both reduce compute versus exact scans.",
 "RAG retrieval should combine vector order with metadata filters in <code>WHERE</code> (tenant/security/category/date). Never retrieve across tenants and filter only in application code.",
 "Vector workloads are memory/CPU heavy. Size Flexible Server compute, memory, storage IOPS and connection pooling (<b>PgBouncer</b>) for concurrency, not just database size.",
],
"prereq": "Lab 2.5 Flexible Server. Embeddings from Azure OpenAI or another model. Server restart may be required after changing extension or PgBouncer parameters.",
"portal": [
 "##Allow-list pgvector",
 "Flexible Server \u2192 <b>Server parameters</b> \u2192 search <code>azure.extensions</code> \u2192 add <code>vector</code> to the comma-separated list \u2192 Save and restart if prompted.",
 "##Enable extension in the database",
 "Connect to database <code>aiapp</code> with <code>psql</code> and run <code>CREATE EXTENSION IF NOT EXISTS vector;</code>.",
 "##Create vector schema and indexes",
 "Run the SQL tab: create a <code>vector(1536)</code> column, B-tree metadata index and HNSW/IVFFlat vector index matching the distance operator you will query.",
 "##Tune workload resources",
 "Server \u2192 <b>Compute + storage</b>: scale vCores/memory for vector index build and query concurrency; increase storage performance/IOPS for large corpora.",
 "Server parameters \u2192 enable <code>pgbouncer.enabled</code> for connection pooling when many app instances call the database.",
 "##Retrieve for RAG",
 "Use the top K chunks from the metadata-filtered vector query as grounded context for the LLM prompt; include source fields for citations.",
],
"cli": r"""RG=rg-ai200-data
PG=<your-postgres-server>
DB=aiapp
ADMIN=pgadmin

# Azure PostgreSQL blocks extensions unless they are allow-listed first.
az postgres flexible-server parameter set -g $RG -s $PG \
  -n azure.extensions -v vector
az postgres flexible-server restart -g $RG -n $PG

# Optional: built-in PgBouncer for high connection counts from app replicas.
az postgres flexible-server parameter set -g $RG -s $PG \
  -n pgbouncer.enabled -v true
az postgres flexible-server restart -g $RG -n $PG

# Scale up for vector index builds / concurrent retrieval, then scale down if needed.
az postgres flexible-server update -g $RG -n $PG \
  --tier GeneralPurpose --sku-name Standard_D4ds_v5 \
  --storage-size 256 --storage-auto-grow Enabled

psql "host=$PG.postgres.database.azure.com port=5432 dbname=$DB user=$ADMIN password=$PGPASSWORD sslmode=require" \
  -f pgvector-rag.sql""",
"code": r"""-- pgvector-rag.sql - semantic retrieval with tenant/metadata filters.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_chunks (
    id          bigserial PRIMARY KEY,
    tenant_id   text NOT NULL,
    source_uri  text NOT NULL,
    title       text NOT NULL,
    content     text NOT NULL,
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
    embedding   vector(1536) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Ordinary filters still need ordinary indexes.
CREATE INDEX IF NOT EXISTS ix_rag_chunks_tenant_source
    ON rag_chunks (tenant_id, source_uri);
CREATE INDEX IF NOT EXISTS ix_rag_chunks_metadata_gin
    ON rag_chunks USING gin (metadata jsonb_path_ops);

-- HNSW: good default for low-latency RAG. Match opclass to query operator.
CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding_hnsw
    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Alternative after bulk loading: IVFFlat needs ANALYZE and probe tuning.
-- CREATE INDEX ix_rag_chunks_embedding_ivfflat
--     ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- ANALYZE rag_chunks;
-- SET ivfflat.probes = 10;

-- For HNSW recall/latency trade-off at query time:
SET hnsw.ef_search = 80;

-- Replace the zero vector with the embedding of the user's question.
WITH q AS (
    SELECT ('[' || array_to_string(array_fill(0.0::float8, ARRAY[1536]), ',') || ']')::vector AS embedding
)
SELECT
    c.id,
    c.title,
    c.source_uri,
    left(c.content, 300) AS context,
    1 - (c.embedding <=> q.embedding) AS cosine_similarity
FROM rag_chunks c, q
WHERE c.tenant_id = 'contoso'
  AND c.metadata @> '{"department":"hr"}'::jsonb
ORDER BY c.embedding <=> q.embedding
LIMIT 5;

-- RAG pattern in the app: embed question -> run this SQL -> pass context+sources to the model.
-- Use a pool (Azure PgBouncer or psycopg_pool) so many app replicas do not exhaust max_connections.""",
"code_label": "SQL",
"traps": [
 "<code>CREATE EXTENSION vector</code> fails until <code>azure.extensions</code> includes <code>vector</code>. The allow-list is an Azure Flexible Server step, not a SQL syntax issue.",
 "The operator and index opclass must match: cosine queries use <code>&lt;=&gt;</code> with <code>vector_cosine_ops</code>; L2 uses <code>&lt;-&gt;</code> with <code>vector_l2_ops</code>.",
 "IVFFlat indexes should be built after loading representative data; building too early or skipping <code>ANALYZE</code> hurts recall/performance.",
 "Connection pooling improves concurrency but does not reduce vector math cost. If CPU/memory are saturated, scale compute or reduce K/dimensions/candidate set.",
],
"cleanup": r"""# Optional cleanup inside the database:
psql "host=<server>.postgres.database.azure.com port=5432 dbname=aiapp user=pgadmin password=$PGPASSWORD sslmode=require" \
  -c "DROP TABLE IF EXISTS rag_chunks;"

# Optional server scale-down after index build:
az postgres flexible-server update -g rg-ai200-data -n <postgres-server-name> \
  --tier GeneralPurpose --sku-name Standard_D2ds_v5 --storage-size 128""",
},
# ---------------------------------------------------------------- 2.7
{
"id": "2.7",
"title": "Caching and vector search with Azure Managed Redis",
"time": "35 min",
"level": "Core",
"objective": "Use Azure Managed Redis for cache-aside operations with expiration/invalidation and RediSearch vector similarity queries.",
"exam": [
 "Azure Managed Redis is managed Redis Enterprise on Azure. For AI apps, use it for low-latency cache-aside reads, session/state, semantic cache entries and RediSearch vector indexes.",
 "Basic operations: <code>SET</code>/<code>GET</code>, <code>SETEX</code> or <code>EXPIRE</code> for TTL, <code>TTL</code> to inspect expiry, and <code>DEL</code> for invalidation after source-of-truth updates.",
 "Cache-aside pattern: app checks Redis \u2192 on miss reads Cosmos/PostgreSQL/model output \u2192 stores value with TTL. Redis is not the system of record unless the scenario says so.",
 "RediSearch vector search requires the <b>RediSearch module</b>, <b>Enterprise</b> clustering policy and <b>NoEviction</b> policy; modules and clustering policy are chosen at creation time.",
 "KNN queries use <code>FT.CREATE</code> with a <code>VECTOR</code> field and <code>FT.SEARCH ... [KNN k @embedding $vec AS score]</code>. Store vectors as binary <code>FLOAT32</code> blobs when using HASH fields.",
],
"prereq": "Azure Managed Redis with RediSearch enabled, Python 3.10+, <code>pip install redis numpy</code>. Access keys are shown for labs; prefer Entra ID/managed identity where supported.",
"portal": [
 "##Create Managed Redis",
 "Portal \u2192 <b>Azure Managed Redis</b> \u2192 <b>Create</b>. Resource group <code>rg-ai200-data</code>, name <code>ai200redis&lt;unique&gt;</code>, region with service availability.",
 "Basics: choose an in-memory tier such as <b>Balanced</b> for a lab. Networking: public for lab or private endpoint for production.",
 "Advanced: enable <b>RediSearch</b>, select <b>Enterprise</b> clustering policy and keep eviction policy <b>NoEviction</b> for RediSearch.",
 "##Connect",
 "Open the cache \u2192 <b>Authentication</b>. Prefer Microsoft Entra ID; for a lab, enable/access keys if your client sample uses password auth.",
 "Copy host name, TLS port and primary key. Managed Redis host names look like <code>&lt;name&gt;.&lt;region&gt;.redis.azure.net</code>.",
 "##Operate cache + vector index",
 "Run the Python tab. Confirm <code>SETEX</code> creates a TTL, <code>DEL</code> invalidates a key, and <code>FT.SEARCH</code> returns nearest vector documents.",
],
"cli": r"""RG=rg-ai200-data
LOC=eastus
REDIS=ai200redis$RANDOM

az group create -n $RG -l $LOC
az extension add -n redisenterprise --upgrade

# Azure Managed Redis uses Redis Enterprise capabilities; RediSearch is enabled at creation.
# Exact SKU names vary by region/tier. Use a small Enterprise-compatible in-memory SKU for labs.
az redisenterprise create -g $RG -n $REDIS -l $LOC \
  --sku Enterprise_E10 --capacity 2

# Create the default database with RediSearch. RediSearch requires Enterprise clustering policy.
az redisenterprise database create -g $RG --cluster-name $REDIS -n default \
  --client-protocol Encrypted --port 10000 \
  --clustering-policy EnterpriseCluster \
  --module name=RediSearch

export REDIS_HOST=$(az redisenterprise show -g $RG -n $REDIS --query hostName -o tsv)
export REDIS_PORT=10000
export REDIS_KEY=$(az redisenterprise database list-keys -g $RG --cluster-name $REDIS -n default \
  --query primaryKey -o tsv)

# Quick connectivity check if redis-cli is available:
redis-cli -h $REDIS_HOST -p $REDIS_PORT --tls -a "$REDIS_KEY" PING""",
"code": r"""# pip install redis numpy
# Cache-aside + invalidation + RediSearch vector query using redis-py.
import json
import os
import time
import numpy as np
import redis

r = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ.get("REDIS_PORT", "10000")),
    password=os.environ["REDIS_KEY"],
    ssl=True,
    decode_responses=False,  # vectors are binary FLOAT32 payloads
)

# --- Cache-aside primitives -----------------------------------------
def load_profile_from_database(user_id: str) -> dict:
    # Source of truth is Cosmos DB/PostgreSQL/etc.; Redis is the cache.
    return {"id": user_id, "displayName": "Adele Vance", "updated": int(time.time())}

def get_profile(user_id: str) -> dict:
    key = f"profile:{user_id}"
    cached = r.get(key)
    if cached:
        return json.loads(cached)

    profile = load_profile_from_database(user_id)
    r.setex(key, 300, json.dumps(profile))  # TTL avoids stale data living forever
    return profile

def invalidate_profile(user_id: str) -> None:
    r.delete(f"profile:{user_id}")          # call after source-of-truth update

print(get_profile("adele"))
print("ttl", r.ttl("profile:adele"))
invalidate_profile("adele")

# --- RediSearch vector index ----------------------------------------
# HASH schema: tenant tag + title/content text + embedding vector.
try:
    r.execute_command("FT.DROPINDEX", "idx:docs")
except redis.ResponseError:
    pass

r.execute_command(
    "FT.CREATE", "idx:docs",
    "ON", "HASH",
    "PREFIX", "1", "doc:",
    "SCHEMA",
    "tenant", "TAG",
    "title", "TEXT",
    "content", "TEXT",
    "embedding", "VECTOR", "HNSW", "6",
        "TYPE", "FLOAT32", "DIM", "4", "DISTANCE_METRIC", "COSINE",
)

def f32(values):
    return np.array(values, dtype=np.float32).tobytes()

r.hset("doc:1", mapping={
    "tenant": "contoso",
    "title": "Expense policy",
    "content": "Meals over $50 require manager approval.",
    "embedding": f32([0.10, 0.82, 0.09, 0.18]),
})
r.hset("doc:2", mapping={
    "tenant": "contoso",
    "title": "VPN help",
    "content": "Reset MFA before VPN travel.",
    "embedding": f32([0.88, 0.10, 0.08, 0.03]),
})

query_vec = f32([0.11, 0.78, 0.11, 0.20])
results = r.execute_command(
    "FT.SEARCH", "idx:docs",
    "(@tenant:{contoso})=>[KNN 2 @embedding $vec AS score]",
    "PARAMS", "2", "vec", query_vec,
    "SORTBY", "score",
    "RETURN", "4", "title", "content", "tenant", "score",
    "DIALECT", "2",
)
print(results)""",
"code_label": "Python / SDK",
"traps": [
 "TTL is not invalidation. If the source data changes, delete/update the cache key immediately; TTL only bounds how long stale data can survive after a missed invalidation.",
 "Do not choose a volatile eviction policy for RediSearch indexes. Azure Managed Redis requires <b>NoEviction</b> with RediSearch.",
 "Modules cannot be added later. If RediSearch was not enabled at creation, create a new cache with the module and migrate.",
 "Vector blobs must match <code>TYPE</code> and <code>DIM</code>. A JSON list string is not the same as a binary FLOAT32 vector for HASH-based RediSearch.",
],
"cleanup": r"""az redisenterprise delete -g rg-ai200-data -n <redis-name> --yes
# or delete the whole lab group if it contains only data-domain resources:
az group delete -n rg-ai200-data --yes --no-wait""",
},
]

