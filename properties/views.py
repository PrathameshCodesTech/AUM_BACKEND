from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Property
from .serializers import PropertyListSerializer, PropertyDetailSerializer,PropertyAnalyticsSerializer
from .services.property_service import PropertyService
from django.utils import timezone


class PropertyListView(generics.ListAPIView):
    """
    GET /api/properties/
    List all active properties with filters
    """
    permission_classes = [AllowAny]
    serializer_class = PropertyListSerializer
    
    def get_queryset(self):
        # Get query parameters
        status_filter = self.request.query_params.get('status')  # 'public_sale' or 'presale'
        city = self.request.query_params.get('city')
        builder_name = self.request.query_params.get('builder_name')
        property_type = self.request.query_params.get('property_type')
        search = self.request.query_params.get('search')
        sort_by = self.request.query_params.get('sort_by')  # ← ADD THIS
        
        # Build filters dict
        filters = {}
        
        if city:
            filters['city'] = city
        
        if builder_name:
            filters['builder'] = builder_name
        
        if property_type:
            filters['property_type'] = property_type
        
        # Handle status filter (public_sale vs presale)
        if status_filter == 'public_sale':
            filters['is_public_sale'] = True
        elif status_filter == 'presale':
            filters['is_presale'] = True
        
        # Handle search
        if search:
            filters['search'] = search
        
        # Handle sorting
        if sort_by:
            filters['sort_by'] = sort_by
        
        return PropertyService.get_properties_with_stats(filters)
    

