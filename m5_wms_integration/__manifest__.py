# -*- coding: utf-8 -*-
{
    'name': 'M5 WMS Integration',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Warehouse',
    'summary': 'Integration with M5 WMS (Warehouse Management System)',
    'description': """
        M5 WMS Integration
        ==================
        This module integrates Odoo with M5 WMS for warehouse management.

        Features:
        ---------
        * Automatic order submission to M5 WMS
        * Support for multiple warehouses
        * Real-time order status tracking
        * COD support
        * Product synchronization
        * Manual and automatic order creation
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
        # Security - تحميل المجموعات أولاً
        'security/m5_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/m5_cron.xml',

        # Views
        'views/m5_config_views.xml',
        'views/m5_order_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_warehouse_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
        'views/menu_views.xml',

        # Wizards
        'wizards/m5_order_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}