from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Property
from .serializers import PropertyListSerializer, PropertyDetailSerializer
from .services.property_service import PropertyService

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