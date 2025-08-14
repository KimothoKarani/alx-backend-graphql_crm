from django.core.management.base import BaseCommand
from decimal import Decimal
from datetime import datetime, timezone

# Import your pure-Python datastore (avoid importing schema/graphene here)
from crm.schema import InMemoryDataStore  # adjust if yours lives elsewhere

class Command(BaseCommand):
    help = "Seed the in-memory datastore"

    def handle(self, *args, **options):
        InMemoryDataStore.reset()

        c1 = InMemoryDataStore.create_customer("Alice Wonderland", "alice@example.com", "+11234567890")
        c2 = InMemoryDataStore.create_customer("Bob The Builder", "bob@example.com", "555-123-4567")
        c3 = InMemoryDataStore.create_customer("Charlie Chaplin", "charlie@example.com")

        p1 = InMemoryDataStore.create_product("Premium Coffee Mug", Decimal("15.99"), 200)
        p2 = InMemoryDataStore.create_product("Ergonomic Keyboard", Decimal("89.50"), 50)
        p3 = InMemoryDataStore.create_product("Noise-Cancelling Headphones", Decimal("249.00"), 30)
        p4 = InMemoryDataStore.create_product("USB-C Charging Cable", Decimal("12.00"), 500)

        order1_products = [p1["id"], p3["id"]]
        total1 = sum(InMemoryDataStore.get_product_by_id(pid)["price"] for pid in order1_products)
        InMemoryDataStore.create_order(
            c1["id"], order1_products, total1,
            datetime(2025, 7, 10, 10, 0, tzinfo=timezone.utc)
        )

        order2_products = [p2["id"], p4["id"], p4["id"]]
        total2 = sum(InMemoryDataStore.get_product_by_id(pid)["price"] for pid in set(order2_products))
        InMemoryDataStore.create_order(
            c2["id"], list(set(order2_products)), total2,
            datetime(2025, 7, 12, 14, 30, tzinfo=timezone.utc)
        )

        self.stdout.write(self.style.SUCCESS("In-memory datastore seeded."))
