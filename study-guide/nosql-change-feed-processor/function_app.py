"""
Change feed processor for Azure Cosmos DB for NoSQL, using the Azure Functions Cosmos DB trigger.

The trigger runs the change feed processor for you. It reads the 'orders' container's change feed,
stores a checkpoint per feed range in the 'leases' container, and calls the function with each
batch of new or updated items. The lease container is what lets the function resume where it
left off and lets multiple instances share the work.

The default change feed (latest version) returns new and updated items, not deletes. Use a
soft-delete flag (e.g. "deleted": true) if you need to observe deletes.
"""
import logging

import azure.functions as func

app = func.FunctionApp()


@app.cosmos_db_trigger(
    arg_name="documents",
    connection="COSMOSDB",  # identity-based: COSMOSDB__accountEndpoint app setting
    database_name="%COSMOS_DATABASE%",
    container_name="orders",
    lease_container_name="leases",
    # Process items already in the container on the first run. Only applies before a
    # checkpoint exists in the lease container.
    start_from_beginning=True,
    max_items_per_invocation=100,
)
def process_order_changes(documents: func.DocumentList) -> None:
    """Handle a batch of new or updated orders. Delivery is at-least-once, so stay idempotent."""
    if not documents:
        return

    logging.info("Change feed delivered %d item(s)", len(documents))

    for doc in documents:
        # The feed doesn't say whether an item is new or updated; the writer tracks that.
        kind = "NEW" if doc.get("version") == 1 else "UPDATED"
        logging.info(
            "[%s] id=%s customer=%s status=%s total=%s",
            kind,
            doc.get("id"),
            doc.get("customerId"),
            doc.get("status"),
            doc.get("total"),
        )


