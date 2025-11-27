# properties/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Property, PropertyUnit, PropertyImage, PropertyDocument
)


# ============================================
# INLINE ADMINS
# ============================================
class PropertyUnitInline(admin.TabularInline):
    model = PropertyUnit
    extra = 1
    fields = ('unit_number', 'floor', 'area',
              'bedrooms', 'bathrooms', 'price', 'status')
    ordering = ('unit_number',)


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    fields = ('image', 'caption', 'order')
    ordering = ('order',)


class PropertyDocumentInline(admin.TabularInline):
    model = PropertyDocument
    extra = 1
    fields = ('title', 'document_type', 'file', 'is_public')
    autocomplete_fields = ['uploaded_by']


# ============================================
# PROPERTY ADMIN
# ============================================
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'colored_type', 'city', 'developer', 'colored_status',
        'funding_progress', 'total_units', 'available_units',
        'price_display', 'is_featured', 'is_published', 'created_at'
    )
    list_filter = (
        'status', 'property_type', 'is_featured', 'is_published',
        'organization', 'city', 'state', 'created_at', 'launch_date'
    )
    search_fields = (
        'name', 'slug', 'description', 'city', 'state',
        'developer__username', 'address'
    )
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['organization', 'developer', 'approved_by']
    ordering = ('-created_at',)
    date_hierarchy = 'launch_date'

    fieldsets = (
        ('Basic Info', {
            'fields': ('organization', 'developer', 'name', 'slug', 'description')
        }),
        ('Property Details', {
            'fields': ('property_type', 'total_area', 'total_units', 'available_units')
        }),
        ('Location', {
            'fields': (
                'address', ('city', 'state'), ('country', 'pincode'),
                ('latitude', 'longitude')
            )
        }),
        ('Pricing', {
            'fields': (
                'price_per_unit', 'minimum_investment', 'maximum_investment',
                'target_amount', 'funded_amount'
            )
        }),
        ('Returns', {
            'fields': ('expected_return_percentage', 'expected_return_period'),
            'classes': ('collapse',)
        }),
        ('Tenure & Timeline', {
            'fields': (
                'lock_in_period', 'project_duration',
                'launch_date', 'funding_start_date', 'funding_end_date', 'possession_date'
            ),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('featured_image',)
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Features', {
            'fields': ('amenities', 'highlights'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Visibility', {
            'fields': ('is_featured', 'is_published')
        }),
    )

    readonly_fields = ('created_at', 'updated_at',
                       'approved_at', 'funded_amount')

    inlines = [PropertyUnitInline, PropertyImageInline, PropertyDocumentInline]

    list_per_page = 50

    actions = [
        'approve_properties', 'publish_properties', 'mark_as_featured',
        'mark_live', 'mark_completed'
    ]

    def colored_type(self, obj):
        colors = {
            'residential': '#007bff',   # Blue
            'commercial': '#28a745',    # Green
            'industrial': '#6c757d',    # Gray
            'land': '#ffc107',          # Yellow
            'mixed': '#17a2b8',         # Cyan
        }
        color = colors.get(obj.property_type, '#6c757d')

        icons = {
            'residential': '🏠',
            'commercial': '🏢',
            'industrial': '🏭',
            'land': '🌳',
            'mixed': '🏘️'
        }
        icon = icons.get(obj.property_type, '🏗️')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_property_type_display()
        )
    colored_type.short_description = 'Type'
    colored_type.admin_order_field = 'property_type'

    def colored_status(self, obj):
        colors = {
            'draft': '#6c757d',              # Gray
            'pending_approval': '#ffc107',   # Yellow
            'approved': '#17a2b8',           # Cyan
            'live': '#28a745',               # Green
            'funding': '#007bff',            # Blue
            'funded': '#28a745',             # Green
            'under_construction': '#fd7e14',  # Orange
            'completed': '#6f42c1',          # Purple
            'closed': '#dc3545',             # Red
        }
        color = colors.get(obj.status, '#6c757d')

        icons = {
            'draft': '📝',
            'pending_approval': '⏳',
            'approved': '✓',
            'live': '🟢',
            'funding': '💰',
            'funded': '✓✓',
            'under_construction': '🏗️',
            'completed': '✓',
            'closed': '🔒'
        }
        icon = icons.get(obj.status, '')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 12px; border-radius: 3px; font-size: 11px; font-weight: 600;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    def funding_progress(self, obj):
        percentage = obj.funding_percentage

        # Determine color based on progress
        if percentage >= 100:
            bar_color = '#28a745'  # Green
            text_color = '#28a745'
        elif percentage >= 75:
            bar_color = '#17a2b8'  # Cyan
            text_color = '#17a2b8'
        elif percentage >= 50:
            bar_color = '#ffc107'  # Yellow
            text_color = '#ffc107'
        elif percentage >= 25:
            bar_color = '#fd7e14'  # Orange
            text_color = '#fd7e14'
        else:
            bar_color = '#dc3545'  # Red
            text_color = '#dc3545'

        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background-color: {}; height: 20px; line-height: 20px; '
            'text-align: center; color: white; font-size: 10px; font-weight: 600;">'
            '{}%</div></div>'
            '<span style="font-size: 10px; color: {};">₹{:,.0f} / ₹{:,.0f}</span>',
            min(percentage, 100), bar_color, int(percentage),
            text_color, obj.funded_amount, obj.target_amount
        )
    funding_progress.short_description = 'Funding'

    def price_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #007bff; font-size: 13px;">₹{:,.2f}</span><br>'
            '<span style="font-size: 10px; color: #6c757d;">per unit</span>',
            obj.price_per_unit
        )
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price_per_unit'

    # Admin Actions
    def approve_properties(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending_approval').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} property(ies) approved.')
    approve_properties.short_description = "✓ Approve properties"

    def publish_properties(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} property(ies) published.')
    publish_properties.short_description = "📢 Publish properties"

    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(
            request, f'{updated} property(ies) marked as featured.')
    mark_as_featured.short_description = "⭐ Mark as featured"

    def mark_live(self, request, queryset):
        updated = queryset.filter(status='approved').update(status='live')
        self.message_user(request, f'{updated} property(ies) marked as live.')
    mark_live.short_description = "🟢 Mark as live"

    def mark_completed(self, request, queryset):
        updated = queryset.filter(
            status='under_construction').update(status='completed')
        self.message_user(
            request, f'{updated} property(ies) marked as completed.')
    mark_completed.short_description = "✓ Mark as completed"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'organization', 'developer', 'approved_by'
        ).annotate(
            _unit_count=Count('units'),
            _image_count=Count('images')
        )

    # Custom view for property statistics
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)

        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        metrics = {
            'total_properties': qs.count(),
            'live_properties': qs.filter(status='live').count(),
            'total_funding': qs.aggregate(total=Sum('target_amount'))['total'] or 0,
            'funded_amount': qs.aggregate(total=Sum('funded_amount'))['total'] or 0,
        }

        response.context_data['summary'] = metrics
        return response


