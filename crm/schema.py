import graphene
import datetime
import decimal
import re
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import EmailValidator
from django.db import IntegrityError, transaction
from django.db.models import Q, F  # Already used in filters.py
from django.utils import timezone  # For timezone.now()
from graphene_django.types import DjangoObjectType
from graphene.relay import Node  # For Relay Global IDs
from graphene_django.filter import DjangoFilterConnectionField  # <--- CRUCIAL IMPORT for filtering!

# Import your Django Models
from .models import Customer, Product, Order

# Import your Filter Classes
from .filters import CustomerFilter, ProductFilter, OrderFilter  # <--- NEW IMPORT


# --- GraphQL Output Types (CustomerType, ProductType, OrderType - remain same) ---
# They already implement `Node` from the previous step.

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = "__all__"
        interfaces = (Node,)


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = "__all__"
        interfaces = (Node,)


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = "__all__"
        interfaces = (Node,)


# --- Custom Error Type (ErrorType - remains same) ---
class ErrorType(graphene.ObjectType):
    field = graphene.String()
    message = graphene.String()
    code = graphene.String()


# --- GraphQL Input Types (CustomerInput, ProductInput - remain same) ---
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(default_value=0)


# --- Mutations (CreateCustomer, BulkCreateCustomers, CreateProduct, CreateOrder - remain same) ---
# The mutations already interact with Django Models, so no changes are needed here for Task 3.

class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    success = graphene.Boolean()
    errors = graphene.List(ErrorType)

    def mutate(self, info, input):
        phone_regex_pattern = r"^(\+\d{1,3})?\d{10,15}$|^\d{3}[-\s]?\d{3}[-\s]?\d{4}$"
        validation_errors = []
        if input.phone and not re.fullmatch(phone_regex_pattern, input.phone):
            validation_errors.append(
                ErrorType(field="phone", message="Invalid phone format. Expected: +1234567890 or 123-456-7890.",
                          code="INVALID_FORMAT"))
        if validation_errors:
            return CreateCustomer(success=False, errors=validation_errors)

        try:
            customer = Customer.objects.create(name=input.name, email=input.email, phone=input.phone)
            return CreateCustomer(customer=customer, message="Customer created successfully.", success=True, errors=[])
        except IntegrityError:
            return CreateCustomer(success=False, errors=[
                ErrorType(field="email", message="Email already exists.", code="DUPLICATE_EMAIL")])
        except ValidationError as e:
            field_errors = []
            if hasattr(e, 'message_dict'):
                for field, messages in e.message_dict.items():
                    for msg in messages:
                        field_errors.append(ErrorType(field=field, message=msg, code="VALIDATION_ERROR"))
            else:
                field_errors.append(ErrorType(message=str(e), code="VALIDATION_ERROR"))
            return CreateCustomer(success=False, errors=field_errors)
        except Exception as e:
            return CreateCustomer(success=False, errors=[
                ErrorType(field="general", message=f"An unexpected error occurred: {str(e)}", code="SERVER_ERROR")])


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(ErrorType)
    success_count = graphene.Int()

    def mutate(self, info, input):
        customers_to_create = []
        errors_list = []
        phone_regex_pattern = r"^(\+\d{1,3})?\d{10,15}$|^\d{3}[-\s]?\d{3}[-\s]?\d{4}$"
        emails_in_current_batch = set()

        for i, customer_input_data in enumerate(input):
            item_errors = []
            if not customer_input_data.name:
                item_errors.append(ErrorType(field=f"input[{i}].name", message=f"Customer at index {i} has no name.",
                                             code="REQUIRED_FIELD"))
            if not customer_input_data.email:
                item_errors.append(ErrorType(field=f"input[{i}].email", message=f"Customer at index {i} has no email.",
                                             code="REQUIRED_FIELD"))

            try:
                EmailValidator(message="Invalid email format.")(customer_input_data.email)
            except ValidationError:
                item_errors.append(
                    ErrorType(field=f"input[{i}].email", message=f"Customer at index {i}: Invalid email format.",
                              code="INVALID_FORMAT"))

            if Customer.objects.filter(email=customer_input_data.email).exists() or \
                    customer_input_data.email in emails_in_current_batch:
                item_errors.append(ErrorType(field=f"input[{i}].email",
                                             message=f"Customer at index {i}: Email already exists or is a duplicate within this batch.",
                                             code="DUPLICATE_EMAIL"))
            else:
                emails_in_current_batch.add(customer_input_data.email)
            if customer_input_data.phone:
                if not re.fullmatch(phone_regex_pattern, customer_input_data.phone):
                    item_errors.append(
                        ErrorType(field=f"input[{i}].phone", message=f"Customer at index {i}: Invalid phone format.",
                                  code="INVALID_FORMAT"))

            if item_errors:
                errors_list.extend(item_errors)
                continue

            customers_to_create.append(
                Customer(name=customer_input_data.name, email=customer_input_data.email,
                         phone=customer_input_data.phone)
            )

        with transaction.atomic():
            created_instances = Customer.objects.bulk_create(customers_to_create, ignore_conflicts=True)
            success_count = len(created_instances)
            created_customers = [CustomerType(**c.__dict__) for c in created_instances]

        return BulkCreateCustomers(customers=created_customers, errors=errors_list, success_count=success_count)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)
    success = graphene.Boolean()
    errors = graphene.List(ErrorType)

    def mutate(self, info, input):
        try:
            product = Product(name=input.name, price=input.price, stock=input.stock)
            product.full_clean()
            product.save()
            return CreateProduct(product=product, success=True, errors=[])
        except ValidationError as e:
            field_errors = []
            if hasattr(e, 'message_dict'):
                for field, messages in e.message_dict.items():
                    for msg in messages:
                        field_errors.append(ErrorType(field=field, message=msg, code="VALIDATION_ERROR"))
            else:
                field_errors.append(ErrorType(message=str(e), code="VALIDATION_ERROR"))
            return CreateProduct(success=False, errors=field_errors)
        except Exception as e:
            return CreateProduct(success=False, errors=[
                ErrorType(field="general", message=f"An unexpected error occurred: {str(e)}", code="SERVER_ERROR")])


