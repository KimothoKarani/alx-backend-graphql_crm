from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.utils import timezone #For timezone-aware datetimes (Django best practice)
import decimal #For precise currency calculations

User = get_user_model()

#Custom phone number validation
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$|^\d{3}[-\s]?\d{3}[-\s]?\d{4}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed or '999-999-9999'."
)

# --- Customer Model ----
class Customer(models.Model):
    name = models.CharField(max_length=255)

    email = models.EmailField(
        unique=True,
        validators=[EmailValidator(message="Invalid email format.")],
    )

    phone = models.CharField(
        validators=[phone_regex], max_length=17, blank=True, null=True)

    # auto_now_add automatically sets the timestamp when the object is first created.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Automatically updates on every save

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def __str__(self):
        return self.name

    # Optional: Add custom clean method for more complex model-level validation
    # def clean(self):
    #     if "badword" in self.name.lower():
    #         raise ValidationError("Customer name contains a forbidden word.")
    #     super().clean() # Always call super().clean()


# --- Product Model ------
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(decimal_places=2, max_digits=10)
    stock = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.name

    def clean(self):
        '''
        Custom validation for Product Model
        '''
        if self.price <= 0:
            raise ValidationError({'price': 'Price must be greater than zero.'})
        if self.stock < 0:
            raise ValidationError({'stock': 'Stock cannot be less than zero.'})
        super().clean()

# ---- Order Model ----
class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                 related_name='orders')

    products = models.ManyToManyField(Product, related_name='orders')

    total_amount = models.DecimalField(decimal_places=2, max_digits=10,
                                       default=decimal.Decimal('0.00'))

    order_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-order_date',)
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"Order {self.id} by {self.customer.name}"

    # You might want to override save() or use a signal to calculate total_amount automatically
    # This ensures total_amount is consistent with current product prices.
    def save(self, *args, **kwargs):
        # Calculate total_amount *before* saving for the first time or if products change.
        # This requires products to be added/set *before* calling save() if it's a new order
        # or if the product set is modified. For simplicity in mutation, we'll calculate it
        # in the mutation itself. However, for robustness, doing it here is better.
        # This will be refined in the mutation logic.
        super().save(*args, **kwargs)

        # After saving, if products are added/removed, ensure total_amount is updated.
        # This can be triggered by a signal or explicit call in mutation.
        # For simplicity in this Graphene context, we will compute and pass total_amount
        # directly in the CreateOrder mutation.
