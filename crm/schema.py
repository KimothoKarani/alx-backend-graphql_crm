import graphene
from graphene_django import DjangoObjectType
from graphql.error import GraphQLError
import datetime
import decimal
import re


class InMemoryDataStore:
    _customers = []
    _products = []
    _orders = []

    # Counters to generate unique IDs for our records
    _next_customer_id = 1
    _next_product_id = 1
    _next_order_id = 1

    @classmethod
    def reset(cls):
        '''
        Resets all the data in the in-memory store. Useful for
        testing or re-seeding
        '''
        cls._customers = []
        cls._products = []
        cls._orders = []
        cls._next_customer_id = 1
        cls._next_product_id = 1
        cls._next_order_id = 1

    @classmethod
    def create_customer(cls, name, email, phone=None):
        '''
        Creates a new customer record and adds it to the store.
        IDs are stored as strings to match GraphQL String types.
        '''
        customer = {
            "id": str(cls._next_customer_id),
            "name": name,
            "email": email,
            "phone": phone,
        }

        cls._customers.append(customer)
        cls._next_customer_id += 1
        return customer

    @classmethod
    def get_customer_by_id(cls, customer_id):
        '''
        Retrieves a customer by its ID.
        next((...  for ... if ...), None) is a Pythonic way to find the
        first matching customer or return None if no match is found.
        '''
        cid = str(customer_id)
        for customer in cls._customers:
            if str(customer["id"]) == cid:
                return customer
        return None  # <-- return after the loop

    @classmethod
    def is_customer_email_unique(cls, email, exclude_customer_id=None):
        '''
        Checks whether a customer email is unique across all customers.
        'exclude_customer_id' is used when updating a customer to
        ignore their own email.
        '''
        exclude = str(exclude_customer_id) if exclude_customer_id is not None else None
        for customer in cls._customers:
            if customer["email"] == email and customer["id"] != exclude:
                return False
        return True  # <-- return after checking all

    @classmethod
    def create_product(cls, name, price, stock=0):
        '''
        Creates a new product record and adds it to the store.
        Price is stored as decimal for precision.
        '''

        product = {
            "id": str(cls._next_product_id),
            "name": name,
            "price": decimal.Decimal(str(price)), #Convert to Decimal for storage
            "stock": int(stock),
        }
        cls._products.append(product)
        cls._next_product_id += 1
        return product

    @classmethod
    def get_product_by_id(cls, product_id):
        '''
        Retrieves a product by its ID.
        '''

        pid = str(product_id)
        for product in cls._products:
            if str(product["id"]) == pid:
                return product
        return None  # <-- return after the loop

    @classmethod
    def create_order(cls, customer_id, product_id, total_amount, order_date=None):
        '''
        Creates a new order record and adds it to the store.
        '''

        if order_date is None:
            order_date = datetime.datetime.now(datetime.timezone.utc)
        order = {
            "id": str(cls._next_order_id),
            "customer_id": customer_id,
            "product_id": product_id,
            "total_amount": total_amount,
            "order_date": order_date,
        }
        cls._orders.append(order)
        cls._next_order_id += 1
        return order

    @classmethod
    def get_all_customers(cls):
        '''
        Retrieves all the customers in the store.
        '''
        return cls._customers

    @classmethod
    def get_all_products(cls):
        return cls._products

    @classmethod
    def get_all_orders(cls):
        '''
        Returns all order records, reconstructing, nested nested customer and
        product data for GraphQL's consumption.
        '''
        orders_with_details = []
        for order in cls._orders:
            customer = cls.get_customer_by_id(order['customer_id'])
            products_in_order = []
            #Fetch each product object based on its ID
            for prod_id in order['product_id']:
                product = cls.get_product_by_id(prod_id)
                if product:
                    products_in_order.append(product)

            # Create a copy of the order and add the full customer and product objects
            # This is important because Graphene expects these nested objects for OrderType
            order_copy = order.copy()
            order_copy["customer"] = customer
            order_copy["products"] = products_in_order
            orders_with_details.append(order_copy)
        return orders_with_details

