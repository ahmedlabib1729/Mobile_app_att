# -*- coding: utf-8 -*-
{
    'name': 'IW Express Integration',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Integration with IW Express Shipping Service',
    'description': """
        IW Express Shipping Integration
        ===============================
        This module integrates Odoo with IW Express shipping service API.

        Features:
        ---------
        * Automatic consignment creation
        * Shipping label generation and printing
        * Real-time shipment tracking
        * COD (Cash on Delivery) management
        * Multi-piece shipment support
        * Support for both domestic and international shipping
        * Webhook integration for status updates
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'sale',
        'stock',
        'delivery',
        'sale_stock',  # مطلوب للعلاقة بين sale و stock
        'contacts',
        'mail',
    ],
    'data': [
        # Security
        'security/iw_security.xml',
        'security/ir.model.access.csv',
        'security/iw_security_rules.xml',  # يجب أن يكون بعد تحميل الـ models

        # Data
        'data/delivery_carrier_data.xml',
        'data/iw_cron.xml',

        # Views
        'views/iw_config_views.xml',
        'views/iw_shipment_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
        'views/menu_views.xml',

        # Wizards
        'wizards/iw_shipment_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}