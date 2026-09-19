"""
Generate new and updated orders so the change feed trigger has something to detect.

Creates a few orders (version 1), then updates each one (version 2). Run this while
'func start' is running in another terminal and watch the function log each change.
"""
import time
import uuid

from setup_containers import MONITORED_CONTAINER, get_database


def main():
    container = get_database().get_container_client(MONITORED_CONTAINER)

    orders = []
    for n in range(3):
        order = {
            "id": str(uuid.uuid4()),
            "customerId": f"customer-{n % 2}",
            "status": "created",
            "total": 25.0 * (n + 1),
            "version": 1,
        }
        orders.append(container.create_item(order))
        print(f"Created order {order['id']}")

    time.sleep(2)

    for order in orders:
        order["status"] = "shipped"
        order["version"] = 2
        container.replace_item(order["id"], order)
        print(f"Updated order {order['id']} -> shipped")


if __name__ == "__main__":
    main()
