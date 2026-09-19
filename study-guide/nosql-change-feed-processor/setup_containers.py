"""
Setup script to create the containers used by the change feed processor.

- orders:  the monitored container. Writes here show up in the change feed.
- leases:  the lease container used by the Azure Functions Cosmos DB trigger. It stores one
           checkpoint per feed range so the trigger can resume where it left off.

The leases container is created here rather than by the trigger
(create_lease_container_if_not_exists) because containers can't be created with Entra ID
data-plane permissions, which the identity-based connection uses.

Run this after the Cosmos DB account exists and COSMOS_ENDPOINT / COSMOS_DATABASE are set.
"""
import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential

MONITORED_CONTAINER = "orders"
LEASE_CONTAINER = "leases"


def get_database():
    """Get a reference to the Cosmos DB database using Entra ID authentication."""
    endpoint = os.environ.get("COSMOS_ENDPOINT")
    database_name = os.environ.get("COSMOS_DATABASE")

    if not endpoint or not database_name:
        raise ValueError(
            "COSMOS_ENDPOINT and COSMOS_DATABASE environment variables must be set."
        )

    client = CosmosClient(endpoint, credential=DefaultAzureCredential())
    return client.get_database_client(database_name)


def main():
    database = get_database()

    print(f"Creating monitored container '{MONITORED_CONTAINER}'...")
    database.create_container_if_not_exists(
        id=MONITORED_CONTAINER,
        partition_key=PartitionKey(path="/customerId"),
    )

    # Lease documents are keyed by processor name + feed range, so /id is a fine
    # partition key: each lease is read and written on its own.
    print(f"Creating lease container '{LEASE_CONTAINER}'...")
    database.create_container_if_not_exists(
        id=LEASE_CONTAINER,
        partition_key=PartitionKey(path="/id"),
    )

    print("Done. Next: run 'func start', then generate_changes.py in another terminal.")


if __name__ == "__main__":
    main()
