import graphene
import datetime
import decimal
import re
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import EmailValidator
# Import Django's specific exceptions
from django.db import IntegrityError, transaction
from django.db.models import Q #For complex queries
from graphene import relay
from graphene_django.types import DjangoObjectType
from graphene.relay import Node # For Relay Global IDs if using Node interface
from graphene_django.filter import DjangoFilterConnectionField
from django.utils import timezone  # FIXED: Added missing import for timezone

# Import the Django models
from .models import Customer, Product, Order

# --- 1. GraphQL Output Types (Leveraging DjangoObjectType) ---
class CustomerType(DjangoObjectType):

    class Meta:
        model = Customer
        fields = '__all__'
        # Interfaces with Relay Node for global IDs, which is good practice.
        interfaces = (Node,)

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = '__all__'
        interfaces = (Node,)

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = '__all__'
        interfaces = (Node,)

# --- Custom Error Type (Remains the same, as it's a generic GraphQL structure) ---
class ErrorType(graphene.ObjectType):
    field = graphene.String(description="The specific input field that caused the error.")
    message = graphene.String(description="A user-friendly description of the error.")
    code = graphene.String(description="An optional machine-readable error code (e.g., 'INVALID_FORMAT', 'DUPLICATE_EMAIL').")

# --- 2. GraphQL Input Types (Remains the same, as these define API input shapes) ---
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True, description="The customer's full name.")
    email = graphene.String(required=True, description="The customer's email address.")
    phone = graphene.String(description="The customer's phone number.")

class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True, description="The product's name.")
    price = graphene.Decimal(required=True, description="The product's price (must be positive).")
    stock = graphene.Int(default_value=0, description="The quantity of product in stock (cannot be negative).")


# --- 3. Mutations (Adapted to use Django ORM) ---

class CreateCustomer(graphene.Mutation):
    """
    Mutation to create a single Customer instance using Django ORM.
    Handles validation errors from Django's model and custom regex.
    """

    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType, description="The customer object if successfully created.")
    message = graphene.String(description="A message indicating the outcome of the operation.")
    success = graphene.Boolean(description="True if the customer was created, False otherwise.")
    errors = graphene.List(ErrorType, description="A list of detailed errors if validation failed.")

    def mutate(self, info, input):
        validation_errors = []

        # Phone format validation (still a good idea here for immediate feedback)
        phone_regex_pattern = r"^(\+\d{1,3})?\d{10,15}$|^\d{3}[-\s]?\d{3}[-\s]?\d{4}$"
        if input.phone and not re.fullmatch(phone_regex_pattern, input.phone):
            validation_errors.append(ErrorType(
                field="phone",
                message="Invalid phone format. Expected: +1234567890 or 123-456-7890.",
                code="INVALID_FORMAT"
            ))

        if validation_errors:
            return CreateCustomer(success=False, errors=validation_errors)

        try:
            # Create the customer using Django ORM
            customer = Customer.objects.create(
                name=input.name,
                email=input.email,  # Django's EmailField and unique=True will handle email validity and uniqueness
                phone=input.phone
            )
            # You might call customer.full_clean() here to run all model validators
            customer.full_clean()
            # customer.save() # If not using .create(), you'd save after full_clean()

            return CreateCustomer(
                customer=customer,  # DjangoObjectType automatically serializes the model instance
                message="Customer created successfully.",
                success=True,
                errors=[]
            )
        except IntegrityError:
            # This catches unique constraint errors (e.g., duplicate email)
            return CreateCustomer(
                success=False,
                errors=[ErrorType(field="email", message="Email already exists.", code="DUPLICATE_EMAIL")]
            )
        except ValidationError as e:
            # Catches validation errors from Django model fields (like EmailValidator)
            # and potentially from model's clean() method.
            field_errors = []
            if hasattr(e, 'message_dict'):
                for field, messages in e.message_dict.items():
                    for msg in messages:
                        field_errors.append(ErrorType(field=field, message=msg, code="VALIDATION_ERROR"))
            else:  # For non-field errors
                field_errors.append(ErrorType(message=str(e), code="VALIDATION_ERROR"))
            return CreateCustomer(success=False, errors=field_errors)
        except Exception as e:
            # Catch any other unexpected errors during creation
            return CreateCustomer(
                success=False,
                errors=[
                    ErrorType(field="general", message=f"An unexpected error occurred: {str(e)}", code="SERVER_ERROR")]
            )


