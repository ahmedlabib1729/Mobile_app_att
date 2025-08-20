# -*- coding: utf-8 -*-
{
    'name': 'Aramex Shipping Integration',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Integration with Aramex Shipping Service API',
    'description': """
        Aramex Shipping Integration
        ==========================
        This module integrates Odoo with Aramex shipping service SOAP API.

        Features:
        ---------
        * Automatic shipment creation
        * AWB label printing  
        * Shipment tracking
        * Pickup scheduling
        * COD (Cash on Delivery) management
        * Multi-package support
        * Multi-country configuration
        * Automatic rate calculation
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
    'external_dependencies': {
        'python': ['zeep', 'requests'],
    },
    'data': [
        # Security
        #'security/aramex_security.xml',
        'security/ir.model.access.csv',

        # Data
       # 'data/delivery_carrier_data.xml',
        #'data/aramex_cron.xml',

        # Views
        'views/aramex_config_views.xml',
        'views/aramex_shipment_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
       #'views/menu_views.xml',

        # Wizards
        'wizards/aramex_shipment_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}