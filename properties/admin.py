# properties/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count, Sum
from django.db import models
import json
from .models import Property, PropertyUnit, PropertyImage, PropertyDocument


# ============================================
# CUSTOM FILTERS
# ============================================

class PropertyStatusFilter(admin.SimpleListFilter):
    title = 'property status'
    parameter_name = 'prop_status'

    def lookups(self, request, model_admin):
        return Property.STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())


class PropertyTypeFilter(admin.SimpleListFilter):
    title = 'property type'
    parameter_name = 'prop_type'

    def lookups(self, request, model_admin):
        return Property.PROPERTY_TYPE_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(property_type=self.value())


class FundingStatusFilter(admin.SimpleListFilter):
    title = 'funding status'
    parameter_name = 'funding'

    def lookups(self, request, model_admin):
        return (
            ('unfunded', 'Not Funded'),
            ('partial', 'Partially Funded'),
            ('fully_funded', 'Fully Funded'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'unfunded':
            return queryset.filter(funded_amount=0)
        elif self.value() == 'partial':
            return queryset.filter(
                funded_amount__gt=0,
                funded_amount__lt=models.F('target_amount')
            )
        elif self.value() == 'fully_funded':
            return queryset.filter(funded_amount__gte=models.F('target_amount'))


# ============================================
# PROPERTY ADMIN
# ============================================

class PropertyUnitInline(admin.TabularInline):
    model = PropertyUnit
    extra = 1
    fields = ['unit_number', 'floor', 'area', 'bedrooms', 'bathrooms', 'price', 'status']
    ordering = ['floor', 'unit_number']


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 3
    fields = ['image', 'caption', 'order']
    ordering = ['order']


class PropertyDocumentInline(admin.TabularInline):
    model = PropertyDocument
    extra = 1
    fields = ['title', 'document_type', 'file', 'is_public']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'property_type_badge',
        'location_display',
        'price_display',
        'funding_progress',
        'units_status',
        'status_badge',
        'featured_badge',
        'created_at',
    ]
    
    list_filter = [
        PropertyStatusFilter,
        PropertyTypeFilter,
        FundingStatusFilter,
        'is_featured',
        'is_published',
        'is_public_sale',
        'is_presale',
        'city',
        'state',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'slug',
        'description',
        'builder_name',
        'city',
        'state',
        'locality',
        'pincode',
        'developer__username',
    ]
    
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'approved_by',
        'approved_at',
        'deleted_at',
        'deleted_by',
        'funding_percentage_display',
        'funded_amount_display',
        'featured_image_preview',
        'investment_count',
        'investor_count',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'developer',
                'name',
                'slug',
                'description',
                'builder_name',
                'property_type',
            )
        }),
        ('Location', {
            'fields': (
                'address',
                'city',
                'state',
                'country',
                'locality',
                'pincode',
                'latitude',
                'longitude',
            ),
            'classes': ('collapse',),
        }),
        ('Property Specifications', {
            'fields': (
                'total_area',
                'total_units',
                'available_units',
            )
        }),
        ('Pricing', {
            'fields': (
                'price_per_unit',
                'minimum_investment',
                'maximum_investment',
            )
        }),
        ('Funding', {
            'fields': (
                'target_amount',
                'funded_amount_display',
                'funding_percentage_display',
            )
        }),
        ('Returns & Tenure', {
            'fields': (
                'expected_return_percentage',
                'gross_yield',
                'potential_gain',
                'expected_return_period',
                'lock_in_period',
                'project_duration',
            ),
            'classes': ('collapse',),
        }),
        ('Important Dates', {
            'fields': (
                'launch_date',
                'funding_start_date',
                'funding_end_date',
                'possession_date',
            )
        }),
        ('Media', {
            'fields': (
                'featured_image',
                'featured_image_preview',
            )
        }),
        ('Status & Approval', {
            'fields': (
                'status',
                'approved_by',
                'approved_at',
                'rejection_reason',
            )
        }),
        ('Features (JSON)', {
            'fields': (
                'amenities',
                'highlights',
            ),
            'classes': ('collapse',),
        }),
        ('SEO', {
            'fields': (
                'meta_title',
                'meta_description',
            ),
            'classes': ('collapse',),
        }),
        ('Visibility', {
            'fields': (
                'is_featured',
                'is_published',
                'is_public_sale',
                'is_presale',
            )
        }),
        ('Soft Delete', {
            'fields': (
                'is_deleted',
                'deleted_at',
                'deleted_by',
            ),
            'classes': ('collapse',),
        }),
        ('Statistics', {
            'fields': (
                'investment_count',
                'investor_count',
            ),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    inlines = [PropertyUnitInline, PropertyImageInline, PropertyDocumentInline]
    autocomplete_fields = ['developer', 'approved_by', 'deleted_by']
    
    # Custom display methods
    def property_type_badge(self, obj):
        colors = {
            'residential': '#28a745',
            'commercial': '#007bff',
            'industrial': '#6c757d',
            'land': '#ffc107',
            'mixed': '#6f42c1',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px; text-transform: uppercase;">{}</span>',
            colors.get(obj.property_type, '#6c757d'),
            obj.get_property_type_display()
        )
    property_type_badge.short_description = 'Type'
    property_type_badge.admin_order_field = 'property_type'
    
    def location_display(self, obj):
        return format_html('<strong>{}</strong>, {}', obj.city, obj.state)
    location_display.short_description = 'Location'
    
    def price_display(self, obj):
        # Fix: Use {} placeholders instead of :f
        return format_html(
            '₹ {}<br><small style="color: #6c757d;">per unit</small>',
            '{:,.2f}'.format(obj.price_per_unit)
        )
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price_per_unit'
    
    def funding_progress(self, obj):
        percentage = obj.funding_percentage
        
        if percentage >= 100:
            color = '#28a745'
            status_text = 'Fully Funded'
        elif percentage >= 75:
            color = '#17a2b8'
            status_text = 'Almost There'
        elif percentage >= 50:
            color = '#ffc107'
            status_text = 'Half Way'
        elif percentage > 0:
            color = '#fd7e14'
            status_text = 'In Progress'
        else:
            color = '#6c757d'
            status_text = 'Not Started'
        
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 10px; overflow: hidden; height: 20px;">'
            '<div style="width: {}%; background-color: {}; height: 100%; display: flex; align-items: center; justify-content: center;">'
            '<small style="color: white; font-weight: bold; font-size: 10px;">{}</small>'
            '</div></div>'
            '<small style="color: {};">{}</small>',
            min(percentage, 100),
            color,
            '{:.1f}%'.format(percentage),
            color,
            status_text
        )
    funding_progress.short_description = 'Funding'
    
    def units_status(self, obj):
        total = obj.total_units
        available = obj.available_units
        sold = total - available
        
        return format_html(
            '<strong>{}</strong> / {} units<br>'
            '<small style="color: #28a745;">{} available</small> • '
            '<small style="color: #dc3545;">{} sold</small>',
            available, total, available, sold
        )
    units_status.short_description = 'Units'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'pending_approval': '#ffc107',
            'approved': '#17a2b8',
            'live': '#28a745',
            'funding': '#007bff',
            'funded': '#6f42c1',
            'under_construction': '#fd7e14',
            'completed': '#28a745',
            'closed': '#dc3545',
        }
        
        if obj.is_deleted:
            return format_html(
                '<span style="background-color: #000; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 10px;">🗑️ DELETED</span>'
            )
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html('⭐ <span style="color: #ffc107;">Featured</span>')
        return format_html('<span style="color: #999;">—</span>')
    featured_badge.short_description = 'Featured'
    featured_badge.admin_order_field = 'is_featured'
    
    def funding_percentage_display(self, obj):
        percentage = obj.funding_percentage
        
        if percentage >= 100:
            color = '#28a745'
        elif percentage >= 50:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<div style="font-size: 24px; font-weight: bold; color: {};">{}</div>'
            '<div style="color: #6c757d;">of ₹{} target</div>',
            color,
            '{:.2f}%'.format(percentage),
            '{:,.2f}'.format(obj.target_amount)
        )
    funding_percentage_display.short_description = 'Funding Progress'
    
    def funded_amount_display(self, obj):
        return format_html(
            '<strong style="color: #007bff; font-size: 16px;">₹ {}</strong>',
            '{:,.2f}'.format(obj.funded_amount)
        )
    funded_amount_display.short_description = 'Funded Amount'
    
    def featured_image_preview(self, obj):
        if obj.featured_image:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 400px; max-height: 300px; border: 1px solid #ddd; border-radius: 5px;" />'
                '</a><br><a href="{}" target="_blank" class="button">View Full Size</a>',
                obj.featured_image.url,
                obj.featured_image.url,
                obj.featured_image.url
            )
        return format_html('<span style="color: #999;">No featured image</span>')
    featured_image_preview.short_description = 'Featured Image Preview'
    
    def investment_count(self, obj):
        from investments.models import Investment
        count = Investment.objects.filter(property=obj).count()
        return format_html('<strong>{}</strong> investments', count)
    investment_count.short_description = 'Total Investments'
    
    def investor_count(self, obj):
        from investments.models import Investment
        count = Investment.objects.filter(property=obj).values('customer').distinct().count()
        return format_html('<strong>{}</strong> investors', count)
    investor_count.short_description = 'Unique Investors'
    
    actions = [
        'approve_properties',
        'reject_properties',
        'publish_properties',
        'unpublish_properties',
        'mark_as_featured',
        'remove_featured',
        'mark_as_live',
        'update_funding',
    ]
    
    def approve_properties(self, request, queryset):
        count = queryset.filter(status='pending_approval').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, '{} propert(y/ies) approved.'.format(count))
    approve_properties.short_description = '✓ Approve Properties'
    
    def reject_properties(self, request, queryset):
        count = queryset.filter(status='pending_approval').update(
            status='draft',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, '{} propert(y/ies) rejected.'.format(count), level='WARNING')
    reject_properties.short_description = '❌ Reject Properties'
    
    def publish_properties(self, request, queryset):
        count = queryset.update(is_published=True)
        self.message_user(request, '{} propert(y/ies) published.'.format(count))
    publish_properties.short_description = '📢 Publish Properties'
    
    def unpublish_properties(self, request, queryset):
        count = queryset.update(is_published=False)
        self.message_user(request, '{} propert(y/ies) unpublished.'.format(count))
    unpublish_properties.short_description = '📴 Unpublish Properties'
    
    def mark_as_featured(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, '{} propert(y/ies) marked as featured.'.format(count))
    mark_as_featured.short_description = '⭐ Mark as Featured'
    
    def remove_featured(self, request, queryset):
        count = queryset.update(is_featured=False)
        self.message_user(request, '{} propert(y/ies) removed from featured.'.format(count))
    remove_featured.short_description = '○ Remove Featured'
    
    def mark_as_live(self, request, queryset):
        count = queryset.filter(status='approved').update(status='live')
        self.message_user(request, '{} propert(y/ies) marked as live.'.format(count))
    mark_as_live.short_description = '🟢 Mark as Live'
    
    def update_funding(self, request, queryset):
        count = 0
        for prop in queryset:
            prop.update_funded_amount()
            count += 1
        self.message_user(request, 'Funding updated for {} propert(y/ies).'.format(count))
    update_funding.short_description = '🔄 Update Funding Amounts'


