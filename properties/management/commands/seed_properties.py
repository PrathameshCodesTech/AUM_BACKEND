from django.core.management.base import BaseCommand
from properties.models import Property, PropertyUnit
from accounts.models import User
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seed sample properties for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write("🌱 Seeding sample properties...")

        # Get or create a developer user
        developer, _ = User.objects.get_or_create(
            username='developer_user',
            defaults={
                'phone': '+919999999999',
                'email': 'developer@assetkart.com',
            }
        )

        properties_data = [
            {
                'name': 'Lodha Park - Premium Apartments',
                'slug': 'lodha-park-mumbai',
                'description': 'Luxury apartments in the heart of Mumbai with world-class amenities including swimming pool, gym, and 24/7 security.',
                'builder_name': 'Lodha Group',
                'property_type': 'residential',
                'address': 'Lower Parel, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'locality': 'Lower Parel',
                'country': 'India',
                'pincode': '400013',
                'total_area': Decimal('50000'),
                'total_units': 30,
                'available_units': 30,
                'price_per_unit': Decimal('1666666.67'),
                'minimum_investment': Decimal('100000'),
                'maximum_investment': Decimal('5000000'),
                'target_amount': Decimal('50000000'),
                'funded_amount': Decimal('0'),
                'expected_return_percentage': Decimal('13.2'),
                'gross_yield': Decimal('2.333'),
                'potential_gain': Decimal('13.2'),
                'expected_return_period': 36,
                'lock_in_period': 12,
                'project_duration': 36,
                'status': 'live',
                'is_published': True,
                'is_public_sale': True,
                'is_presale': False,
                'amenities': ['Swimming Pool', 'Gym', '24/7 Security', 'Kids Play Area', 'Club House'],
                'highlights': ['Prime Location', 'Gated Community', 'Premium Finishes'],
            },
            {
                'name': 'Prestige Lakeside - Commercial Spaces',
                'slug': 'prestige-lakeside-bangalore',
                'description': 'Modern commercial spaces perfect for offices and retail. Located in prime business district of Bangalore.',
                'builder_name': 'Prestige Group',
                'property_type': 'commercial',
                'address': 'Whitefield, Bangalore',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'locality': 'Whitefield',
                'country': 'India',
                'pincode': '560066',
                'total_area': Decimal('100000'),
                'total_units': 25,
                'available_units': 25,
                'price_per_unit': Decimal('4000000'),
                'minimum_investment': Decimal('100000'),
                'maximum_investment': Decimal('10000000'),
                'target_amount': Decimal('100000000'),
                'funded_amount': Decimal('0'),
                'expected_return_percentage': Decimal('11.23'),
                'gross_yield': Decimal('5.83'),
                'potential_gain': Decimal('15.0'),
                'expected_return_period': 24,
                'lock_in_period': 6,
                'project_duration': 24,
                'status': 'live',
                'is_published': True,
                'is_public_sale': True,
                'is_presale': False,
                'amenities': ['Parking', 'Power Backup', 'High Speed Elevators', 'Food Court'],
                'highlights': ['Tech Park Adjacent', 'Metro Connected', 'Premium Location'],
            },
            {
                'name': 'DLF Garden City - Residential Plots',
                'slug': 'dlf-garden-city-gurgaon',
                'description': 'Premium residential plots in DLF Garden City. Ideal for building your dream home.',
                'builder_name': 'DLF Limited',
                'property_type': 'land',
                'address': 'Sector 92, Gurgaon',
                'city': 'Gurgaon',
                'state': 'Haryana',
                'locality': 'Sector 92',
                'country': 'India',
                'pincode': '122505',
                'total_area': Decimal('30000'),
                'total_units': 30,
                'available_units': 30,
                'price_per_unit': Decimal('1000000'),
                'minimum_investment': Decimal('100000'),
                'maximum_investment': Decimal('3000000'),
                'target_amount': Decimal('30000000'),
                'funded_amount': Decimal('0'),
                'expected_return_percentage': Decimal('13.2'),
                'gross_yield': Decimal('2.333'),
                'potential_gain': Decimal('13.2'),
                'expected_return_period': 48,
                'lock_in_period': 24,
                'project_duration': 48,
                'status': 'live',
                'is_published': True,
                'is_public_sale': True,
                'is_presale': False,
                'amenities': ['Gated Community', 'Water Supply', 'Electricity', 'Roads'],
                'highlights': ['DTCP Approved', 'Clear Title', 'Ready to Build'],
            },
            {
                'name': 'Godrej Emerald - Smart Homes',
                'slug': 'godrej-emerald-pune-presale',
                'description': 'Smart homes with modern amenities in Godrej Emerald. Exclusive presale opportunity with limited units.',
                'builder_name': 'Godrej Properties',
                'property_type': 'residential',
                'address': 'Hinjewadi Phase 2, Pune',
                'city': 'Pune',
                'state': 'Maharashtra',
                'locality': 'Hinjewadi Phase 2',
                'country': 'India',
                'pincode': '411057',
                'total_area': Decimal('40000'),
                'total_units': 20,
                'available_units': 20,
                'price_per_unit': Decimal('2000000'),
                'minimum_investment': Decimal('100000'),
                'maximum_investment': Decimal('4000000'),
                'target_amount': Decimal('40000000'),
                'funded_amount': Decimal('0'),
                'expected_return_percentage': Decimal('18.5'),
                'gross_yield': Decimal('4.2'),
                'potential_gain': Decimal('20.0'),
                'expected_return_period': 30,
                'lock_in_period': 12,
                'project_duration': 30,
                'status': 'funding',
                'is_published': True,
                'is_public_sale': False,
                'is_presale': True,
                'amenities': ['Smart Home Features', 'Solar Panels', 'Rain Water Harvesting', 'EV Charging'],
                'highlights': ['Green Building', 'IT Hub Proximity', 'Pre-Launch Pricing'],
            },
            {
                'name': 'Oberoi Realty - Luxury Villas',
                'slug': 'oberoi-realty-villas-mumbai',
                'description': 'Ultra-luxury villas with private gardens and swimming pools. Exclusive gated community with world-class amenities.',
                'builder_name': 'Oberoi Realty',
                'property_type': 'residential',
                'address': 'Goregaon East, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'locality': 'Goregaon East',
                'country': 'India',
                'pincode': '400063',
                'total_area': Decimal('150000'),
                'total_units': 10,
                'available_units': 10,
                'price_per_unit': Decimal('25000000'),
                'minimum_investment': Decimal('1000000'),
                'maximum_investment': Decimal('25000000'),
                'target_amount': Decimal('250000000'),
                'funded_amount': Decimal('0'),
                'expected_return_percentage': Decimal('12.8'),
                'gross_yield': Decimal('3.5'),
                'potential_gain': Decimal('14.5'),
                'expected_return_period': 60,
                'lock_in_period': 36,
                'project_duration': 60,
                'status': 'live',
                'is_published': True,
                'is_featured': True,
                'is_public_sale': True,
                'is_presale': False,
                'amenities': ['Private Pool', 'Private Garden', 'Club House', 'Concierge Service', 'Spa'],
                'highlights': ['Ultra Luxury', 'Gated Community', 'Airport Road', 'Premium Location'],
            },
        ]

        created_count = 0

        for prop_data in properties_data:
            # Create property
            property_obj, created = Property.objects.get_or_create(
                slug=prop_data['slug'],
                defaults={
                    **prop_data,
                    'developer': developer
                }
            )

            if created:
                # Create property units
                total_units = prop_data['total_units']
                for i in range(1, total_units + 1):
                    PropertyUnit.objects.create(
                        property=property_obj,
                        unit_number=f"UNIT-{i:03d}",
                        area=Decimal('1000'),
                        price=prop_data['price_per_unit'],
                        status='available'
                    )
                
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Created: {property_obj.name} ({property_obj.builder_name}) - {total_units} units"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Already exists: {property_obj.name}"
                    )
                )

        self.stdout.write("\n" + "="*60)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Seeding complete! Created {created_count} properties"
            )
        )
        self.stdout.write(f"📊 Total properties in database: {Property.objects.count()}")
        self.stdout.write("="*60 + "\n")