class BulkCreateCustomers(graphene.Mutation):
    """
    Mutation for bulk creation of Customer instances.
    Leverages Django's bulk_create for efficiency.
    Handles individual validation and partial success.
    """

    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType, description="List of customers successfully created.")
    errors = graphene.List(ErrorType, description="List of errors for customers that failed creation.")
    success_count = graphene.Int(description="The number of customers successfully created.")

    def mutate(self, info, input):
        customers_to_create = []  # List to hold Django Customer model instances (not yet saved)
        errors_list = []
        success_count = 0

        # Regex for phone validation (EmailField handles basic email format)
        phone_regex_pattern = r"^(\+\d{1,3})?\d{10,15}$|^\d{3}[-\s]?\d{3}[-\s]?\d{4}$"

        # Keep track of emails encountered within this batch to ensure uniqueness
        # *within* the bulk upload itself, in addition to existing data.
        emails_in_current_batch = set()

        for i, customer_input_data in enumerate(input):
            item_errors = []

            # 1. Basic field presence/type validation (Graphene handles 'required=True' typically)
            if not customer_input_data.name:
                item_errors.append(ErrorType(field=f"input[{i}].name", message=f"Customer at index {i} has no name.",
                                             code="REQUIRED_FIELD"))
            if not customer_input_data.email:
                item_errors.append(ErrorType(field=f"input[{i}].email", message=f"Customer at index {i} has no email.",
                                             code="REQUIRED_FIELD"))

            # 2. Validate email format (Django's EmailField validates on save, but pre-check helps)
            try:
                EmailValidator(message="Invalid email format.")(customer_input_data.email)
            except ValidationError:
                item_errors.append(
                    ErrorType(field=f"input[{i}].email", message=f"Customer at index {i}: Invalid email format.",
                              code="INVALID_FORMAT"))

            # 3. Validate email uniqueness against existing DB data AND within the current batch
            if Customer.objects.filter(email=customer_input_data.email).exists() or \
                    customer_input_data.email in emails_in_current_batch:
                item_errors.append(ErrorType(field=f"input[{i}].email",
                                             message=f"Customer at index {i}: Email already exists or is a duplicate within this batch.",
                                             code="DUPLICATE_EMAIL"))
            else:
                emails_in_current_batch.add(customer_input_data.email)  # Add to set if unique so far

            # 4. Validate phone format if provided
            if customer_input_data.phone:
                if not re.fullmatch(phone_regex_pattern, customer_input_data.phone):
                    item_errors.append(
                        ErrorType(field=f"input[{i}].phone", message=f"Customer at index {i}: Invalid phone format.",
                                  code="INVALID_FORMAT"))

            # If this specific customer record has errors, add them to the main errors list
            # and skip creating this customer, then move to the next in the batch.
            if item_errors:
                errors_list.extend(item_errors)
                continue

            # If all validations pass for this customer, create a Django model instance (don't save yet)
            customers_to_create.append(
                Customer(
                    name=customer_input_data.name,
                    email=customer_input_data.email,
                    phone=customer_input_data.phone
                )
            )

        # Use a database transaction for bulk_create to ensure atomicity for the valid ones.
        # If any bulk_create fails (e.g., due to DB-level constraint not caught above), it rolls back.
        with transaction.atomic():
            created_instances = Customer.objects.bulk_create(customers_to_create, ignore_conflicts=True)
            # `ignore_conflicts=True` will skip objects that violate unique constraints,
            # but doesn't tell us *which* ones were skipped directly from the return value.
            # We already handled duplicate emails in Python logic above, which is better for feedback.

            # The `created_instances` list will contain the objects that were actually created.
            success_count = len(created_instances)

            # FIXED: For the output, we return the Django instances directly (DjangoObjectType handles conversion)
            created_customers = created_instances

        return BulkCreateCustomers(
            customers=created_customers,
            errors=errors_list,  # Errors from pre-validation
            success_count=success_count
        )


