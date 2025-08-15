import django_filters
from django.db.models import Q
import re

from .models import Customer, Product, Order

# ---- CustomerFilter ------
class CustomerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text="Case-insensitive partial match for customer email.",
    )

    created_at = django_filters.DateFromToRangeFilter(
        help_text="Filter customers by creation date range (YYYY-MM-DD).",
    )

    phone_pattern = django_filters.CharFilter(
        method='filter_phone_pattern',
        help_text="Filter customers whose phone number matches a regex pattern (e.g., '^\\+1').",

    )

    class Meta:
        model = Customer
        fields = ['name', 'email', 'created_at']

    def filter_phone_pattern(self, queryset, name, value):
        """
        Custom method to filter customers by a regex pattern in their phone number.
        The 'value' argument will be the regex string provided by the client.
        """
        # __regex is a Django ORM lookup for regular expressions.
        # It's case-sensitive by default, use __iregex for case-insensitive.
        if value: # Only apply if a pattern is provided
            try:
                # Ensure the regex pattern is valid before attempting to query.
                # Re.compile will raise an error if the pattern is malformed.
                re.compile(value)
                return queryset.filter(phone__isnull=False, phone__regex=value)
            except re.error as e:
                # In a real API, we will log this or return a GraphQL error.
                # For now, we'll return an empty queryset or raise a GraphQLError in schema.py
                raise Exception('Invalid phone number "%s": %s' % (value, e))
        return queryset # If no value, return the original queryset

# ---- ProductFilter -----
class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text="Case-insensitive partial match for product name.",
    )
    price = django_filters.RangeFilter(
        help_text="Filter products by price range."
        # Automatically handles price_min, price_max
    )
    stock = django_filters.RangeFilter(
        help_text="Filter products by stock price."
        # Automatically handles stock_min, stock_max
    )

    low_stock = django_filters.BooleanFilter(
        method='filter_low_stock',
        help_text="If true, filters products with stock less than 10."
    )

    class Meta:
        model = Product
        fields = ['name', 'price', 'stock']

    def filter_low_stock(self, queryset, name, value):
        """
        Custom method to filter products with stock less than a defined threshold (e.g., 10).
        """
        if value:  # If 'low_stock' argument is true
            return queryset.filter(stock__lt=10)  # __lt means "less than"
        return queryset


# --- OrderFilter ---
class OrderFilter(django_filters.FilterSet):
    """
    FilterSet for the Order model.
    """
    total_amount = django_filters.RangeFilter(help_text="Filter orders by total amount range.")
    order_date = django_filters.DateFromToRangeFilter(help_text="Filter orders by order date range (YYYY-MM-DD).")

    # Filtering by related fields: customer's name
    # field_name='customer__name' tells Django to look at the 'name' field of the 'customer' relationship.
    customer_name = django_filters.CharFilter(
        field_name='customer__name',
        lookup_expr='icontains',
        help_text="Case-insensitive partial match for the customer's name."
    )

    # Filtering by related fields: product's name (Many-to-Many relationship)
    # __name: looks at the 'name' field of any product related to the order.
    product_name = django_filters.CharFilter(
        field_name='products__name',
        lookup_expr='icontains',
        help_text="Case-insensitive partial match for product names included in the order."
    )

    # Challenge: Allow filtering orders that include a specific product ID.
    # We use a MethodFilter here because we might want to check if *any* product in the order matches.
    product_id = django_filters.CharFilter(
        method='filter_by_product_id',
        help_text="Filter orders that include a specific product ID."
    )

    class Meta:
        model = Order
        fields = ['total_amount', 'order_date']

    def filter_by_product_id(self, queryset, name, value):
        """
        Custom method to filter orders that contain a product with the given ID.
        """
        if value:
            # products__id__exact filters orders where one of their related products has that ID.
            return queryset.filter(products__id__exact=value)
        return queryset