# ---- 1. Gra[hQL Output Types (Define the shape of data clients receive)--------

class CustomerType(graphene.ObjectType):
    """
    Defines the structure of a Customer object for GraphQL queries and mutation outputs.
    Clients will see and query these fields.
    """
    id = graphene.String(description="Unique identifier for the customer.")
    name = graphene.String(description="The customer's full name.")
    email = graphene.String(description="The customer's email address (unique).")
    phone = graphene.String(description="The customer's phone number (optional).")

class ProductType(graphene.ObjectType):
    """
    Defines the structure of a Product object for GraphQL.
    """
    id = graphene.String(description="Unique identifier for the product.")
    name = graphene.String(description="The product's name.")
    price = graphene.Decimal(description="The product's price.")
    stock = graphene.Int(description="The quantity of this product in stock.")

class OrderType(graphene.ObjectType):
    """
    Defines the structure of an Order object for GraphQL.
    Includes nested CustomerType and a list of ProductType for detailed responses.
    """
    id = graphene.String(description="Unique identifier for the order.")
    customer = graphene.Field(CustomerType, description="The customer who placed this order.")
    products = graphene.List(ProductType, description="The list of products included in this order.")
    total_amount = graphene.Decimal(description="The calculated total amount of the order.")
    order_date = graphene.DateTime(description="The date and time the order was placed.")

# --- Custom Error Type (for structured error handling in mutation responses) ---
class ErrorType(graphene.ObjectType):
    """
    A reusable GraphQL type for returning specific error details.
    Allows for more granular error messages than just raising a top-level exception.
    """
    field = graphene.String(description="The specific input field that caused the error (e.g., 'email', 'price').")
    message = graphene.String(description="A user-friendly description of the error.")
    code = graphene.String(description="An optional machine-readable error code (e.g., 'INVALID_FORMAT', 'DUPLICATE_EMAIL').")

# --- 2. GraphQL Input Types (Define the shape of data clients send to mutations) ---

class CustomerInput(graphene.InputObjectType):
    """
    Defines the input structure for `CreateCustomer` and `BulkCreateCustomers` mutations.
    Clients will provide data conforming to this shape.
    """
    name = graphene.String(required=True, description="The customer's full name.")
    email = graphene.String(required=True, description="The customer's email address.")
    phone = graphene.String(description="The customer's phone number.")

class ProductInput(graphene.InputObjectType):
    """
    Defines the input structure for `CreateProduct` mutation.
    """
    name = graphene.String(required=True, description="The product's name.")
    price = graphene.Decimal(required=True, description="The product's price (must be positive).")
    stock = graphene.Int(default_value=0, description="The quantity of product in stock (cannot be negative).")

# --- 3. Mutations (Operations that modify data) ---

