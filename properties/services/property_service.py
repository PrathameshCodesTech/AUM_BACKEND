from django.db.models import Count, Sum, Q
from ..models import Property, PropertyUnit

class PropertyService:
    """Service for property-related business logic"""
    
    
    @staticmethod
    def get_properties_with_stats(filters=None):
        """Get properties with filters"""
        from django.db.models import Q
        
        queryset = Property.objects.filter(
            status='live', 
            is_published=True,
            is_deleted=False  # Exclude soft-deleted
        )
        
        # Apply filters
        if filters:
            if filters.get('city'):
                queryset = queryset.filter(city__iexact=filters['city'])
            
            if filters.get('builder'):
                queryset = queryset.filter(builder_name__icontains=filters['builder'])
            
            if filters.get('property_type'):
                queryset = queryset.filter(property_type=filters['property_type'])
            
            if filters.get('is_featured') is not None:
                queryset = queryset.filter(is_featured=filters['is_featured'])
            
            if filters.get('is_public_sale') is not None:
                queryset = queryset.filter(is_public_sale=filters['is_public_sale'])
            
            if filters.get('is_presale') is not None:
                queryset = queryset.filter(is_presale=filters['is_presale'])
            
            # Search filter (searches in name, builder_name, city, locality)
            if filters.get('search'):
                search_term = filters['search']
                queryset = queryset.filter(
                    Q(name__icontains=search_term) |
                    Q(builder_name__icontains=search_term) |
                    Q(city__icontains=search_term) |
                    Q(locality__icontains=search_term)
                )
        
        # Order by: Featured first, then by created date
        # Handle sorting
        sort_by = filters.get('sort_by', 'default')
        
        if sort_by == 'price_low':
            queryset = queryset.order_by('minimum_investment', '-is_featured')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-minimum_investment', '-is_featured')
        elif sort_by == 'yield_high':
            queryset = queryset.order_by('-gross_yield', '-is_featured')
        elif sort_by == 'irr_high':
            queryset = queryset.order_by('-expected_return_percentage', '-is_featured')
        else:
            # Default: Featured first, then by created date
            queryset = queryset.order_by('-is_featured', '-created_at')
        
        return queryset
    
    @staticmethod
    def get_property_detail(property_id):
        """Get detailed property information"""
        property_obj = Property.objects.get(
            id=property_id,
            is_published=True,
            is_deleted=False
        )
        return property_obj
    
    @staticmethod
    def calculate_investment_stats(property_obj):
        """Calculate investment statistics for property"""
        total_units = property_obj.total_units
        available_units = property_obj.available_units
        sold_units = total_units - available_units
        sold_percentage = (sold_units / total_units * 100) if total_units > 0 else 0
        
        return {
            'total_units': total_units,
            'available_units': available_units,
            'sold_units': sold_units,
            'sold_percentage': round(sold_percentage, 2),
            'minimum_investment': str(property_obj.minimum_investment),
            'maximum_investment': str(property_obj.maximum_investment) if property_obj.maximum_investment else None,
            'funded_amount': str(property_obj.funded_amount),
            'target_amount': str(property_obj.target_amount),
            'funding_percentage': round(property_obj.funding_percentage, 2)
        }