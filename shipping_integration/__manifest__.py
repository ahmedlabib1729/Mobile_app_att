# shipping_integration/__manifest__.py
{
    'name': 'Shipping Integration System',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Generic shipping integration system for multiple providers',
    'description': """
        This module provides a flexible shipping integration system that allows:
        - Easy integration with multiple shipping providers
        - Dynamic field mapping
        - Provider configuration without coding
        - Automatic shipment creation and tracking
    """,
    'author': 'Your Company',
    'depends': ['sale', 'delivery', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/shipping_provider_views.xml',
        'views/sale_order_views.xml',
        'views/create_shipment_wizard_views.xml',
        'data/shipping_provider_data.xml',
        'data/porter_field_mappings.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}