class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)
        order_date = graphene.DateTime()

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    errors = graphene.List(ErrorType)

    def mutate(self, info, customer_id, product_ids, order_date=None):
        validation_errors = []

        # 1. Resolve Global IDs
        local_customer_id = None
        try:
            _, local_customer_id = Node.from_global_id(customer_id)
        except Exception:
            validation_errors.append(
                ErrorType(field="customerId", message="Invalid customer ID format.", code="INVALID_ID_FORMAT"))
            # If customer ID is invalid, further processing is pointless. Return early.
            return CreateOrder(success=False, errors=validation_errors)

        local_product_ids = []
        for prod_global_id in product_ids:
            try:
                _, local_prod_id = Node.from_global_id(prod_global_id)
                local_product_ids.append(local_prod_id)
            except Exception:
                validation_errors.append(
                    ErrorType(field="productIds", message=f"Invalid product ID format for '{prod_global_id}'.",
                              code="INVALID_ID_FORMAT"))

        if validation_errors:  # Check for product ID format errors before proceeding
            return CreateOrder(success=False, errors=validation_errors)

        # 2. Validate existence of customer and products
        customer_obj = None
        try:
            customer_obj = Customer.objects.get(id=local_customer_id)
        except ObjectDoesNotExist:
            validation_errors.append(
                ErrorType(field="customerId", message=f"Customer with ID '{local_customer_id}' not found.",
                          code="CUSTOMER_NOT_FOUND"))

        if not local_product_ids:
            validation_errors.append(
                ErrorType(field="productIds", message="At least one product must be selected for the order.",
                          code="REQUIRED_FIELD"))

        product_objs = []
        total_amount = decimal.Decimal('0.00')

        # Use a single query to fetch all required products
        products_query_set = Product.objects.filter(id__in=local_product_ids)

        # Check if all unique requested product IDs were found
        # Convert IDs to string for consistent comparison if your local_product_ids are strings
        found_ids_set = {str(p.id) for p in products_query_set}
        for requested_id in local_product_ids:
            if str(requested_id) not in found_ids_set:
                validation_errors.append(
                    ErrorType(field="productIds", message=f"Product with ID '{requested_id}' not found.",
                              code="PRODUCT_NOT_FOUND"))
            else:
                # Add to product_objs and sum price only if it was actually found in the DB.
                # Avoid duplicates in total calculation if `product_ids` input had duplicates.
                # `products_query_set` will only contain unique product objects.
                pass  # We'll build product_objs correctly after validation_errors check

        # If any validation errors accumulated (including missing customer/products), return them
        if validation_errors:
            return CreateOrder(success=False, errors=validation_errors)

        # If we reach here, all customer and product IDs are valid and exist.
        # Now populate product_objs and calculate total_amount correctly based on unique products.
        seen_unique_product_ids_for_total = set()
        for prod_obj in products_query_set:
            product_objs.append(prod_obj)
            # Only add to total once for each unique product requested
            if prod_obj.id not in seen_unique_product_ids_for_total:
                total_amount += prod_obj.price
                seen_unique_product_ids_for_total.add(prod_obj.id)

        if order_date is None:
            order_date = timezone.now()

        with transaction.atomic():
            try:
                order = Order.objects.create(customer=customer_obj, total_amount=total_amount, order_date=order_date)
                order.products.set(product_objs)

                return CreateOrder(order=order, success=True, errors=[])
            except ValidationError as e:
                field_errors = []
                if hasattr(e, 'message_dict'):
                    for field, messages in e.message_dict.items():
                        for msg in messages:
                            field_errors.append(ErrorType(field=field, message=msg, code="VALIDATION_ERROR"))
                else:
                    field_errors.append(ErrorType(message=str(e), code="VALIDATION_ERROR"))
                return CreateOrder(success=False, errors=field_errors)
            except Exception as e:
                return CreateOrder(success=False, errors=[
                    ErrorType(field="general", message=f"An unexpected error occurred: {str(e)}", code="SERVER_ERROR")])