class CreateProduct(graphene.Mutation):
    """
    Mutation to create a single Product instance using Django ORM.
    Handles validation from Django model's clean method.
    """

    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType, description="The product object if successfully created.")
    success = graphene.Boolean(description="True if the product was created, False otherwise.")
    errors = graphene.List(ErrorType, description="A list of detailed errors if validation failed.")

    def mutate(self, info, input):
        try:
            # Create a Product instance
            product = Product(
                name=input.name,
                price=input.price,
                stock=input.stock
            )
            # Call full_clean() to run all model validation (field validators and clean() method)
            product.full_clean()
            product.save()  # Save to the database

            return CreateProduct(
                product=product,  # DjangoObjectType automatically serializes the model instance
                success=True,
                errors=[]
            )
        except ValidationError as e:
            # Catch validation errors from the model
            field_errors = []
            if hasattr(e, 'message_dict'):
                for field, messages in e.message_dict.items():
                    for msg in messages:
                        field_errors.append(ErrorType(field=field, message=msg, code="VALIDATION_ERROR"))
            else:
                field_errors.append(ErrorType(message=str(e), code="VALIDATION_ERROR"))
            return CreateProduct(success=False, errors=field_errors)
        except Exception as e:
            return CreateProduct(
                success=False,
                errors=[
                    ErrorType(field="general", message=f"An unexpected error occurred: {str(e)}", code="SERVER_ERROR")]
            )


