# properties/models.py
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from accounts.models import User, TimestampedModel, SoftDeleteModel


class Property(TimestampedModel, SoftDeleteModel):
    """Real estate property/project"""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('live', 'Live'),
        ('funding', 'Funding'),
        ('funded', 'Fully Funded'),
        ('under_construction', 'Under Construction'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
    ]

    PROPERTY_TYPE_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('land', 'Land'),
        ('mixed', 'Mixed Use'),
    ]

    # Created by developer
    developer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='developed_properties')

    # Property details
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    builder_name = models.CharField(max_length=255, help_text="Builder/Developer company name")

    property_type = models.CharField(
        max_length=20, choices=PROPERTY_TYPE_CHOICES)

    # Location
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    locality = models.CharField(max_length=200, blank=True, help_text="Area/Locality name")
    pincode = models.CharField(max_length=10)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)

    # Property specifications
    total_area = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="in sq ft")
    total_units = models.IntegerField(validators=[MinValueValidator(1)])
    available_units = models.IntegerField()

    # Pricing
    price_per_unit = models.DecimalField(max_digits=15, decimal_places=2)
    minimum_investment = models.DecimalField(max_digits=15, decimal_places=2)
    maximum_investment = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True)

    # Funding
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    funded_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'))

    # Returns
    expected_return_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, 
        help_text="Target IRR %")
    gross_yield = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Gross Yield %")
    potential_gain = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Potential Gain %")
    expected_return_period = models.IntegerField(
        help_text="in months", null=True, blank=True)

    # Tenure
    lock_in_period = models.IntegerField(help_text="in months", default=0)
    project_duration = models.IntegerField(help_text="in months")

    # Dates
    launch_date = models.DateField(null=True, blank=True)
    funding_start_date = models.DateField(null=True, blank=True)
    funding_end_date = models.DateField(null=True, blank=True)
    possession_date = models.DateField(null=True, blank=True)

    # Images & Media
    featured_image = models.ImageField(
        upload_to='properties/featured/', null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft')

    # Approval
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='approved_properties')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Features (JSON)
    amenities = models.JSONField(default=list, blank=True)
    highlights = models.JSONField(default=list, blank=True)

    # SEO
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    # Visibility
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    is_public_sale = models.BooleanField(
        default=True, 
        help_text="Available for public investment")
    is_presale = models.BooleanField(
        default=False, 
        help_text="Pre-launch/Early bird sale")

    class Meta:
        db_table = 'properties'
        verbose_name_plural = 'Properties'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['slug']),
            models.Index(fields=['developer']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['is_public_sale', 'is_presale']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def funding_percentage(self):
        """Calculate funding percentage"""
        if self.target_amount > 0:
            return (self.funded_amount / self.target_amount) * 100
        return 0

    @property
    def is_fully_funded(self):
        """Check if property is fully funded"""
        return self.funded_amount >= self.target_amount

    def update_funded_amount(self):
        """Recalculate funded amount from approved investments"""
        from investments.models import Investment
        total = Investment.objects.filter(
            property=self,
            status='approved'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        self.funded_amount = total
        self.save(update_fields=['funded_amount'])


class PropertyUnit(TimestampedModel):
    """Individual units within a property"""

    UNIT_STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('blocked', 'Blocked'),
    ]

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='units')

    unit_number = models.CharField(max_length=50)
    floor = models.IntegerField(null=True, blank=True)

    # Unit specs
    area = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="in sq ft")
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.IntegerField(null=True, blank=True)

    # Pricing (can be different from base property price)
    price = models.DecimalField(max_digits=15, decimal_places=2)

    # Status
    status = models.CharField(
        max_length=20, choices=UNIT_STATUS_CHOICES, default='available')

    # If reserved/sold
    reserved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='reserved_units')
    reserved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'property_units'
        unique_together = ('property', 'unit_number')
        indexes = [
            models.Index(fields=['property', 'status']),
        ]

    def __str__(self):
        return f"{self.property.name} - Unit {self.unit_number}"



import os
from django.utils.text import slugify
import uuid

def property_image_upload_path(instance, filename):
    """Generate upload path for property images"""
    ext = filename.split('.')[-1]
    # Create a clean filename
    property_slug = slugify(instance.property.name)
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{property_slug}-image-{unique_id}.{ext}"
    return os.path.join('properties/gallery', filename)


class PropertyImage(TimestampedModel):
    """Property images gallery"""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=property_image_upload_path)  # ← CHANGED
    caption = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'property_images'
        ordering = ['order']

    def __str__(self):
        return f"{self.property.name} - Image {self.id}"


def property_document_upload_path(instance, filename):
    """Generate upload path for property documents"""
    ext = filename.split('.')[-1]
    property_slug = slugify(instance.property.name)
    doc_type = instance.document_type
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{property_slug}-{doc_type}-{unique_id}.{ext}"
    return os.path.join('properties/documents', filename)


class PropertyDocument(TimestampedModel):
    """Legal and property documents"""

    DOCUMENT_TYPE_CHOICES = [
        ('prospectus', 'Prospectus'),
        ('legal', 'Legal Document'),
        ('approval', 'Government Approval'),
        ('plan', 'Floor Plan'),
        ('brochure', 'Brochure'),
        ('agreement', 'Agreement'),
        ('other', 'Other'),
    ]

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='documents')

    title = models.CharField(max_length=255)
    document_type = models.CharField(
        max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to=property_document_upload_path)  # ← CHANGED

    # Access control
    is_public = models.BooleanField(default=False)

    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'property_documents'

    def __str__(self):
        return f"{self.property.name} - {self.title}"



class PropertyInterest(TimestampedModel):
    """Track user interest in properties"""
    
    property = models.ForeignKey(
        Property, 
        on_delete=models.CASCADE, 
        related_name='interests'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='property_interests'
    )
    
    # Interest details
    token_count = models.IntegerField(default=1)
    message = models.TextField(blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('contacted', 'Contacted'),
        ('converted', 'Converted to Investment'),
        ('declined', 'Declined'),
    ]
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # Contact tracking
    contacted_at = models.DateTimeField(null=True, blank=True)
    contacted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='contacted_interests'
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'property_interests'
        unique_together = ('property', 'user')  # One interest per user per property
        indexes = [
            models.Index(fields=['property', 'status']),
            models.Index(fields=['user']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.property.name}"