class CreateCustomer(graphene.Mutation):
    """
    Mutation to create a single Customer instance.
    Handles email uniqueness and phone format validation.
    """
    class Arguments:
        # 'input' is a single argument of type CustomerInput, encapsulating all customer details.
        input = CustomerInput(required=True)

    # Output fields for this mutation (what is returned upon success or structured failure)
    customer = graphene.Field(CustomerType, description="The customer object if successfully created.")
    message = graphene.String(description="A message indicating the outcome of the operation.")
    success = graphene.Boolean(description="True if the customer was created, False otherwise.")
    errors = graphene.List(ErrorType, description="A list of detailed errors if validation failed.")

    def mutate(self, info, input):
        # --- Validation Logic ---
        validation_errors = []

        # 1. Validate email format using a regular expression
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.fullmatch(email_regex, input.email):
            validation_errors.append(ErrorType(
                field="email",
                message="Invalid email format.",
                code="INVALID_FORMAT"
            ))

        # 2. Ensure email is unique in our data store
        if InMemoryDataStore.is_customer_email_unique(input.email) is False:
            validation_errors.append(ErrorType(
                field="email",
                message="Email already exists.",
                code="DUPLICATE_EMAIL"
            ))

        # 3. Validate phone format if provided
        if input.phone:
            # Simple phone regex: allows optional '+' then 10-15 digits, OR 3-3-4 digit format with hyphens.
            # For robust phone validation, a library like `phonenumbers` is recommended.
            phone_regex = r"^(\+\d{1,3})?\d{10,15}$|^\d{3}-\d{3}-\d{4}$"
            if not re.fullmatch(phone_regex, input.phone):
                validation_errors.append(ErrorType(
                    field="phone",
                    message="Invalid phone format. Expected: +1234567890 or 123-456-7890.",
                    code="INVALID_FORMAT"
                ))

        # If any validation errors occurred, return them immediately
        if validation_errors:
            return CreateCustomer(success=False, errors=validation_errors)

        # --- Business Logic (If validation passes, create the customer) ---
        customer_data = InMemoryDataStore.create_customer(
            name=input.name,
            email=input.email,
            phone=input.phone
        )

        # --- Return Success Response ---
        # We instantiate the mutation class and pass the data for its output fields.
        return CreateCustomer(
            customer=CustomerType(**customer_data), # Convert the customer dictionary to CustomerType
            message="Customer created successfully.",
            success=True,
            errors=[] # Empty list indicates no errors
        )

class BulkCreateCustomers(graphene.Mutation):
    """
    Mutation to create multiple customer instances in one request.
    Supports partial success: valid customers are created, errors are reported for failed ones.
    """
    class Arguments:
        # Takes a list of CustomerInput objects for bulk creation.
        input = graphene.List(CustomerInput, required=True)

    # Output fields for bulk operation
    customers = graphene.List(CustomerType, description="List of customers successfully created.")
    errors = graphene.List(ErrorType, description="List of errors for customers that failed creation.")
    success_count = graphene.Int(description="The number of customers successfully created.")

    def mutate(self, info, input):
        created_customers = [] # To store successfully created CustomerType instances
        errors_list = []       # To store ErrorType instances for failures
        success_count = 0

        # Regex for email and phone validation (repeated for clarity within this mutation)
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        phone_regex = r"^(\+\d{1,3})?\d{10,15}$|^\d{3}-\d{3}-\d{4}$"

        # Keep track of emails encountered within this batch to ensure uniqueness
        # *within* the bulk upload itself, in addition to existing data.
        emails_in_current_batch = set()

        # Iterate through each customer data dictionary in the input list
        for i, customer_input in enumerate(input):
            item_errors = [] # Errors specific to the current customer in the loop

            # Validate name presence (though Graphene handles required=True for InputType)
            if not customer_input.name:
                 item_errors.append(ErrorType(
                    field=f"input[{i}].name",
                    message=f"Customer at index {i} has no name.",
                    code="REQUIRED_FIELD"
                ))

            # Validate email format
            if not re.fullmatch(email_regex, customer_input.email):
                item_errors.append(ErrorType(
                    field=f"input[{i}].email", # Indicate which item in the list has the error
                    message=f"Customer at index {i}: Invalid email format.",
                    code="INVALID_FORMAT"
                ))
            # Validate email uniqueness against existing data AND within the current batch
            if not InMemoryDataStore.is_customer_email_unique(customer_input.email) or \
               customer_input.email in emails_in_current_batch:
                item_errors.append(ErrorType(
                    field=f"input[{i}].email",
                    message=f"Customer at index {i}: Email already exists or is a duplicate within this batch.",
                    code="DUPLICATE_EMAIL"
                ))
            else:
                emails_in_current_batch.add(customer_input.email) # Add to set if unique so far

            # Validate phone format if provided
            if customer_input.phone:
                if not re.fullmatch(phone_regex, customer_input.phone):
                    item_errors.append(ErrorType(
                        field=f"input[{i}].phone",
                        message=f"Customer at index {i}: Invalid phone format.",
                        code="INVALID_FORMAT"
                    ))

            # If this specific customer record has errors, add them to the main errors list
            # and skip creating this customer, then move to the next in the batch.
            if item_errors:
                errors_list.extend(item_errors)
                continue # Skip to the next customer in the loop

            # If all validations pass for this customer, create it
            try:
                customer_data = InMemoryDataStore.create_customer(
                    name=customer_input.name,
                    email=customer_input.email,
                    phone=customer_input.phone
                )
                created_customers.append(CustomerType(**customer_data)) # Add to successes
                success_count += 1
            except Exception as e:
                # Catch any unexpected errors during the actual creation process
                errors_list.append(ErrorType(
                    field=f"input[{i}].general",
                    message=f"Customer at index {i}: An unexpected error occurred during creation: {str(e)}",
                    code="INTERNAL_ERROR"
                ))

        # Return the collected results of the bulk operation
        return BulkCreateCustomers(
            customers=created_customers,
            errors=errors_list,
            success_count=success_count
        )