class UpdateLowStockProducts(graphene.Mutation):
    """
    Mutation to query products with stock < 10, increment their stock by 10,
    and return the updated products.
    """

    class Arguments:
        # No specific inputs required, as the logic is internal to find low-stock products.
        # You could add a 'threshold' or 'increment_by' argument if you wanted to make it dynamic.
        pass

    # Output fields
    updated_products = graphene.List(ProductType, description="List of products whose stock was updated.")
    message = graphene.String(description="A message indicating the outcome.")
    success = graphene.Boolean(description="True if the operation was successful, False otherwise.")
    errors = graphene.List(ErrorType, description="List of errors encountered.")

    def mutate(self, info):
        updated_products_list = []
        errors_list = []

        try:
            # 1. Query products with stock < 10
            # Used select_for_update() to lock these rows during the update transaction
            # to prevent race conditions if multiple processes tried to update simultaneously.
            # Bets for concurrent environments.
            low_stock_products_queryset = Product.objects.filter(stock__lt=10).select_for_update()

            if not low_stock_products_queryset.exists():
                return UpdateLowStockProducts(
                    updated_products=[],
                    message="No low-stock products found to update.",
                    success=True,
                    errors=[]
                )

            # 2. Perform the update in a database transaction
            with transaction.atomic():
                # Store IDs before updating, to fetch full objects later
                product_ids_to_update = [p.id for p in low_stock_products_queryset]

                # Bulk update: Used F() expression to update stock directly in the database
                # This is more efficient and atomic than fetching each object, modifying, and saving.
                updated_count = low_stock_products_queryset.update(stock=F('stock') + 10)

                # 3. Retrieve the updated products to return them
                # Used in_bulk for efficient retrieval of specific IDs
                updated_product_instances = Product.objects.filter(id__in=product_ids_to_update)

                # Convert to list of ProductType for GraphQL output
                updated_products_list = [ProductType(**p.__dict__) for p in updated_product_instances]

            return UpdateLowStockProducts(
                updated_products=updated_products_list,
                message=f"Successfully restocked {updated_count} low-stock products.",
                success=True,
                errors=[]
            )

        except Exception as e:
            errors_list.append(ErrorType(
                field="general",
                message=f"An error occurred during low-stock product update: {str(e)}",
                code="SERVER_ERROR"
            ))
            return UpdateLowStockProducts(
                updated_products=[],
                message="Failed to update low-stock products due to an error.",
                success=False,
                errors=errors_list
            )

# --- Root Query Class (Using DjangoFilterConnectionField) ---
class Query(graphene.ObjectType):
    """
    The root query class for fetching data from the CRM system,
    now supporting filtering and sorting via DjangoFilterConnectionField.
    """
    node = Node.Field()  # Essential for Relay Global IDs

    # Use DjangoFilterConnectionField for automatic filtering and pagination.
    # It automatically adds `filter` and `order_by` arguments, based on the filterset_class.
    all_customers = DjangoFilterConnectionField(
        CustomerType,
        filterset_class=CustomerFilter,  # Link to our CustomerFilter
        description="Retrieve all customers with filtering and sorting options."
    )
    all_products = DjangoFilterConnectionField(
        ProductType,
        filterset_class=ProductFilter,  # Link to our ProductFilter
        description="Retrieve all products with filtering and sorting options."
    )
    all_orders = DjangoFilterConnectionField(
        OrderType,
        filterset_class=OrderFilter,  # Link to our OrderFilter
        description="Retrieve all orders with filtering and sorting options."
    )

    # Note: We no longer need manual resolve_all_customers/products/orders methods
    # for these fields, as DjangoFilterConnectionField handles the query execution.
    # The default resolver simply returns the queryset from the associated model.



# --- Root Mutation Class (Same as previous solution) ---
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
    update_low_stock_products = UpdateLowStockProducts.Field(description="Updates stock for products with less than 10 units.")