# ============================================
# PROPERTY UNIT ADMIN
# ============================================

@admin.register(PropertyUnit)
class PropertyUnitAdmin(admin.ModelAdmin):
    list_display = [
        'unit_number',
        'property_link',
        'floor',
        'area_display',
        'bedroom_bath',
        'price_display',
        'status_badge',
        'reserved_by_display',
    ]
    
    list_filter = ['status', 'property', 'floor', 'bedrooms', 'created_at']
    search_fields = ['unit_number', 'property__name', 'reserved_by__username']
    ordering = ['property', 'floor', 'unit_number']
    readonly_fields = ['created_at', 'updated_at', 'reserved_at']
    autocomplete_fields = ['property', 'reserved_by']
    
    def property_link(self, obj):
        url = reverse('admin:properties_property_change', args=[obj.property.id])
        return format_html('<a href="{}">{}</a>', url, obj.property.name)
    property_link.short_description = 'Property'
    
    def area_display(self, obj):
        return format_html('{} sq ft', '{:,.2f}'.format(obj.area))
    area_display.short_description = 'Area'
    
    def bedroom_bath(self, obj):
        if obj.bedrooms and obj.bathrooms:
            return format_html('🛏️ {} • 🚿 {}', obj.bedrooms, obj.bathrooms)
        return format_html('<span style="color: #999;">—</span>')
    bedroom_bath.short_description = 'BR/BA'
    
    def price_display(self, obj):
        return format_html(
            '<strong style="color: #007bff;">₹ {}</strong>',
            '{:,.2f}'.format(obj.price)
        )
    price_display.short_description = 'Price'
    
    def status_badge(self, obj):
        colors = {
            'available': '#28a745',
            'reserved': '#ffc107',
            'sold': '#dc3545',
            'blocked': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def reserved_by_display(self, obj):
        if obj.reserved_by:
            url = reverse('admin:accounts_user_change', args=[obj.reserved_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.reserved_by.get_full_name() or obj.reserved_by.username)
        return format_html('<span style="color: #999;">—</span>')
    reserved_by_display.short_description = 'Reserved By'


# ============================================
# PROPERTY IMAGE ADMIN
# ============================================

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ['property_link', 'image_thumbnail', 'caption', 'order', 'created_at']
    list_filter = ['property', 'created_at']
    search_fields = ['property__name', 'caption']
    ordering = ['property', 'order']
    readonly_fields = ['created_at', 'updated_at', 'image_preview']
    autocomplete_fields = ['property']
    
    def property_link(self, obj):
        url = reverse('admin:properties_property_change', args=[obj.property.id])
        return format_html('<a href="{}">{}</a>', url, obj.property.name)
    property_link.short_description = 'Property'
    
    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 80px; height: 60px; object-fit: cover; border-radius: 5px;" />',
                obj.image.url
            )
        return format_html('<span style="color: #999;">No image</span>')
    image_thumbnail.short_description = 'Image'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 600px; max-height: 400px; border: 1px solid #ddd; border-radius: 5px;" />'
                '</a>',
                obj.image.url,
                obj.image.url
            )
        return format_html('<span style="color: #999;">No image uploaded</span>')
    image_preview.short_description = 'Image Preview'