class CreateProduct(graphene.Mutation):
    """
    Mutation to create a single Product instance.
    Includes validation for price (positive) and stock (non-negative).
    """
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType, description="The product object if successfully created.")
    success = graphene.Boolean(description="True if the product was created, False otherwise.")
    errors = graphene.List(ErrorType, description="A list of detailed errors if validation failed.")

    def mutate(self, info, input):
        validation_errors = []

        # --- Validation Logic ---
        # 1. Ensure price is positive
        # input.price is already a decimal.Decimal due to graphene.Decimal type
        if input.price <= 0:
            validation_errors.append(ErrorType(
                field="price",
                message="Price must be a positive value.",
                code="INVALID_VALUE"
            ))

        # 2. Ensure stock is non-negative
        if input.stock < 0:
            validation_errors.append(ErrorType(
                field="stock",
                message="Stock cannot be negative.",
                code="INVALID_VALUE"
            ))

        if validation_errors:
            return CreateProduct(success=False, errors=validation_errors)

        # --- Business Logic ---
        product_data = InMemoryDataStore.create_product(
            name=input.name,
            price=input.price,
            stock=input.stock
        )

        # --- Return Success ---
        return CreateProduct(
            product=ProductType(**product_data),
            success=True,
            errors=[]
        )

class CreateOrder(graphene.Mutation):
    """
    Mutation to create an Order instance.
    Handles nested order creation with product associations,
    and robust validation for customer and product IDs.
    Calculates total_amount automatically.
    """
    class Arguments:
        customer_id = graphene.String(required=True, description="The ID of the customer placing the order.")
        # product_ids is a list of product IDs (strings)
        product_ids = graphene.List(graphene.String, required=True, description="A list of product IDs to include in the order.")
        order_date = graphene.DateTime(description="Optional order date, defaults to current time if not provided.")

    order = graphene.Field(OrderType, description="The created order object with nested customer and product data.")
    success = graphene.Boolean(description="True if the order was created, False otherwise.")
    errors = graphene.List(ErrorType, description="A list of detailed errors if validation failed.")

    def mutate(self, info, customer_id, product_ids, order_date=None):
        validation_errors = []

        # --- Validation Logic ---
        # 1. Validate customer_id: Must exist in our store
        customer = InMemoryDataStore.get_customer_by_id(customer_id)
        if not customer:
            validation_errors.append(ErrorType(
                field="customerId",
                message=f"Customer with ID '{customer_id}' not found.",
                code="CUSTOMER_NOT_FOUND"
            ))

        # 2. Ensure at least one product is selected
        if not product_ids:
            validation_errors.append(ErrorType(
                field="productIds",
                message="At least one product must be selected for the order.",
                code="REQUIRED_FIELD"
            ))

        # 3. Validate product_ids: All must exist and calculate total_amount
        products_for_order = []
        total_amount = decimal.Decimal('0.00')
        # Use a set to track product IDs already processed in this order to catch duplicates within the list
        seen_product_ids = set()

        for prod_id in product_ids:
            if prod_id in seen_product_ids:
                validation_errors.append(ErrorType(
                    field="productIds",
                    message=f"Duplicate product ID '{prod_id}' found in order.",
                    code="DUPLICATE_PRODUCT"
                ))
                continue # Skip this duplicate and continue processing other products

            product = InMemoryDataStore.get_product_by_id(prod_id)
            if not product:
                validation_errors.append(ErrorType(
                    field="productIds",
                    message=f"Product with ID '{prod_id}' not found.",
                    code="PRODUCT_NOT_FOUND"
                ))
            else:
                products_for_order.append(product)
                total_amount += product["price"] # Summing up prices
                seen_product_ids.add(prod_id) # Add to seen set

        # If any validation errors accumulated, return them
        if validation_errors:
            return CreateOrder(success=False, errors=validation_errors)

        # If order_date is not provided, default to current UTC time
        if order_date is None:
            order_date = datetime.datetime.now(datetime.timezone.utc)

        # --- Business Logic ---
        # Create the order in the data store, storing just customer and product IDs internally
        order_data = InMemoryDataStore.create_order(
            customer_id=customer_id,
            product_ids=[p["id"] for p in products_for_order], # Store only IDs in the raw order data
            total_amount=total_amount,
            order_date=order_date
        )

        # --- Return Created Order with Nested Data ---
        # For the GraphQL response, we need to return the full CustomerType and ProductType objects.
        return CreateOrder(
            order=OrderType(
                id=order_data["id"],
                customer=CustomerType(**customer), # Pass the fetched customer dictionary converted to CustomerType
                products=[ProductType(**p) for p in products_for_order], # Convert fetched product dictionaries to ProductType
                total_amount=order_data["total_amount"],
                order_date=order_data["order_date"]
            ),
            success=True,
            errors=[]
        )

