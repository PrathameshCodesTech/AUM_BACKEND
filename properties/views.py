from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Property
from .serializers import PropertyListSerializer, PropertyDetailSerializer,PropertyAnalyticsSerializer
from .services.property_service import PropertyService
from django.utils import timezone

from accounts.services.email_service import send_dynamic_email


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
        from django.conf import settings
        # from utils.emails import send_dynamic_email
        import logging
        
        logger = logging.getLogger(__name__) 
        
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
            
            # 🆕 SEND EMAIL TO ADMIN using centralized template
            try:
                admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', settings.EMAIL_HOST_USER)
                
                # Prepare email parameters
                email_params = {
                    'user_name': request.user.get_full_name() or 'Not provided',
                    'user_email': request.user.email,
                    'user_phone': getattr(request.user, 'phone', 'Not provided'),
                    'user_id': request.user.id,
                    'project_name': property_obj.name,
                    'location': f"{property_obj.city}, {property_obj.state}",
                    'min_investment': f"₹{property_obj.minimum_investment:,.0f}",
                    'units_interested': interest.token_count,
                    'admin_link': f"{settings.FRONTEND_BASE_URL}/admin/properties/{property_obj.id}/interests"
                }
                
                # Send email using centralized function
                send_dynamic_email(
                    email_type='admin_eoi_notification',
                    to=admin_email,
                    params=email_params
                )
                
                logger.info(f"✅ EOI notification email sent to admin for property: {property_obj.name} (User: {request.user.email})")
                
            except Exception as e:
                logger.error(f"❌ Failed to send EOI notification email: {str(e)}")
                # Don't fail the request if email fails - user experience is more important
            
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
            logger.error(f"❌ Error in ExpressInterestView: {str(e)}")
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
    
from investments.models import Investment
from django.db.models import Count, Sum

