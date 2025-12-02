from django.urls import path
from .views import PropertyListView, PropertyDetailView, ExpressInterestView, PropertyFilterOptionsView, PropertyAnalyticsView

app_name = 'properties'

urlpatterns = [
    path('', PropertyListView.as_view(), name='property-list'),
    path('<int:property_id>/', PropertyDetailView.as_view(), name='property-detail'),
    path('<int:property_id>/express-interest/', ExpressInterestView.as_view(), name='express-interest'),
    path('filter-options/', PropertyFilterOptionsView.as_view(), name='filter-options'),  # ← ADD THIS BEFORE detail route
    path('<str:slug>/analytics/', PropertyAnalyticsView.as_view(), name='property-analytics'),  # ← ADD THIS
]