# --- Root Query Class (for fetching data - added for completeness/testing) ---
# This allows you to query the data you've created via mutations.
class Query(graphene.ObjectType):
    """
    The root query class for fetching data from the CRM system.
    """
    # Define query fields that return lists of our types
    all_customers = graphene.List(CustomerType, description="Retrieve all customers.")
    all_products = graphene.List(ProductType, description="Retrieve all products.")
    all_orders = graphene.List(OrderType, description="Retrieve all orders with nested customer and product data.")

    # Resolver methods for each query field
    def resolve_all_customers(self, info):
        # Convert raw customer dictionaries from data store into CustomerType instances
        return [CustomerType(**c) for c in InMemoryDataStore.get_all_customers()]

    def resolve_all_products(self, info):
        # Convert raw product dictionaries from data store into ProductType instances
        return [ProductType(**p) for p in InMemoryDataStore.get_all_products()]

    def resolve_all_orders(self, info):
        # The InMemoryDataStore.get_all_orders method already prepares nested data.
        # We just need to convert these prepared dictionaries into Graphene's OrderType.
        orders_data = InMemoryDataStore.get_all_orders()
        graphene_orders = []
        for order_data in orders_data:
            # Reconstruct OrderType, ensuring nested customer and product lists are also Graphene types
            graphene_orders.append(
                OrderType(
                    id=order_data["id"],
                    # Check if customer exists (could be None if ID was invalid)
                    customer=CustomerType(**order_data["customer"]) if order_data["customer"] else None,
                    # Convert each product dictionary in the list to ProductType
                    products=[ProductType(**p) for p in order_data["products"]],
                    total_amount=order_data["total_amount"],
                    order_date=order_data["order_date"]
                )
            )
        return graphene_orders

# --- 4. Root Mutation Class (Combines all defined mutations) ---
class Mutation(graphene.ObjectType):
    """
    The root mutation class that exposes all available mutations for the CRM system.
    """
    create_customer = CreateCustomer.Field(description="Creates a new customer.")
    bulk_create_customers = BulkCreateCustomers.Field(description="Creates multiple customers in a single request.")
    create_product = CreateProduct.Field(description="Creates a new product.")
    create_order = CreateOrder.Field(description="Creates a new order, associating it with customers and products.")


# schema = graphene.Schema(query=Query, mutation=Mutation)