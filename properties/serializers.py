from rest_framework import serializers
from .models import Property, PropertyUnit, PropertyImage, PropertyDocument

class PropertyImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'image_url', 'caption', 'order']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

class PropertyDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyDocument
        fields = ['id', 'title', 'document_type', 'file', 'file_url', 'is_public', 'created_at']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

class PropertyUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyUnit
        fields = ['id', 'unit_number', 'floor', 'area', 'bedrooms', 'bathrooms', 'price', 'status']

class PropertyListSerializer(serializers.ModelSerializer):
    """Serializer for property listing (card view)"""
    primary_image = serializers.SerializerMethodField()
    invested_percentage = serializers.SerializerMethodField()
    investor_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = [
            'id', 'name', 'slug', 'property_type', 'status',
            'builder_name', 'city', 'state', 'locality',
            'target_amount', 'minimum_investment', 'maximum_investment',
            'total_units', 'available_units',
            'expected_return_percentage', 'gross_yield', 'potential_gain',
            'funded_amount', 'invested_percentage', 'investor_count',
            'primary_image',
            'is_featured', 'is_public_sale', 'is_presale',
            'created_at'
        ]
    
    #!
    def get_primary_image(self, obj):
        # First try featured image
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        
        # Fallback to first gallery image
        first_image = obj.images.first()
        if first_image and first_image.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        
        return None
    
    def get_invested_percentage(self, obj):
        return round(float(obj.funding_percentage), 2)
    
    def get_investor_count(self, obj):
        # TODO: Calculate from investments when Investment model is ready
        return 0

class PropertyDetailSerializer(serializers.ModelSerializer):
    """Serializer for property detail view"""
    images = PropertyImageSerializer(many=True, read_only=True)
    documents = PropertyDocumentSerializer(many=True, read_only=True)
    units = PropertyUnitSerializer(many=True, read_only=True)
    invested_percentage = serializers.SerializerMethodField()
    investor_count = serializers.SerializerMethodField()
    developer_name = serializers.CharField(source='developer.username', read_only=True)
    primary_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = [
            'id', 'name', 'slug', 'description', 'property_type', 'status',
            'builder_name', 'developer_name',
            'address', 'city', 'state', 'country', 'locality', 'pincode',
            'latitude', 'longitude',
            'total_area', 'total_units', 'available_units',
            'price_per_unit', 'minimum_investment', 'maximum_investment',
            'target_amount', 'funded_amount', 'invested_percentage', 'investor_count',
            'expected_return_percentage', 'gross_yield', 'potential_gain',
            'expected_return_period',
            'lock_in_period', 'project_duration',
            'launch_date', 'funding_start_date', 'funding_end_date', 'possession_date',
            'featured_image', 'primary_image',
            'amenities', 'highlights',
            'is_featured', 'is_published', 'is_public_sale', 'is_presale',
            'images', 'documents', 'units',
            'created_at', 'updated_at'
        ]
    
    def get_invested_percentage(self, obj):
        return round(float(obj.funding_percentage), 2)
    
    def get_investor_count(self, obj):
        # TODO: Calculate from investments when Investment model is ready
        return 0
    
    def get_primary_image(self, obj):
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None