class PropertyDetailView(APIView):
    """
    GET /api/properties/{id}/
    GET /api/properties/{id}/?deep=true  (includes all related data)
    Get property details
    """
    permission_classes = [AllowAny]
    
    def get(self, request, property_id):
        try:
            # Get deep parameter
            deep = request.query_params.get('deep', 'false').lower() == 'true'
            
            property_obj = PropertyService.get_property_detail(property_id)
            
            if deep:
                # Use DetailSerializer with all related data
                serializer = PropertyDetailSerializer(property_obj, context={'request': request})
                
                # Add investment stats
                stats = PropertyService.calculate_investment_stats(property_obj)
                
                # Get all images (featured + gallery)
                images = []
                
                # Add featured image first
                if property_obj.featured_image:
                    images.append({
                        'id': 0,
                        'url': request.build_absolute_uri(property_obj.featured_image.url),
                        'caption': 'Featured Image',
                        'is_featured': True
                    })
                
                # Add gallery images
                for img in property_obj.images.all().order_by('order'):
                    images.append({
                        'id': img.id,
                        'url': request.build_absolute_uri(img.image.url) if img.image else None,
                        'caption': img.caption or f'{property_obj.name} - Image {img.id}',
                        'is_featured': False,
                        'order': img.order
                    })
                
                # Get documents
                documents = []
                for doc in property_obj.documents.all():
                    documents.append({
                        'id': doc.id,
                        'title': doc.title,
                        'document_type': doc.document_type,
                        'file_url': request.build_absolute_uri(doc.file.url) if doc.file else None,
                        'is_public': doc.is_public,
                        'created_at': doc.created_at
                    })
                
                # Get units
                units = []
                for unit in property_obj.units.all():
                    units.append({
                        'id': unit.id,
                        'unit_number': unit.unit_number,
                        'floor': unit.floor,
                        'area': str(unit.area),
                        'bedrooms': unit.bedrooms,
                        'bathrooms': unit.bathrooms,
                        'price': str(unit.price),
                        'status': unit.status
                    })
                
                return Response({
                    'success': True,
                    'data': {
                        **serializer.data,
                        'stats': stats,
                        'all_images': images,
                        'all_documents': documents,
                        'all_units': units
                    }
                }, status=status.HTTP_200_OK)
            else:
                # Basic response
                serializer = PropertyListSerializer(property_obj, context={'request': request})
                return Response({
                    'success': True,
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            
        except Property.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Property not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExpressInterestView(APIView):
    """
    POST /api/properties/{id}/express-interest/
    Express interest in a property
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, property_id):
        from .models import PropertyInterest
        
        try:
            # Check if property exists
            property_obj = Property.objects.get(id=property_id, is_published=True)
            
            # Get or create interest
            interest, created = PropertyInterest.objects.get_or_create(
                property=property_obj,
                user=request.user,
                defaults={
                    'token_count': request.data.get('token_count', 1),
                    'message': request.data.get('message', ''),
                    'status': 'pending'
                }
            )
            
            if not created:
                # Update existing interest
                interest.token_count = request.data.get('token_count', interest.token_count)
                interest.message = request.data.get('message', interest.message)
                interest.status = 'pending'
                interest.save()
                
                message = 'Your interest has been updated. Our team will contact you soon.'
            else:
                message = 'Interest registered successfully. Our team will contact you soon.'
            
            # TODO: Send notification to admin/sales team
            # send_interest_notification(interest)
            
            return Response({
                'success': True,
                'message': message,
                'data': {
                    'interest_id': interest.id,
                    'property_name': property_obj.name,
                    'status': interest.status
                }
            }, status=status.HTTP_200_OK)
            
        except Property.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Property not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class PropertyFilterOptionsView(APIView):
    """
    GET /api/properties/filter-options/
    Get available filter options (cities, builders, property types)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get distinct values from live properties
        properties = Property.objects.filter(
            status='live',
            is_published=True,
            is_deleted=False
        )
        
        # Get unique cities
        cities = properties.values_list('city', flat=True).distinct().order_by('city')
        
        # Get unique builders
        builders = properties.values_list('builder_name', flat=True).distinct().order_by('builder_name')
        
        # Get property types with their display names
        property_types = []
        for choice in Property.PROPERTY_TYPE_CHOICES:
            if properties.filter(property_type=choice[0]).exists():
                property_types.append({
                    'value': choice[0],
                    'label': choice[1]
                })
        
        return Response({
            'success': True,
            'data': {
                'cities': list(cities),
                'builders': list(builders),
                'property_types': property_types
            }
        }, status=status.HTTP_200_OK)
    
    
    
class PropertyAnalyticsView(APIView):
    """
    GET /api/properties/{slug}/analytics/
    Property analytics for showcase page with charts
    """
    permission_classes = [AllowAny]
    
    def get(self, request, slug):
        try:
            # Get property by slug (any status, not deleted)
            property_obj = Property.objects.select_related('developer').get(
                slug=slug, 
                is_deleted=False
            )
            
            # Basic property data
            property_serializer = PropertyListSerializer(property_obj, context={'request': request})
            
            # SAFE Decimal → Float conversions
            price_per_unit = float(property_obj.price_per_unit)
            gross_yield = float(property_obj.gross_yield or 0)
            potential_gain = float(property_obj.potential_gain or 0)
            expected_return_pct = float(property_obj.expected_return_percentage or 0)
            
            # CHART 1: Funding Sources (Pie Chart)
            funding_breakdown = [
                {"name": "Individual Investors", "value": 65, "color": "#10B981"},
                {"name": "HNIs", "value": 20, "color": "#3B82F6"},
                {"name": "Institutions", "value": 15, "color": "#F59E0B"}
            ]
            
            # CHART 2: Price History (Line Chart) - FULLY SAFE
            months_back = 12
            price_history = []
            
            # SAFE launch_date handling
            if property_obj.launch_date:
                start_month = property_obj.launch_date.month
                start_year = property_obj.launch_date.year
            else:
                start_month = 1
                start_year = 2024
            
            for i in range(months_back, 0, -1):
                month_num = ((start_month + i - 2) % 12) + 1
                year_num = start_year + ((start_month + i - 2) // 12)
                
                growth_rate = 0.015 + (i * 0.002)
                current_price = price_per_unit * (1 + growth_rate * i)
                
                price_history.append({
                    "month": f"M{month_num:02d}/{str(year_num)[-2:]}",
                    "price": round(current_price / 100000) * 100000  # Lakhs
                })
            
            # CHART 3: Payout History (Bar Chart)
            payout_history = [
                {"quarter": "Q1 2024", "amount": 250000, "type": "actual"},
                {"quarter": "Q2 2024", "amount": 320000, "type": "actual"},
                {"quarter": "Q3 2024", "amount": 280000, "type": "actual"},
                {"quarter": "Q4 2024", "amount": 350000, "type": "projected"},
                {"quarter": "Q1 2025", "amount": 400000, "type": "projected"}
            ]
            
            # CHART 4: ROI Breakdown (Donut Chart)
            roi_breakdown = [
                {"name": "Rental Yield", "value": gross_yield, "color": "#10B981"},
                {"name": "Capital Gain", "value": potential_gain, "color": "#F59E0B"},
                {"name": "Target IRR", "value": expected_return_pct, "color": "#EF4444"}
            ]
            
            # CHART 5: Progress Metrics - SAFE funding_percentage
            funding_pct = 0
            if hasattr(property_obj, 'funding_percentage') and property_obj.funding_percentage:
                funding_pct = float(property_obj.funding_percentage)
            
            progress_metrics = {
                "funding": round(funding_pct, 1),
                "construction": min(80 + (funding_pct * 0.25), 100),
                "investor_goal": 75.0
            }
            
            # Calculator defaults - SAFE
            calculator = {
                "sample_amounts": [500000, 1000000, 2000000, 5000000],
                "launch_price": price_per_unit * 0.85,
                "current_price": price_per_unit
            }
            
            # Key metrics - FULLY SAFE
            time_since_launch = 0
            if property_obj.launch_date:
                time_since_launch = (timezone.now().date() - property_obj.launch_date).days
            
            key_metrics = {
                "total_investors": 250,
                "avg_roi": expected_return_pct,
                "time_since_launch_days": time_since_launch,
                "price_appreciation": 28.6
            }
            
            analytics_data = {
                "funding_breakdown": funding_breakdown,
                "price_history": price_history,
                "payout_history": payout_history,
                "roi_breakdown": roi_breakdown,
                "progress_metrics": progress_metrics,
                "calculator": calculator,
                "key_metrics": key_metrics
            }
            
            return Response({
                "success": True,
                "data": {
                    "property": property_serializer.data,
                    "analytics": analytics_data
                }
            }, status=status.HTTP_200_OK)
            
        except Property.DoesNotExist:
            return Response({
                "success": False,
                "message": "Property not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
