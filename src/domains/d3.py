# -*- coding: utf-8 -*-
# Domain 3 - Connect to and consume Azure services (20-25%)

DOMAIN = {
    "key": "connect",
    "name": "Connect to and Consume Azure Services",
    "weight": "20\u201325%",
    "blurb": "Azure Service Bus for durable back-end messaging (queues, topics, subscriptions, filters and dead-letter handling), Event Grid for reactive discrete events (custom events, filters, retry policy and dead-lettering), and Azure Functions for serverless APIs with triggers, bindings, configuration and deployment. Expect scenario questions that distinguish transactional messaging from event notification, and code questions that test SDK client names, trigger/binding decorators and CLI deployment flags.",
}

LABS = [
# ---------------------------------------------------------------- 3.1
{
"id": "3.1",
"title": "Process back-end work with Azure Service Bus queues and dead-letter handling",
"time": "35 min",
"level": "Core",
"objective": "Create a Service Bus queue, process messages safely with peek-lock, deliberately dead-letter failures, and inspect the dead-letter subqueue.",
"exam": [
 "Service Bus queues are for <b>durable, transactional work</b>: one consumer completes a message, or the message becomes visible again after its <b>lock duration</b>. This is not Event Grid's fire-and-retry event notification model.",
 "<b>Peek-lock</b> is the default receive mode in the Python SDK: receive obtains a lock, then your code calls <code>complete_message</code>, <code>abandon_message</code>, <code>dead_letter_message</code> or lets the lock expire. <b>Receive-and-delete</b> removes on receive and is almost never the right answer for reliable processing.",
 "<b>MaxDeliveryCount</b> defaults to <code>10</code>. After too many abandoned/expired deliveries, Service Bus moves the message to the <b>dead-letter queue</b> automatically; code can also dead-letter with a reason and description.",
 "The DLQ is a <b>subqueue</b>, not a separate queue you create. In the SDK use <code>get_queue_receiver(..., sub_queue=ServiceBusSubQueue.DEAD_LETTER)</code>.",
 "Locks expire. Long work needs either a longer queue <b>lock duration</b> or auto/manual lock renewal; completing after the lock is lost raises a lock-lost error.",
],
"prereq": "Azure CLI 2.x, a Standard Service Bus namespace, and Python packages <code>azure-servicebus</code> and <code>python-dotenv</code> for local testing.",
"portal": [
 "##Create the namespace and queue",
 "Azure portal → search <b>Service Bus</b> → <b>+ Create</b>. Resource group <code>rg-ai200-connect</code>, namespace <code>sb-ai200-&lt;unique&gt;</code>, SKU <b>Standard</b>, region near you.",
 "Open the namespace → <b>Queues</b> → <b>+ Queue</b>. Name <code>jobs</code>, Max delivery count <code>3</code> for the lab, Lock duration <code>1 minute</code>. Leave dead-lettering on message expiration off unless the scenario asks for it.",
 "##Send and process",
 "Namespace → <b>Shared access policies</b> → <b>RootManageSharedAccessKey</b> → copy the primary connection string for the local SDK sample (use managed identity in production).",
 "Run the Python tab. Watch successful messages get <b>completed</b>, transient messages get <b>abandoned</b>, and poison messages get explicitly or automatically <b>dead-lettered</b>.",
 "##Inspect the DLQ",
 "Queue <code>jobs</code> → <b>Service Bus Explorer</b> → select the <b>Dead-letter</b> subqueue. Peek messages and inspect <code>DeadLetterReason</code>, delivery count and application properties.",
 "Reprocess a DLQ message by reading from the dead-letter subqueue and sending a corrected copy to the active queue; completing the DLQ message removes it from the DLQ.",
],
"cli": r"""RG=rg-ai200-connect
LOC=eastus
SBNS=sb-ai200-$RANDOM       # globally unique, 6-50 chars, letters/numbers/hyphens
QUEUE=jobs

az group create -n $RG -l $LOC

# --- Standard namespace: queues now, topics/subscriptions in Lab 3.2 -----
az servicebus namespace create -g $RG -n $SBNS -l $LOC --sku Standard

# MaxDeliveryCount defaults to 10. Set 3 here so DLQ behaviour is easy to see.
az servicebus queue create -g $RG --namespace-name $SBNS --name $QUEUE \
  --max-delivery-count 3 \
  --lock-duration PT1M \
  --default-message-time-to-live P14D

# Connection string for a local lab. Prefer Microsoft Entra auth / managed identity in apps.
az servicebus namespace authorization-rule keys list \
  -g $RG --namespace-name $SBNS -n RootManageSharedAccessKey \
  --query primaryConnectionString -o tsv

# Useful inspections -------------------------------------------------------
az servicebus queue show -g $RG --namespace-name $SBNS --name $QUEUE \
  --query "{maxDeliveryCount:maxDeliveryCount,lockDuration:lockDuration,count:messageCount}" -o table

az servicebus queue show -g $RG --namespace-name $SBNS --name $QUEUE \
  --query "countDetails" -o json""",
"code": r"""# pip install azure-servicebus python-dotenv
# .env: SERVICEBUS_CONNECTION_STRING="Endpoint=sb://..."
#
# Exam point: receive mode is a reliability decision. Peek-lock lets you complete
# only after work succeeds; receive-and-delete is faster but can lose work forever.
import os
from dotenv import load_dotenv
from azure.servicebus import (
    ServiceBusClient,
    ServiceBusMessage,
    ServiceBusReceiveMode,
    ServiceBusSubQueue,
)

load_dotenv()
CONNECTION_STR = os.environ["SERVICEBUS_CONNECTION_STRING"]
QUEUE = os.getenv("SERVICEBUS_QUEUE", "jobs")


def seed_messages(client: ServiceBusClient) -> None:
    with client.get_queue_sender(queue_name=QUEUE) as sender:
        sender.send_messages([
            ServiceBusMessage("ok: resize image", subject="lab", message_id="job-ok-1"),
            ServiceBusMessage("retry: flaky dependency", subject="lab", message_id="job-retry-1"),
            ServiceBusMessage("poison: invalid payload", subject="lab", message_id="job-poison-1"),
        ])


def process_once(client: ServiceBusClient) -> None:
    # Default is ServiceBusReceiveMode.PEEK_LOCK. The message is invisible only
    # while the lock is held; complete/abandon/dead-letter settles it.
    with client.get_queue_receiver(queue_name=QUEUE, max_wait_time=5) as receiver:
        for msg in receiver.receive_messages(max_message_count=10, max_wait_time=5):
            body = str(msg)
            print(f"received id={msg.message_id} delivery={msg.delivery_count} body={body}")
            if body.startswith("ok:"):
                receiver.complete_message(msg)       # permanently remove after success
            elif body.startswith("retry:"):
                receiver.abandon_message(msg)        # make available for another try
            else:
                receiver.dead_letter_message(
                    msg,
                    reason="InvalidPayload",
                    error_description="Schema validation failed; needs manual triage.",
                )


def force_max_delivery_to_dlq(client: ServiceBusClient) -> None:
    with client.get_queue_sender(queue_name=QUEUE) as sender:
        sender.send_messages(ServiceBusMessage("always failing", message_id="auto-dlq-1"))

    # Abandon the same logical message repeatedly. When delivery_count exceeds
    # MaxDeliveryCount, Service Bus moves it to the DLQ automatically.
    for _ in range(5):
        with client.get_queue_receiver(queue_name=QUEUE, max_wait_time=3) as receiver:
            messages = receiver.receive_messages(max_message_count=1, max_wait_time=3)
            if not messages:
                break
            msg = messages[0]
            print(f"abandoning {msg.message_id}, delivery={msg.delivery_count}")
            receiver.abandon_message(msg)


def read_dead_letters(client: ServiceBusClient) -> None:
    with client.get_queue_receiver(
        queue_name=QUEUE,
        sub_queue=ServiceBusSubQueue.DEAD_LETTER,
        max_wait_time=5,
    ) as dlq:
        for msg in dlq.receive_messages(max_message_count=20, max_wait_time=5):
            print(
                "DLQ",
                msg.message_id,
                "reason=", msg.dead_letter_reason,
                "description=", msg.dead_letter_error_description,
                "body=", str(msg),
            )
            # Complete only after you have recorded/replayed/triaged it.
            dlq.complete_message(msg)


def unsafe_receive_and_delete(client: ServiceBusClient) -> None:
    # Demonstration only: if the process crashes after this receive, the message is gone.
    with client.get_queue_receiver(
        queue_name=QUEUE,
        receive_mode=ServiceBusReceiveMode.RECEIVE_AND_DELETE,
        max_wait_time=2,
    ) as receiver:
        print("receive-and-delete sample:", receiver.receive_messages(max_message_count=1))


with ServiceBusClient.from_connection_string(CONNECTION_STR) as sb:
    seed_messages(sb)
    process_once(sb)
    force_max_delivery_to_dlq(sb)
    read_dead_letters(sb)""",
"code_label": "Python / SDK",
"traps": [
 "The dead-letter queue is addressed as a <b>subqueue</b>. Creating a second queue named <code>jobs-dlq</code> is not how Service Bus DLQ works.",
 "<code>abandon_message</code> is for retry; <code>dead_letter_message</code> is for terminal failure. <code>defer_message</code> hides a message until you retrieve it by sequence number and is a different feature.",
 "<b>Receive-and-delete</b> may be acceptable for telemetry-like loss-tolerant reads, but for back-end work the exam expects <b>peek-lock</b> plus explicit settlement.",
 "Max delivery count is checked after repeated deliveries caused by abandon/lock expiry. A single exception in your code does not magically DLQ unless the message is re-delivered enough times or you explicitly dead-letter it.",
 "If processing can exceed the lock duration, renew the lock; otherwise <code>complete_message</code> can fail because another worker may already own the message.",
],
"cleanup": r"""az servicebus queue delete -g rg-ai200-connect --namespace-name <servicebus-namespace> --name jobs
# or delete everything from this domain:
az group delete -n rg-ai200-connect --yes --no-wait""",
},
# ---------------------------------------------------------------- 3.2
{
"id": "3.2",
"title": "Publish/subscribe with Service Bus topics, subscriptions and filters",
"time": "35 min",
"level": "Core",
"objective": "Fan out messages through a Service Bus topic, route copies with SQL and correlation filters, and receive from independent subscriptions.",
"exam": [
 "A <b>topic</b> publishes one message to many <b>subscriptions</b>; each subscription acts like its own virtual queue. Use topics for fan-out, not multiple consumers competing on the same queue.",
 "<b>Rules/filters</b> live on subscriptions. The default rule is an all-pass <code>TrueFilter</code>; delete it when you want only matching messages.",
 "<b>SQL filters</b> can evaluate application properties (e.g. <code>priority = 'high'</code>) and system properties via <code>sys.</code>. <b>Correlation filters</b> are optimized exact matches on fields like <code>correlation_id</code>, <code>subject</code>/<code>label</code>, <code>session_id</code> and custom properties.",
 "Each subscription has its own delivery count, locks and DLQ. Completing a message in one subscription does not remove it from another subscription.",
 "Sessions are optional and solve ordered, stateful processing for related messages; a normal topic subscription does not guarantee global ordering under parallel consumers.",
],
"prereq": "Lab 3.1 Service Bus namespace on the <b>Standard</b> tier. Topics and subscriptions are not available in Basic.",
"portal": [
 "##Create the topic",
 "Namespace → <b>Topics</b> → <b>+ Topic</b>. Name <code>orders</code>. Keep duplicate detection and partitioning off unless the scenario explicitly needs them.",
 "Topic <code>orders</code> → <b>Subscriptions</b> → <b>+ Subscription</b>: create <code>all-orders</code>, <code>priority-orders</code> and <code>billing-correlation</code>.",
 "##Configure filters",
 "Open <code>priority-orders</code> → <b>Rules</b>. Delete <code>$Default</code>, add SQL rule <code>high-priority</code> with expression <code>priority = 'high'</code>.",
 "Open <code>billing-correlation</code> → <b>Rules</b>. Delete <code>$Default</code>, add a correlation rule that matches <code>CorrelationId = billing</code>.",
 "Leave <code>all-orders</code> with the default rule so it receives every published order.",
 "##Send and observe fan-out",
 "Run the Python tab to publish three orders with different application properties and correlation IDs.",
 "Use <b>Service Bus Explorer</b> on each subscription. <code>all-orders</code> sees all messages, <code>priority-orders</code> sees only high priority, and <code>billing-correlation</code> sees only messages with the billing correlation ID.",
],
"cli": r"""RG=rg-ai200-connect
SBNS=<servicebus-namespace>
TOPIC=orders

# --- Topic + three independent subscriptions -----------------------------
az servicebus topic create -g $RG --namespace-name $SBNS --name $TOPIC

az servicebus topic subscription create -g $RG --namespace-name $SBNS \
  --topic-name $TOPIC --name all-orders

az servicebus topic subscription create -g $RG --namespace-name $SBNS \
  --topic-name $TOPIC --name priority-orders --max-delivery-count 5

az servicebus topic subscription create -g $RG --namespace-name $SBNS \
  --topic-name $TOPIC --name billing-correlation --max-delivery-count 5

# The default rule is "match everything"; remove it from filtered subscriptions.
az servicebus topic subscription rule delete -g $RG --namespace-name $SBNS \
  --topic-name $TOPIC --subscription-name priority-orders --name '$Default'

az servicebus topic subscription rule delete -g $RG --namespace-name $SBNS \
  --topic-name $TOPIC --subscription-name billing-correlation --name '$Default'

# SQL filter: evaluates application properties on the message.
az servicebus topic subscription rule create -g $RG --namespace-name $SBNS \
  --topic-name $TOPIC --subscription-name priority-orders \
  --name high-priority --filter-type SqlFilter \
  --filter-sql-expression "priority = 'high'"

# Correlation filter: optimized exact match on a system field.
az servicebus topic subscription rule create -g $RG --namespace-name $SBNS \
  --topic-name $TOPIC --subscription-name billing-correlation \
  --name billing-only --filter-type CorrelationFilter \
  --correlation-id billing

az servicebus topic subscription rule list -g $RG --namespace-name $SBNS \
  --topic-name $TOPIC --subscription-name priority-orders -o table""",
"code": r"""# pip install azure-servicebus python-dotenv
# .env: SERVICEBUS_CONNECTION_STRING="Endpoint=sb://..."
#
# The azure-servicebus package is data-plane: send and receive messages.
# Subscription rules are management-plane and are created above with Azure CLI.
import os
from dotenv import load_dotenv
from azure.servicebus import ServiceBusClient, ServiceBusMessage

load_dotenv()
CONNECTION_STR = os.environ["SERVICEBUS_CONNECTION_STRING"]
TOPIC = os.getenv("SERVICEBUS_TOPIC", "orders")
SUBSCRIPTIONS = ["all-orders", "priority-orders", "billing-correlation"]


def publish_orders(client: ServiceBusClient) -> None:
    messages = [
        ServiceBusMessage(
            "order 1001",
            message_id="order-1001",
            subject="order-created",
            correlation_id="billing",
            application_properties={"priority": "high", "tenant": "contoso"},
        ),
        ServiceBusMessage(
            "order 1002",
            message_id="order-1002",
            subject="order-created",
            correlation_id="fulfillment",
            application_properties={"priority": "normal", "tenant": "contoso"},
        ),
        ServiceBusMessage(
            "order 1003",
            message_id="order-1003",
            subject="order-created",
            correlation_id="billing",
            application_properties={"priority": "low", "tenant": "fabrikam"},
        ),
    ]
    with client.get_topic_sender(topic_name=TOPIC) as sender:
        sender.send_messages(messages)


def drain_subscription(client: ServiceBusClient, subscription: str) -> None:
    with client.get_subscription_receiver(
        topic_name=TOPIC,
        subscription_name=subscription,
        max_wait_time=5,
    ) as receiver:
        print(f"\n--- {subscription} ---")
        for msg in receiver.receive_messages(max_message_count=10, max_wait_time=5):
            props = dict(msg.application_properties or {})
            print(
                msg.message_id,
                "correlation_id=", msg.correlation_id,
                "priority=", props.get(b"priority") or props.get("priority"),
                "body=", str(msg),
            )
            receiver.complete_message(msg)


with ServiceBusClient.from_connection_string(CONNECTION_STR) as sb:
    publish_orders(sb)
    for sub in SUBSCRIPTIONS:
        drain_subscription(sb, sub)""",
"code_label": "Python / SDK",
"traps": [
 "If you forget to delete <code>$Default</code>, a filtered subscription still receives every message. This is the most common topic-filter lab mistake.",
 "Queue with many consumers = <b>competing consumers</b> (one copy processed once). Topic with many subscriptions = <b>pub/sub fan-out</b> (one copy per matching subscription).",
 "A SQL filter checks message properties, not arbitrary JSON body content. Put routing values in <code>application_properties</code> or system fields.",
 "Correlation filters are exact-match and fast; choose SQL filters when you need comparisons, <code>IN</code>, <code>LIKE</code> or compound expressions.",
 "A subscription DLQ belongs to that subscription. A poison message in <code>priority-orders</code> does not prove <code>all-orders</code> failed.",
],
"cleanup": r"""az servicebus topic delete -g rg-ai200-connect --namespace-name <servicebus-namespace> --name orders
az group delete -n rg-ai200-connect --yes --no-wait""",
},
# ---------------------------------------------------------------- 3.3
{
"id": "3.3",
"title": "Event-driven workflows with Azure Event Grid: custom events, filters and retries",
"time": "35 min",
"level": "Core",
"objective": "Publish custom Event Grid events, route them with subject and advanced filters, and configure retries plus Storage dead-lettering for failed delivery.",
"exam": [
 "<b>Event Grid</b> is for reactive, discrete events: 'something happened'. It provides push delivery with retry and filtering; it is not a durable command queue like Service Bus and not a high-throughput telemetry stream like Event Hubs.",
 "Custom topics accept <b>Event Grid schema</b>, <b>CloudEvents v1.0</b> or custom input schema. The Python SDK uses <code>EventGridPublisherClient</code> from <code>azure-eventgrid</code>.",
 "Filtering happens in the <b>event subscription</b>: subject prefix/suffix filters, included event types, and advanced filters such as <code>data.tier StringIn gold platinum</code>.",
 "Delivery is <b>at least once</b>. Handlers must be idempotent because retries can deliver duplicates; Event Grid does not preserve strict ordering.",
 "Retry policy is controlled with <b>max delivery attempts</b> and <b>event TTL</b>. Configure a Storage container dead-letter endpoint when undeliverable events must be retained for inspection.",
],
"prereq": "Azure CLI 2.x, Python packages <code>azure-eventgrid</code> and <code>azure-core</code>, and a HTTPS webhook/Function endpoint that can answer Event Grid subscription validation events.",
"portal": [
 "##Create the custom topic",
 "Portal → <b>Event Grid Topics</b> → <b>+ Create</b>. RG <code>rg-ai200-connect</code>, name <code>egt-ai200-&lt;unique&gt;</code>, region near the handler, input schema <b>Event Grid Schema</b>.",
 "Open the topic → <b>Access keys</b> for the endpoint/key used by the Python publisher. In production prefer managed identity where supported by the publishing path.",
 "##Create dead-letter storage",
 "Create a StorageV2 account and private container <code>eventgrid-deadletter</code>. The event subscription will write failed events there after retries are exhausted or TTL expires.",
 "##Create the event subscription",
 "Topic → <b>Event Subscriptions</b> → <b>+ Event Subscription</b>. Name <code>orders-webhook</code>, endpoint type <b>Web Hook</b>, endpoint your HTTPS handler.",
 "Set <b>Event types</b> to <code>Contoso.OrderCreated</code>. Add subject filter <code>/orders/</code> and an advanced filter <code>data.tier StringIn gold platinum</code>.",
 "Open <b>Additional features</b>: Max delivery attempts <code>12</code>, Event TTL <code>1440</code> minutes, Dead-letter endpoint = the Storage container.",
 "##Publish and verify",
 "Run the Python tab. Events with subject under <code>/orders/</code> and tier <code>gold</code>/<code>platinum</code> reach the handler; non-matching events are dropped before delivery.",
 "Temporarily return HTTP 500 from the handler to watch retries. After policy exhaustion, inspect blobs in <code>eventgrid-deadletter</code>.",
],
"cli": r"""RG=rg-ai200-connect
LOC=eastus
TOPIC=egt-ai200-$RANDOM
SUB=orders-webhook
SA=ai200egdl$RANDOM
CONTAINER=eventgrid-deadletter
WEBHOOK=https://<your-public-endpoint>/api/events

az group create -n $RG -l $LOC

# --- Custom Event Grid topic using Event Grid schema ----------------------
az eventgrid topic create -g $RG -n $TOPIC -l $LOC --input-schema eventgridschema

ENDPOINT=$(az eventgrid topic show -g $RG -n $TOPIC --query endpoint -o tsv)
KEY=$(az eventgrid topic key list -g $RG -n $TOPIC --query key1 -o tsv)
echo "EVENTGRID_TOPIC_ENDPOINT=$ENDPOINT"
echo "EVENTGRID_TOPIC_KEY=$KEY"

# --- Storage container used for dead-lettered delivery attempts ----------
az storage account create -g $RG -n $SA -l $LOC --sku Standard_LRS --kind StorageV2 \
  --allow-blob-public-access false
SA_KEY=$(az storage account keys list -g $RG -n $SA --query "[0].value" -o tsv)
az storage container create --account-name $SA --account-key $SA_KEY -n $CONTAINER

SA_ID=$(az storage account show -g $RG -n $SA --query id -o tsv)
DLQ_ID="$SA_ID/blobServices/default/containers/$CONTAINER"
TOPIC_ID=$(az eventgrid topic show -g $RG -n $TOPIC --query id -o tsv)

# --- Subscription: filters + retry policy + dead-letter destination -------
az eventgrid event-subscription create \
  --name $SUB \
  --source-resource-id $TOPIC_ID \
  --endpoint-type webhook \
  --endpoint "$WEBHOOK" \
  --included-event-types Contoso.OrderCreated \
  --subject-begins-with /orders/ \
  --advanced-filter data.tier StringIn gold platinum \
  --max-delivery-attempts 12 \
  --event-ttl 1440 \
  --deadletter-endpoint "$DLQ_ID"

az eventgrid event-subscription show --name $SUB --source-resource-id $TOPIC_ID \
  --query "{endpoint:destination.endpointUrl,attempts:retryPolicy.maxDeliveryAttempts,ttl:retryPolicy.eventTimeToLiveInMinutes}" -o json""",
"code": r"""# pip install azure-eventgrid azure-core python-dotenv
# .env:
#   EVENTGRID_TOPIC_ENDPOINT="https://<topic>.<region>-1.eventgrid.azure.net/api/events"
#   EVENTGRID_TOPIC_KEY="<key>"
#
# Event Grid publisher code sends facts ("OrderCreated"), not commands ("ProcessOrder").
# Consumers must be idempotent because delivery is at least once.
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.eventgrid import EventGridEvent, EventGridPublisherClient

load_dotenv()
endpoint = os.environ["EVENTGRID_TOPIC_ENDPOINT"]
key = os.environ["EVENTGRID_TOPIC_KEY"]

client = EventGridPublisherClient(endpoint, AzureKeyCredential(key))

events = [
    EventGridEvent(
        subject="/orders/1001",
        event_type="Contoso.OrderCreated",
        data_version="1.0",
        data={
            "orderId": "1001",
            "tier": "gold",
            "total": 249.00,
            "dedupeKey": str(uuid.uuid4()),
        },
    ),
    EventGridEvent(
        subject="/orders/1002",
        event_type="Contoso.OrderCreated",
        data_version="1.0",
        data={"orderId": "1002", "tier": "bronze", "total": 19.00},
    ),
    EventGridEvent(
        subject="/inventory/sku-99",
        event_type="Contoso.InventoryAdjusted",
        data_version="1.0",
        data={"sku": "sku-99", "tier": "gold", "delta": -1},
    ),
]

# Only the first event matches: event type Contoso.OrderCreated, subject /orders/,
# and advanced filter data.tier in [gold, platinum].
client.send(events)
print(f"published {len(events)} events at {datetime.now(timezone.utc).isoformat()}")


# Handler reminder (webhook or Azure Function):
# - Reply to Microsoft.EventGrid.SubscriptionValidationEvent with validationResponse.
# - Return 2xx only after durable/idempotent processing.
# - Treat duplicate event IDs as normal; retries are expected.""",
"code_label": "Python / SDK",
"traps": [
 "Service Bus vs Event Grid vs Event Hubs: <b>Service Bus</b> = commands/work with locks and DLQ; <b>Event Grid</b> = discrete event notification with filtering/retry; <b>Event Hubs</b> = high-throughput streaming/telemetry with partitions and offsets.",
 "Event Grid retries do not make your handler transactional. If the handler performs side effects and then returns 500, the same event can be delivered again.",
 "Filters are evaluated by Event Grid before delivery. A non-matching event is not a failed delivery and will not appear in the dead-letter container.",
 "Webhook endpoints must pass the <b>subscription validation handshake</b>; a normal API route that ignores validation events cannot be subscribed.",
 "Dead-lettering requires a Storage <b>container resource ID</b>, not just a connection string or a blob URL.",
],
"cleanup": r"""az eventgrid event-subscription delete --name orders-webhook \
  --source-resource-id $(az eventgrid topic show -g rg-ai200-connect -n <topic-name> --query id -o tsv)
az eventgrid topic delete -g rg-ai200-connect -n <topic-name> --yes
az storage account delete -g rg-ai200-connect -n <storage-account> --yes
az group delete -n rg-ai200-connect --yes --no-wait""",
},
# ---------------------------------------------------------------- 3.4
{
"id": "3.4",
"title": "Build a serverless API with Azure Functions triggers and bindings",
"time": "35 min",
"level": "Foundational",
"objective": "Create a Python v2 Azure Functions app with an HTTP-triggered API, a queue output binding, and a queue-triggered worker that writes results through an output binding.",
"exam": [
 "<b>Triggers start a function</b>; <b>bindings move data in/out</b> without hand-written client plumbing. Every function has exactly one trigger and can have multiple input/output bindings.",
 "The Python <b>v2 programming model</b> uses decorators in <code>function_app.py</code>: <code>@app.route</code>, <code>@app.queue_trigger</code>, <code>@app.queue_output</code>, <code>@app.blob_output</code> and <code>@app.function_name</code>.",
 "<code>host.json</code> configures the Functions host and extensions. <code>local.settings.json</code> stores local app settings and secrets; it is not deployed and should not be committed.",
 "HTTP trigger auth levels are <b>anonymous</b>, <b>function</b> and <b>admin</b>. A serverless API often uses <code>function</code> or front-door/API Management auth rather than anonymous.",
 "Queue triggers automatically retry failed executions and move poison Storage Queue messages to a poison queue after the configured dequeue count; that is separate from Service Bus DLQ.",
],
"prereq": "Python 3.10+ or 3.11, Azure Functions Core Tools v4, Azurite or a real Storage account for <code>AzureWebJobsStorage</code>, and package <code>azure-functions</code>.",
"portal": [
 "##Understand the app shape",
 "A client calls <code>POST /api/analyze</code>. The HTTP-triggered function validates the request and writes a small work item to Storage Queue <code>ai-jobs</code> through an <b>output binding</b>.",
 "A second function is started by a <b>queue trigger</b>, processes the work item, then writes a result JSON blob through a <b>blob output binding</b>.",
 "##Create locally",
 "Run the CLI tab to create a Python v2 Functions project. Replace the generated <code>function_app.py</code> with the code tab.",
 "Start Azurite (or set a real <code>AzureWebJobsStorage</code> connection), then run <code>func start</code>. The terminal shows discovered functions and routes.",
 "##Test the API",
 "POST JSON to <code>http://localhost:7071/api/analyze</code>. A successful call returns <code>202 Accepted</code> and places a message on <code>ai-jobs</code>.",
 "Watch the queue-triggered function fire automatically. In Storage Explorer, confirm the queue message disappears and a blob appears under <code>results/</code>.",
 "##Map decorators to portal integration",
 "After deployment, Function App → <b>Functions</b> → each function → <b>Integration</b> shows the trigger and bindings that came from the decorators.",
],
"cli": r"""# Core Tools v4. Run from a development folder, not inside the generated src/domains folder.
func init ai200-functions --worker-runtime python --model v2
cd ai200-functions

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install azure-functions
python -m pip freeze > requirements.txt

# For local non-HTTP triggers/bindings, use Azurite or a real Storage connection.
# With Azurite running locally:
func settings add AzureWebJobsStorage UseDevelopmentStorage=true
func settings add FUNCTIONS_WORKER_RUNTIME python

# Replace function_app.py with the code tab, then run locally.
func start

# In another shell:
curl -i http://localhost:7071/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"documentId":"doc-001","text":"summarize this document"}'""",
"code": r"""# function_app.py - Python v2 programming model.
# Trigger starts execution; bindings connect data sources/sinks declaratively.
import json
import logging
import uuid
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.function_name(name="StartAnalysis")
@app.route(route="analyze", methods=["POST"])
@app.queue_output(arg_name="job", queue_name="ai-jobs", connection="AzureWebJobsStorage")
def start_analysis(req: func.HttpRequest, job: func.Out[str]) -> func.HttpResponse:
    try:
        body = req.get_json()
        text = body["text"]
    except (ValueError, KeyError):
        return func.HttpResponse("Body must be JSON with a 'text' field.", status_code=400)

    job_id = str(uuid.uuid4())
    job.set(json.dumps({
        "id": job_id,
        "documentId": body.get("documentId", job_id),
        "text": text,
    }))

    return func.HttpResponse(
        json.dumps({"id": job_id, "status": "queued"}),
        status_code=202,
        mimetype="application/json",
    )


@app.function_name(name="ProcessAnalysis")
@app.queue_trigger(arg_name="message", queue_name="ai-jobs", connection="AzureWebJobsStorage")
@app.blob_output(arg_name="result", path="results/{id}.json", connection="AzureWebJobsStorage")
def process_analysis(message: func.QueueMessage, result: func.Out[str]) -> None:
    payload = json.loads(message.get_body().decode("utf-8"))
    logging.info("Processing analysis job %s", payload["id"])

    # Replace this with an Azure AI call in a real app. Keep queue payloads small.
    summary = payload["text"][:120]
    result.set(json.dumps({
        "id": payload["id"],
        "documentId": payload["documentId"],
        "summary": summary,
    }))""",
"code_label": "function_app.py",
"traps": [
 "A binding is not a trigger. <code>@app.queue_output</code> writes a queue message; it does not start the function. <code>@app.queue_trigger</code> starts the worker when a message appears.",
 "Do not put secrets in <code>function_app.py</code> or commit <code>local.settings.json</code>. App settings are the deployment-time configuration boundary.",
 "The route defaults to <code>/api/&lt;route&gt;</code>. If your local URL misses the <code>/api</code> prefix, the function may be healthy but unreachable.",
 "Storage Queue poison handling is not the same API as Service Bus dead-lettering. The exam commonly swaps these terms.",
 "Bindings are convenient, but large payloads should go to Blob Storage/Cosmos DB and the queue should carry a pointer; Storage Queue messages have size limits.",
],
"cleanup": r"""# Local cleanup only:
rm -rf ai200-functions

# If you used a real Storage account:
az storage account delete -g rg-ai200-connect -n <storage-account> --yes""",
},
# ---------------------------------------------------------------- 3.5
{
"id": "3.5",
"title": "Configure and deploy an Azure Functions app",
"time": "35 min",
"level": "Core",
"objective": "Create a Linux Consumption Function App, configure app settings and managed identity access, then deploy a Python project with Core Tools.",
"exam": [
 "A Function App is the deployment and configuration boundary. All functions in the app share app settings, managed identity, networking, Application Insights and hosting plan.",
 "For serverless hosting choose <b>Flex Consumption</b> or <b>Consumption</b> when you want scale-out without managing servers. Premium/Dedicated are distractors when the scenario does not need VNET-heavy warm instances or fixed capacity.",
 "Deploy Python Functions with Core Tools from the project root using <code>func azure functionapp publish &lt;app&gt; --python</code>. The app's runtime stack must match the local Python version supported by Azure Functions.",
 "Use <b>app settings</b> for configuration and connection names referenced by decorators. For identity-based connections, settings use a prefix such as <code>ServiceBusConnection__fullyQualifiedNamespace</code> instead of a secret connection string.",
 "Turn on a <b>system-assigned managed identity</b> and grant least-privilege roles such as <b>Azure Service Bus Data Receiver</b>/<b>Data Sender</b>. Do not store root SAS keys when managed identity is available.",
],
"prereq": "Completed Lab 3.4 project, Azure CLI 2.x, Azure Functions Core Tools v4, and an existing Service Bus namespace if you want to test identity-based Service Bus bindings.",
"portal": [
 "##Create the Function App",
 "Portal → <b>Function App</b> → <b>+ Create</b>. Hosting plan <b>Consumption</b> (or <b>Flex Consumption</b> where available), OS <b>Linux</b>, runtime <b>Python</b>, Functions version <b>4</b>.",
 "Create or select a Storage account for the Functions host. Enable <b>Application Insights</b> for logs, failures and invocation traces.",
 "##Configure settings",
 "Function App → <b>Settings → Environment variables</b> → add app settings used by your code, for example <code>AI_ENDPOINT</code>, <code>MODEL_DEPLOYMENT</code> and <code>ServiceBusConnection__fullyQualifiedNamespace</code>.",
 "Function App → <b>Identity</b> → turn <b>System assigned</b> on. Grant roles on downstream services: Service Bus Data Receiver for triggers, Data Sender for output messages, Key Vault Secrets User for secrets.",
 "##Deploy",
 "From the local Functions project root, run <code>func azure functionapp publish &lt;app-name&gt; --python</code>. Core Tools packages and deploys the project.",
 "Function App → <b>Functions</b> confirms discovered functions. Use <b>Log stream</b>, <b>Application Insights</b> and <b>Diagnose and solve problems</b> for startup or binding errors.",
 "##Verify",
 "Call the HTTP endpoint with the function key, then check logs. If a trigger does not start, verify the extension bundle, connection setting name, role assignment and queue/topic names.",
],
"cli": r"""RG=rg-ai200-connect
LOC=eastus
APP=func-ai200-$RANDOM
SA=ai200funcsa$RANDOM
SBNS=<servicebus-namespace>

az group create -n $RG -l $LOC

# Host storage is required by the Functions runtime even when your app uses other services.
az storage account create -g $RG -n $SA -l $LOC --sku Standard_LRS --kind StorageV2

# Linux Consumption plan. Use --flexconsumption-location instead when choosing Flex Consumption.
az functionapp create -g $RG -n $APP \
  --storage-account $SA \
  --consumption-plan-location $LOC \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux

# App settings are what decorator 'connection=' names resolve to at runtime.
az functionapp config appsettings set -g $RG -n $APP --settings \
  FUNCTIONS_WORKER_RUNTIME=python \
  AI_ENDPOINT=https://<azure-ai-endpoint> \
  MODEL_DEPLOYMENT=gpt-4o \
  ServiceBusConnection__fullyQualifiedNamespace=$SBNS.servicebus.windows.net

# Managed identity + least-privilege data-plane roles for Service Bus bindings.
az functionapp identity assign -g $RG -n $APP
PRINCIPAL=$(az functionapp identity show -g $RG -n $APP --query principalId -o tsv)
SB_ID=$(az servicebus namespace show -g $RG -n $SBNS --query id -o tsv)
az role assignment create --assignee $PRINCIPAL --role "Azure Service Bus Data Receiver" --scope $SB_ID
az role assignment create --assignee $PRINCIPAL --role "Azure Service Bus Data Sender" --scope $SB_ID

# Deploy from the Python Functions project root created in Lab 3.4.
func azure functionapp publish $APP --python

# Observe startup and invocation logs.
az functionapp log tail -g $RG -n $APP""",
"code": r"""#!/usr/bin/env bash
# deploy.sh - run from the folder that contains function_app.py, host.json and requirements.txt.
# This is the repeatable deployment checklist the exam maps to "configure and deploy".
set -euo pipefail

APP_NAME="${APP_NAME:?set APP_NAME to your Function App name}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-ai200-connect}"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Optional local smoke test before publishing. If functions are not discovered
# here, Azure will not discover them either. Stop it with Ctrl+C, then publish.
# func start --verbose

# Publish the Python app. Core Tools zips the project and triggers the Azure build/deploy flow.
func azure functionapp publish "$APP_NAME" --python

# Post-deploy checks: app settings, discovered functions and live logs.
az functionapp config appsettings list -g "$RESOURCE_GROUP" -n "$APP_NAME" \
  --query "[].{name:name,value:value}" -o table

az functionapp function list -g "$RESOURCE_GROUP" -n "$APP_NAME" -o table
az functionapp log tail -g "$RESOURCE_GROUP" -n "$APP_NAME" """,
"code_label": "Bash",
"traps": [
 "Publishing from the wrong folder deploys an empty app. The project root must contain <code>function_app.py</code>, <code>host.json</code> and <code>requirements.txt</code>.",
 "A missing app setting with the exact binding <code>connection</code> name causes startup/binding errors. <code>ServiceBusConnection</code> and <code>ServiceBusConn</code> are different names.",
 "Managed identity role assignments can take a few minutes to propagate. A newly deployed trigger may fail with authorization errors before the role is effective.",
 "Consumption hosting can cold start. If the scenario requires pre-warmed instances, VNET integration at scale, or longer execution limits, evaluate Premium/Flex rather than classic Consumption.",
 "Do not confuse <code>az functionapp deployment source config-zip</code> with Core Tools publish. Config-zip uploads bits; Core Tools understands Functions project conventions and Python builds.",
],
"cleanup": r"""az functionapp delete -g rg-ai200-connect -n <function-app-name>
az storage account delete -g rg-ai200-connect -n <storage-account> --yes
az group delete -n rg-ai200-connect --yes --no-wait""",
},
]
