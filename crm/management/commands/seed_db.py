# crm/management/commands/seed_db.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from crm.models import Customer, Product, Order
import decimal
import datetime

class Command(BaseCommand):
    help = "Seed the database with sample customers, products, and orders."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Delete existing Customers/Products/Orders first.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Clearing existing data…")
            Order.objects.all().delete()
            Product.objects.all().delete()
            Customer.objects.all().delete()

        self.stdout.write("Seeding customers…")
        c1 = Customer.objects.create(name="Alice Wonderland",  email="alice@example.com",  phone="+11234567890")
        c2 = Customer.objects.create(name="Bob The Builder",    email="bob@example.com",    phone="555-123-4567")
        c3 = Customer.objects.create(name="Charlie Chaplin",    email="charlie@example.com")
        c4 = Customer.objects.create(name="Diana Prince",       email="diana@example.com",  phone="987-654-3210")

        self.stdout.write("Seeding products…")
        p1 = Product.objects.create(name="Premium Coffee Mug",           price=decimal.Decimal("15.99"), stock=200)
        p2 = Product.objects.create(name="Ergonomic Keyboard",           price=decimal.Decimal("89.50"), stock=50)
        p3 = Product.objects.create(name="Noise-Cancelling Headphones",  price=decimal.Decimal("249.00"), stock=30)
        p4 = Product.objects.create(name="USB-C Charging Cable",         price=decimal.Decimal("12.00"), stock=5)
        p5 = Product.objects.create(name="Wireless Mouse",               price=decimal.Decimal("35.00"), stock=150)

        self.stdout.write("Seeding orders…")
        dt1 = datetime.datetime(2025, 7, 10, 10, 0, 0, tzinfo=datetime.timezone.utc)
        dt2 = datetime.datetime(2025, 7, 12, 14, 30, 0, tzinfo=datetime.timezone.utc)

        o1 = Order.objects.create(customer=c1, total_amount=p1.price + p3.price, order_date=dt1)
        o1.products.add(p1, p3)

        o2 = Order.objects.create(customer=c2, total_amount=p2.price + p4.price, order_date=dt2)
        o2.products.add(p2, p4)

        self.stdout.write(self.style.SUCCESS("✓ Database seeding complete."))