# ============================================
# PROPERTY DOCUMENT ADMIN
# ============================================

@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'property_link', 'document_type_badge', 'is_public_badge', 'uploaded_by_link', 'created_at']
    list_filter = ['document_type', 'is_public', 'property', 'created_at']
    search_fields = ['title', 'property__name', 'uploaded_by__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['property', 'uploaded_by']
    
    def property_link(self, obj):
        url = reverse('admin:properties_property_change', args=[obj.property.id])
        return format_html('<a href="{}">{}</a>', url, obj.property.name)
    property_link.short_description = 'Property'
    
    def document_type_badge(self, obj):
        colors = {
            'prospectus': '#007bff',
            'legal': '#dc3545',
            'approval': '#28a745',
            'plan': '#17a2b8',
            'brochure': '#ffc107',
            'agreement': '#6f42c1',
            'other': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.document_type, '#6c757d'),
            obj.get_document_type_display()
        )
    document_type_badge.short_description = 'Type'
    
    def is_public_badge(self, obj):
        if obj.is_public:
            return format_html('<span style="color: #28a745;">🌐 Public</span>')
        return format_html('<span style="color: #6c757d;">🔒 Private</span>')
    is_public_badge.short_description = 'Access'
    
    def uploaded_by_link(self, obj):
        if obj.uploaded_by:
            url = reverse('admin:accounts_user_change', args=[obj.uploaded_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.uploaded_by.get_full_name() or obj.uploaded_by.username)
        return format_html('<span style="color: #999;">System</span>')
    uploaded_by_link.short_description = 'Uploaded By'
