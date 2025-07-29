# -*- coding: utf-8 -*-
{
    'name': 'Porter Express Integration',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Integration with Porter Express Shipping Service',
    'description': """
        Porter Express Shipping Integration
        ===================================
        This module integrates Odoo with Porter Express shipping service API.

        Features:
        ---------
        * Automatic shipment creation
        * Label printing  
        * Shipment tracking
        * Pickup scheduling
        * COD management
        * Multi-package support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'sale',
        'stock',
        'delivery',
        'contacts',
        'mail',
    ],
    'data': [
        # Security
        'security/porter_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/delivery_carrier_data.xml',
        'data/porter_cron.xml',

        # Views
        'views/porter_config_views.xml',
        'views/porter_shipment_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
        'views/menu_views.xml',
'views/porter_area_views.xml',

        # Wizards
        'wizards/porter_shipment_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}