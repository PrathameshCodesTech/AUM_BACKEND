"""
Property Admin Serializers
For admin dashboard property management
"""
from rest_framework import serializers
from .models import Property, PropertyImage, PropertyDocument, PropertyUnit
from django.contrib.auth import get_user_model

User = get_user_model()


# ========================================
# HELPER SERIALIZERS
# ========================================

class PropertyImageSerializer(serializers.ModelSerializer):
    """Serializer for property images"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'image_url', 'caption', 'order', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class PropertyDocumentSerializer(serializers.ModelSerializer):
    """Serializer for property documents"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyDocument
        fields = [
            'id', 
            'title', 
            'document_type', 
            'file', 
            'file_url',
            'is_public', 
            'uploaded_by',
            'created_at'
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class PropertyUnitSerializer(serializers.ModelSerializer):
    """Serializer for property units"""
    reserved_by_name = serializers.CharField(source='reserved_by.username', read_only=True)
    
    class Meta:
        model = PropertyUnit
        fields = [
            'id',
            'unit_number',
            'floor',
            'area',
            'bedrooms',
            'bathrooms',
            'price',
            'status',
            'reserved_by',
            'reserved_by_name',
            'reserved_at',
            'created_at'
        ]


# ========================================
# LIST SERIALIZER (Enhanced with All Important Fields)
# ========================================

class AdminPropertyListSerializer(serializers.ModelSerializer):
    """Enhanced serializer for listing properties in admin dashboard"""
    
    # Calculated fields
    units_sold = serializers.SerializerMethodField()
    units_available = serializers.IntegerField(source='available_units')
    total_investment = serializers.SerializerMethodField()
    funding_percentage = serializers.SerializerMethodField()
    is_fully_funded = serializers.SerializerMethodField()
    
    # Related fields
    developer_name = serializers.CharField(source='developer.username', read_only=True)
    developer_email = serializers.EmailField(source='developer.email', read_only=True)
    
    # Image
    featured_image_url = serializers.SerializerMethodField()
    
    # Formatted values
    total_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = [
            # Basic Info
            'id',
            'name',
            'slug',
            'builder_name',
            'property_type',
            
            # Location
            'address',
            'city',
            'state',
            'locality',
            'pincode',
            
            # Units & Pricing
            'total_units',
            'units_available',
            'units_sold',
            'price_per_unit',
            'total_value',
            'minimum_investment',
            'maximum_investment',
            
            # Funding
            'target_amount',
            'funded_amount',
            'total_investment',
            'funding_percentage',
            'is_fully_funded',
            
            # Returns
            'expected_return_percentage',
            'gross_yield',
            'potential_gain',
            'expected_return_period',
            
            # Tenure
            'lock_in_period',
            'project_duration',
            
            # Dates
            'launch_date',
            'funding_start_date',
            'funding_end_date',
            'possession_date',
            
            # Status & Visibility
            'status',
            'is_featured',
            'is_published',
            'is_public_sale',
            'is_presale',
            
            # Developer
            'developer',
            'developer_name',
            'developer_email',
            
            # Media
            'featured_image_url',
            
            # Timestamps
            'created_at',
            'updated_at',
        ]
    
    def get_units_sold(self, obj):
        """Calculate units sold"""
        return obj.total_units - obj.available_units
    
    def get_total_investment(self, obj):
        """Calculate total investment received"""
        from investments.models import Investment
        from django.db.models import Sum
        
        total = Investment.objects.filter(
            property=obj,
            status='approved'
        ).aggregate(total=Sum('amount'))['total']
        
        return str(total or 0)
    
    def get_funding_percentage(self, obj):
        """Get funding percentage using model property"""
        return round(obj.funding_percentage, 2)
    
    def get_is_fully_funded(self, obj):
        """Check if fully funded using model property"""
        return obj.is_fully_funded
    
    def get_total_value(self, obj):
        """Calculate total property value"""
        return str(obj.price_per_unit * obj.total_units)
    
    def get_featured_image_url(self, obj):
        """Get featured image URL"""
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None


# ========================================
# DETAIL SERIALIZER (Complete with All Relationships)
# ========================================

class AdminPropertyDetailSerializer(serializers.ModelSerializer):
    """Complete detailed property info for admin"""
    
    # Calculated fields
    units_sold = serializers.SerializerMethodField()
    funding_percentage = serializers.SerializerMethodField()
    is_fully_funded = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()
    
    # Related data
    developer_details = serializers.SerializerMethodField()
    approved_by_details = serializers.SerializerMethodField()
    investment_stats = serializers.SerializerMethodField()
    
    # Nested relationships
    images = PropertyImageSerializer(many=True, read_only=True)
    documents = PropertyDocumentSerializer(many=True, read_only=True)
    units = PropertyUnitSerializer(many=True, read_only=True)
    
    # Image URL
    featured_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = [
            # IDs
            'id',
            
            # Basic Info
            'name',
            'slug',
            'description',
            'builder_name',
            'property_type',
            
            # Location
            'address',
            'city',
            'state',
            'country',
            'locality',
            'pincode',
            'latitude',
            'longitude',
            
            # Specifications
            'total_area',
            'total_units',
            'available_units',
            'units_sold',
            
            # Pricing
            'price_per_unit',
            'minimum_investment',
            'maximum_investment',
            'total_value',
            
            # Funding
            'target_amount',
            'funded_amount',
            'funding_percentage',
            'is_fully_funded',
            
            # Returns
            'expected_return_percentage',
            'gross_yield',
            'potential_gain',
            'expected_return_period',
            
            # Tenure
            'lock_in_period',
            'project_duration',
            
            # Dates
            'launch_date',
            'funding_start_date',
            'funding_end_date',
            'possession_date',
            
            # Images & Media
            'featured_image',
            'featured_image_url',
            'images',
            
            # Status
            'status',
            
            # Approval
            'approved_by',
            'approved_by_details',
            'approved_at',
            'rejection_reason',
            
            # Features
            'amenities',
            'highlights',
            
            # SEO
            'meta_title',
            'meta_description',
            
            # Visibility
            'is_featured',
            'is_published',
            'is_public_sale',
            'is_presale',
            
            # Developer
            'developer',
            'developer_details',
            
            # Relationships
            'documents',
            'units',
            
            # Stats
            'investment_stats',
            
            # Timestamps
            'created_at',
            'updated_at',
            
            # Soft Delete (if needed)
            'is_deleted',
            'deleted_at',
        ]
    
    def get_units_sold(self, obj):
        """Calculate units sold"""
        return obj.total_units - obj.available_units
    
    def get_funding_percentage(self, obj):
        """Get funding percentage"""
        return round(obj.funding_percentage, 2)
    
    def get_is_fully_funded(self, obj):
        """Check if fully funded"""
        return obj.is_fully_funded
    
    def get_total_value(self, obj):
        """Calculate total property value"""
        return str(obj.price_per_unit * obj.total_units)
    
    def get_featured_image_url(self, obj):
        """Get featured image URL"""
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None
    
    def get_developer_details(self, obj):
        """Get developer information"""
        if not obj.developer:
            return None
        return {
            'id': obj.developer.id,
            'username': obj.developer.username,
            'email': obj.developer.email,
            'phone': obj.developer.phone,
            'date_joined': obj.developer.date_joined,
        }
    
    def get_approved_by_details(self, obj):
        """Get approver information"""
        if not obj.approved_by:
            return None
        return {
            'id': obj.approved_by.id,
            'username': obj.approved_by.username,
            'email': obj.approved_by.email,
        }
    
    def get_investment_stats(self, obj):
        """Get comprehensive investment statistics"""
        from investments.models import Investment
        from django.db.models import Sum, Count, Avg
        
        investments = Investment.objects.filter(property=obj)
        
        approved_investments = investments.filter(status='approved')
        
        return {
            # Counts
            'total_investments': investments.count(),
            'pending_investments': investments.filter(status='pending').count(),
            'approved_investments': approved_investments.count(),
            'rejected_investments': investments.filter(status='rejected').count(),
            
            # Amounts
            'total_invested': str(approved_investments.aggregate(
                total=Sum('amount'))['total'] or 0),
            'average_investment': str(approved_investments.aggregate(
                avg=Avg('amount'))['avg'] or 0),
            
            # Units
            'total_units_purchased': approved_investments.aggregate(
                total=Sum('units_purchased'))['total'] or 0,
            
            # Unique investors
            'unique_investors': approved_investments.values('customer').distinct().count(),
        }


# ========================================
# CREATE/UPDATE SERIALIZER
# ========================================

class AdminPropertyCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating properties"""
    
    class Meta:
        model = Property
        fields = [
            'name',
            'slug',
            'description',
            'builder_name',
            'property_type',
            
            # Location
            'address',
            'city',
            'state',
            'country',
            'locality',
            'pincode',
            'latitude',
            'longitude',
            
            # Specifications
            'total_area',
            'total_units',
            'available_units',
            
            # Pricing
            'price_per_unit',
            'minimum_investment',
            'maximum_investment',
            
            # Funding
            'target_amount',
            'funded_amount',
            
            # Returns
            'expected_return_percentage',
            'gross_yield',
            'potential_gain',
            'expected_return_period',
            
            # Tenure
            'lock_in_period',
            'project_duration',
            
            # Dates
            'launch_date',
            'funding_start_date',
            'funding_end_date',
            'possession_date',
            
            # Images
            'featured_image',
            
            # Status
            'status',
            
            # Approval
            'approved_by',
            'approved_at',
            'rejection_reason',
            
            # Features
            'amenities',
            'highlights',
            
            # SEO
            'meta_title',
            'meta_description',
            
            # Visibility
            'is_featured',
            'is_published',
            'is_public_sale',
            'is_presale',
            
            # Developer
            'developer',
        ]
    
    def validate_total_units(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total units must be greater than 0")
        return value
    
    def validate_price_per_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price per unit must be greater than 0")
        return value
    
    def validate_total_area(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total area must be greater than 0")
        return value
    
    def validate_target_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Target amount must be greater than 0")
        return value
    
    def validate_minimum_investment(self, value):
        if value <= 0:
            raise serializers.ValidationError("Minimum investment must be greater than 0")
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        total_units = attrs.get('total_units')
        available_units = attrs.get('available_units')
        
        # Check available units don't exceed total
        if available_units and total_units and available_units > total_units:
            raise serializers.ValidationError({
                'available_units': 'Available units cannot exceed total units'
            })
        
        # Check minimum investment doesn't exceed maximum
        min_investment = attrs.get('minimum_investment')
        max_investment = attrs.get('maximum_investment')
        
        if min_investment and max_investment and min_investment > max_investment:
            raise serializers.ValidationError({
                'maximum_investment': 'Maximum investment cannot be less than minimum investment'
            })
        
        # Check funding dates
        funding_start = attrs.get('funding_start_date')
        funding_end = attrs.get('funding_end_date')
        
        if funding_start and funding_end and funding_start > funding_end:
            raise serializers.ValidationError({
                'funding_end_date': 'Funding end date must be after start date'
            })
        
        return attrs


# ========================================
# ACTION SERIALIZER
# ========================================

class AdminPropertyActionSerializer(serializers.Serializer):
    """Serializer for property actions"""
    action = serializers.ChoiceField(
        choices=[
            'publish', 
            'unpublish', 
            'archive', 
            'feature', 
            'unfeature',
            'approve',
            'reject'
        ],
        required=True
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required when action is 'reject'"
    )
    
    def validate(self, attrs):
        action = attrs.get('action')
        rejection_reason = attrs.get('rejection_reason')
        
        # Require rejection reason when rejecting
        if action == 'reject' and not rejection_reason:
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting property'
            })
        
        return attrs
    
"""
Property Admin Serializers
For admin dashboard property management
"""
from rest_framework import serializers
from .models import Property, PropertyImage, PropertyDocument, PropertyUnit
from django.contrib.auth import get_user_model

User = get_user_model()


# ========================================
# NESTED MODEL SERIALIZERS
# ========================================

class PropertyImageSerializer(serializers.ModelSerializer):
    """Serializer for property images"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'image_url', 'caption', 'order', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class PropertyDocumentSerializer(serializers.ModelSerializer):
    """Serializer for property documents"""
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    
    class Meta:
        model = PropertyDocument
        fields = [
            'id', 
            'title', 
            'document_type', 
            'file', 
            'file_url',
            'is_public', 
            'uploaded_by',
            'uploaded_by_name',
            'created_at'
        ]
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class PropertyUnitSerializer(serializers.ModelSerializer):
    """Serializer for property units"""
    reserved_by_name = serializers.CharField(source='reserved_by.username', read_only=True)
    
    class Meta:
        model = PropertyUnit
        fields = [
            'id',
            'unit_number',
            'floor',
            'area',
            'bedrooms',
            'bathrooms',
            'price',
            'status',
            'reserved_by',
            'reserved_by_name',
            'reserved_at',
            'created_at'
        ]


# ========================================
# IMAGE/DOCUMENT/UNIT CRUD SERIALIZERS
# ========================================

class PropertyImageUploadSerializer(serializers.ModelSerializer):
    """Upload property image"""
    class Meta:
        model = PropertyImage
        fields = ['property', 'image', 'caption', 'order']
    
    def validate_image(self, value):
        # Validate file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image size must be less than 5MB")
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Only JPEG, PNG, and WEBP images are allowed")
        
        return value


class PropertyDocumentUploadSerializer(serializers.ModelSerializer):
    """Upload property document"""
    class Meta:
        model = PropertyDocument
        fields = ['property', 'title', 'document_type', 'file', 'is_public', 'uploaded_by']
    
    def validate_file(self, value):
        # Validate file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must be less than 10MB")
        
        return value


class PropertyUnitCreateUpdateSerializer(serializers.ModelSerializer):
    """Create/update property unit"""
    class Meta:
        model = PropertyUnit
        fields = [
            'property',
            'unit_number',
            'floor',
            'area',
            'bedrooms',
            'bathrooms',
            'price',
            'status',
            'reserved_by'
        ]
    
    def validate_unit_number(self, value):
        # Check if unit number already exists for this property
        property_id = self.initial_data.get('property')
        instance_id = self.instance.id if self.instance else None
        
        if PropertyUnit.objects.filter(
            property_id=property_id,
            unit_number=value
        ).exclude(id=instance_id).exists():
            raise serializers.ValidationError(
                f"Unit number '{value}' already exists for this property"
            )
        
        return value