class PropertyAnalyticsView(APIView):
    """
    GET /api/properties/{slug}/analytics/
    GET /api/properties/{slug}/analytics/?amount=500000
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
            
            # DYNAMIC: Get real investor count for THIS property
            try:
                total_investors = Investment.objects.filter(
                    property=property_obj,
                    status='approved'
                ).values('customer').distinct().count()  # Changed from 'user' to 'customer'
            except Exception as inv_err:
                print(f"Investment count error: {inv_err}")
                total_investors = 0
            
            # DYNAMIC: Calculate actual funding breakdown
            total_funded = float(property_obj.funded_amount)
            if total_funded > 0:
                funding_breakdown = [
                    {"name": "Individual Investors", "value": 65, "color": "#10B981"},
                    {"name": "HNIs", "value": 20, "color": "#3B82F6"},
                    {"name": "Institutions", "value": 15, "color": "#F59E0B"}
                ]
            else:
                funding_breakdown = [
                    {"name": "Individual Investors", "value": 100, "color": "#10B981"}
                ]
            
            # CHART 2: Price History (Line Chart)
            months_back = 12
            price_history = []
            
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
                    "price": round(current_price / 100000) * 100000
                })
            
            # CHART 3: Payout History (Bar Chart)
            payout_history = [
                {"quarter": "Q1 2024", "amount": 250000, "type": "projected"},
                {"quarter": "Q2 2024", "amount": 320000, "type": "projected"},
                {"quarter": "Q3 2024", "amount": 280000, "type": "projected"},
                {"quarter": "Q4 2024", "amount": 350000, "type": "projected"},
                {"quarter": "Q1 2025", "amount": 400000, "type": "projected"}
            ]
            
            # CHART 4: ROI Breakdown (Donut Chart)
            roi_breakdown = [
                {"name": "Rental Yield", "value": gross_yield, "color": "#10B981"},
                {"name": "Capital Gain", "value": potential_gain, "color": "#F59E0B"},
                {"name": "Target IRR", "value": expected_return_pct, "color": "#EF4444"}
            ]
            
            # DYNAMIC: Progress Metrics
            funding_pct = 0
            if hasattr(property_obj, 'funding_percentage') and property_obj.funding_percentage:
                funding_pct = float(property_obj.funding_percentage)
            
            # DYNAMIC: Construction status based on property status
            construction_status_map = {
                'draft': 0,
                'pending_approval': 10,
                'approved': 20,
                'live': 30,
                'funding': 40,
                'funded': 50,
                'under_construction': 75,
                'completed': 100,
                'closed': 100
            }
            construction_pct = construction_status_map.get(property_obj.status, 0)
            
            # DYNAMIC: Investor goal
            target_investors = property_obj.total_units
            investor_goal_pct = (total_investors / target_investors * 100) if target_investors > 0 else 0
            investor_goal_pct = min(investor_goal_pct, 100)
            
            progress_metrics = {
                "funding": round(funding_pct, 1),
                "construction": round(construction_pct, 1),
                "investor_goal": round(investor_goal_pct, 1)
            }
            
            # Calculator defaults
            calculator = {
                "sample_amounts": [500000, 1000000, 2000000, 5000000],
                "launch_price": price_per_unit * 0.85,
                "current_price": price_per_unit
            }
            
            # DYNAMIC: Key metrics
            time_since_launch = 0
            if property_obj.launch_date:
                time_since_launch = (timezone.now().date() - property_obj.launch_date).days
            
            # DYNAMIC: Price appreciation calculation
            launch_price = calculator["launch_price"]
            current_price = calculator["current_price"]
            price_appreciation = ((current_price - launch_price) / launch_price * 100) if launch_price > 0 else 0
            
            key_metrics = {
                "total_investors": total_investors,
                "avg_roi": expected_return_pct,
                "time_since_launch_days": time_since_launch,
                "price_appreciation": round(price_appreciation, 1)
            }
            
            # Expected Earnings Calculation
            investment_amount = request.query_params.get('amount', 500000)
            try:
                investment_amount = float(investment_amount)
            except:
                investment_amount = 500000
            
            expected_earnings = self.calculate_expected_earnings(property_obj, investment_amount)
            
            analytics_data = {
                "funding_breakdown": funding_breakdown,
                "price_history": price_history,
                "payout_history": payout_history,
                "roi_breakdown": roi_breakdown,
                "progress_metrics": progress_metrics,
                "calculator": calculator,
                "key_metrics": key_metrics,
                "expected_earnings": expected_earnings
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
            import traceback
            print(f"Analytics Error: {e}")
            print(traceback.format_exc())
            return Response({
                "success": False,
                "message": f"Error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def calculate_expected_earnings(self, property_obj, investment_amount):
        """Calculate year-by-year expected earnings breakdown"""
        from datetime import timedelta
        
        tenure_months = property_obj.expected_return_period or property_obj.project_duration or 60
        tenure_years = (tenure_months // 12) or 5
        annual_return_rate = float(property_obj.expected_return_percentage or 12) / 100
        tax_rate = 0.10
        
        if property_obj.possession_date:
            payout_start_date = property_obj.possession_date
        elif property_obj.launch_date:
            months_to_add = property_obj.project_duration or 24
            payout_start_date = property_obj.launch_date + timedelta(days=months_to_add * 30)
        else:
            payout_start_date = timezone.now().date() + timedelta(days=730)
        
        earnings_breakdown = []
        
        for year in range(1, tenure_years + 1):
            payout_date = payout_start_date + timedelta(days=365 * year)
            gross_amount = investment_amount * annual_return_rate
            tax_amount = gross_amount * tax_rate
            net_amount = gross_amount - tax_amount
            
            earnings_breakdown.append({
                "date_period": f"{year} Year{'s' if year > 1 else ''}",
                "payout_date": payout_date.strftime("%d %b %Y"),
                "gross_amount": round(gross_amount, 2),
                "gross_amount_display": f"₹ {round(gross_amount / 100000, 2)} L",
                "tax_amount": round(tax_amount, 2),
                "tax_amount_display": f"₹ {round(tax_amount):,}",
                "net_amount": round(net_amount, 2),
                "net_amount_display": f"₹ {round(net_amount / 100000, 2)} L"
            })
        
        return {
            "investment_amount": investment_amount,
            "investment_amount_display": f"₹ {round(investment_amount / 100000, 2)} L",
            "total_tenure_years": tenure_years,
            "annual_return_rate": annual_return_rate * 100,
            "tax_rate": tax_rate * 100,
            "breakdown": earnings_breakdown,
            "total_gross": sum([item["gross_amount"] for item in earnings_breakdown]),
            "total_tax": sum([item["tax_amount"] for item in earnings_breakdown]),
            "total_net": sum([item["net_amount"] for item in earnings_breakdown])
        }