# ============================================
# PROPERTY UNIT ADMIN
# ============================================
@admin.register(PropertyUnit)
class PropertyUnitAdmin(admin.ModelAdmin):
    list_display = (
        'unit_number', 'property', 'floor', 'area_display',
        'bedrooms', 'bathrooms', 'price_display', 'colored_status',
        'reserved_by', 'created_at'
    )
    list_filter = (
        'status', 'property__organization', 'bedrooms',
        'bathrooms', 'created_at'
    )
    search_fields = (
        'unit_number', 'property__name', 'reserved_by__username'
    )
    autocomplete_fields = ['property', 'reserved_by']
    ordering = ('property', 'unit_number')

    fieldsets = (
        ('Unit Info', {
            'fields': ('property', 'unit_number', 'floor')
        }),
        ('Specifications', {
            'fields': ('area', 'bedrooms', 'bathrooms', 'price')
        }),
        ('Status', {
            'fields': ('status', 'reserved_by', 'reserved_at')
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'reserved_at')

    list_per_page = 100

    actions = ['mark_available', 'mark_sold']

    def area_display(self, obj):
        return format_html(
            '<span style="font-weight: 600;">{:,.0f}</span> '
            '<span style="font-size: 10px; color: #6c757d;">sq ft</span>',
            obj.area
        )
    area_display.short_description = 'Area'
    area_display.admin_order_field = 'area'

    def price_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #007bff;">₹{:,.2f}</span>',
            obj.price
        )
    price_display.short_description = 'Price'
    price_display.admin_order_field = 'price'

    def colored_status(self, obj):
        colors = {
            'available': '#28a745',  # Green
            'reserved': '#ffc107',   # Yellow
            'sold': '#dc3545',       # Red
            'blocked': '#6c757d',    # Gray
        }
        color = colors.get(obj.status, '#6c757d')

        icons = {
            'available': '✓',
            'reserved': '⏳',
            'sold': '✗',
            'blocked': '🔒'
        }
        icon = icons.get(obj.status, '')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    # Admin Actions
    def mark_available(self, request, queryset):
        updated = queryset.update(
            status='available', reserved_by=None, reserved_at=None)
        self.message_user(request, f'{updated} unit(s) marked as available.')
    mark_available.short_description = "✓ Mark as available"

    def mark_sold(self, request, queryset):
        updated = queryset.update(status='sold')
        self.message_user(request, f'{updated} unit(s) marked as sold.')
    mark_sold.short_description = "🔒 Mark as sold"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('property', 'reserved_by')


# ============================================
# PROPERTY IMAGE ADMIN
# ============================================
@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = (
        'property', 'image_preview', 'caption', 'order', 'created_at'
    )
    list_filter = ('property__organization', 'created_at')
    search_fields = ('property__name', 'caption')
    autocomplete_fields = ['property']
    ordering = ('property', 'order')

    fieldsets = (
        ('Image Info', {
            'fields': ('property', 'image', 'caption', 'order')
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    list_per_page = 50

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px; '
                'border-radius: 5px; border: 2px solid #dee2e6;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('property')


# ============================================
# PROPERTY DOCUMENT ADMIN
# ============================================
@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'property', 'colored_type', 'is_public',
        'uploaded_by', 'created_at'
    )
    list_filter = (
        'document_type', 'is_public', 'created_at'
    )
    search_fields = (
        'title', 'property__name', 'uploaded_by__username'
    )
    autocomplete_fields = ['property', 'uploaded_by']
    ordering = ('-created_at',)

    fieldsets = (
        ('Document Info', {
            'fields': ('property', 'title', 'document_type', 'file')
        }),
        ('Access Control', {
            'fields': ('is_public', 'uploaded_by')
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    list_per_page = 50

    actions = ['make_public', 'make_private']

    def colored_type(self, obj):
        colors = {
            'prospectus': '#007bff',    # Blue
            'legal': '#dc3545',         # Red
            'approval': '#28a745',      # Green
            'plan': '#17a2b8',          # Cyan
            'brochure': '#ffc107',      # Yellow
            'agreement': '#6f42c1',     # Purple
            'other': '#6c757d',         # Gray
        }
        color = colors.get(obj.document_type, '#6c757d')

        icons = {
            'prospectus': '📄',
            'legal': '⚖️',
            'approval': '✓',
            'plan': '📐',
            'brochure': '📰',
            'agreement': '📋',
            'other': '📎'
        }
        icon = icons.get(obj.document_type, '📎')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_document_type_display()
        )
    colored_type.short_description = 'Type'
    colored_type.admin_order_field = 'document_type'

    # Admin Actions
    def make_public(self, request, queryset):
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} document(s) made public.')
    make_public.short_description = "🌐 Make public"

    def make_private(self, request, queryset):
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} document(s) made private.')
    make_private.short_description = "🔒 Make private"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('property', 'uploaded_by')