class CreateOrder(graphene.Mutation):
    """
    Mutation to create an Order instance with nested customer and product associations.
    Uses Django ORM for fetching and creating.
    """

    class Arguments:
        customer_id = graphene.ID(required=True,
                                  description="The Global ID of the customer placing the order.")  # Use graphene.ID
        product_ids = graphene.List(graphene.ID, required=True,
                                    description="A list of Global IDs of products to include in the order.")  # Use graphene.ID
        order_date = graphene.DateTime(description="Optional order date, defaults to current time.")

    order = graphene.Field(OrderType, description="The created order object with nested customer and product data.")
    success = graphene.Boolean(description="True if the order was created, False otherwise.")
    errors = graphene.List(ErrorType, description="A list of detailed errors if validation failed.")

    def mutate(self, info, customer_id, product_ids, order_date=None):
        validation_errors = []

        # 1. Resolve Global IDs to actual Django model IDs (integers)
        try:
            # Node.from_global_id converts the GraphQL Global ID (e.g., "Customer:1")
            # into a tuple (type_name, id). We only need the ID.
            _, local_customer_id = Node.from_global_id(customer_id)
            local_customer_id = int(local_customer_id)  # FIXED: Ensure it's an integer
        except Exception:
            validation_errors.append(
                ErrorType(field="customerId", message="Invalid customer ID format.", code="INVALID_ID_FORMAT"))
            return CreateOrder(success=False, errors=validation_errors)

        local_product_ids = []
        for prod_global_id in product_ids:
            try:
                _, local_prod_id = Node.from_global_id(prod_global_id)
                local_product_ids.append(int(local_prod_id))  # FIXED: Ensure it's an integer
            except Exception:
                validation_errors.append(
                    ErrorType(field="productIds", message=f"Invalid product ID format for '{prod_global_id}'.",
                              code="INVALID_ID_FORMAT"))
                # Don't break loop, collect all ID format errors

        if validation_errors:
            return CreateOrder(success=False, errors=validation_errors)

        # 2. Validate customer and products existence using Django ORM
        customer_obj = None
        try:
            customer_obj = Customer.objects.get(id=local_customer_id)
        except ObjectDoesNotExist:
            validation_errors.append(
                ErrorType(field="customerId", message=f"Customer with ID '{local_customer_id}' not found.",
                          code="CUSTOMER_NOT_FOUND"))

        # Ensure at least one product is selected
        if not local_product_ids:
            validation_errors.append(
                ErrorType(field="productIds", message="At least one product must be selected for the order.",
                          code="REQUIRED_FIELD"))

        # Fetch all products at once
        product_objs = []
        total_amount = decimal.Decimal('0.00')

        # Using a Q object for an OR query (id=id1 OR id=id2...)
        # This is more efficient than looping and calling .get() for each.
        products_query_set = Product.objects.filter(id__in=local_product_ids)
        if len(products_query_set) != len(set(local_product_ids)):  # Check if all requested unique products were found
            found_ids = {p.id for p in products_query_set}  # FIXED: Compare integers to integers
            missing_ids = [pid for pid in local_product_ids if pid not in found_ids]
            for missing_id in missing_ids:
                validation_errors.append(
                    ErrorType(field="productIds", message=f"Product with ID '{missing_id}' not found.",
                              code="PRODUCT_NOT_FOUND"))

        # Populate product_objs and calculate total_amount based on fetched products
        for prod_obj in products_query_set:
            product_objs.append(prod_obj)
            total_amount += prod_obj.price

        # If any validation errors accumulated, return them
        if validation_errors:
            return CreateOrder(success=False, errors=validation_errors)

        # Set order date
        if order_date is None:
            order_date = timezone.now()  # FIXED: Use Django's timezone-aware now

        # Use a transaction for atomic order creation and product association
        with transaction.atomic():
            try:
                # Create the order instance
                order = Order.objects.create(
                    customer=customer_obj,
                    total_amount=total_amount,
                    order_date=order_date
                )
                # Associate products with the order (ManyToMany relationship)
                order.products.set(product_objs)  # .set() replaces existing products with the new set
                # For adding to existing, use .add() method: order.products.add(*product_objs)

                return CreateOrder(
                    order=order,  # DjangoObjectType will automatically serialize this
                    success=True,
                    errors=[]
                )
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
                return CreateOrder(
                    success=False,
                    errors=[ErrorType(field="general", message=f"An unexpected error occurred: {str(e)}",
                                      code="SERVER_ERROR")]
                )


# --- Root Query Class (Now querying Django Models) ---
class Query(graphene.ObjectType):
    """
    The root query class for fetching data from the CRM system.
    """
    node = Node.Field()  # Essential for Relay Global IDs

    # Query fields now directly return lists of Django model instances
    # Graphene-Django's DjangoObjectType handles the conversion automatically.
    all_customers = graphene.List(CustomerType, description="Retrieve all customers.")
    all_products = graphene.List(ProductType, description="Retrieve all products.")
    all_orders = graphene.List(OrderType, description="Retrieve all orders.")

    def resolve_all_customers(self, info):
        # Simply return all customer objects from the database
        return Customer.objects.all()

    def resolve_all_products(self, info):
        # Simply return all product objects from the database
        return Product.objects.all()

    def resolve_all_orders(self, info):
        # Simply return all order objects from the database
        return Order.objects.all()


# --- Root Mutation Class (Same structure, but methods are ORM-based) ---
class Mutation(graphene.ObjectType):
    """
    The root mutation class that exposes all available mutations for the CRM system.
    """
    create_customer = CreateCustomer.Field(description="Creates a new customer.")
    bulk_create_customers = BulkCreateCustomers.Field(description="Creates multiple customers in a single request.")
    create_product = CreateProduct.Field(description="Creates a new product.")
    create_order = CreateOrder.Field(description="Creates a new order, associating it with customers and products.")
