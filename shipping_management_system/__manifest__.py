# -*- coding: utf-8 -*-
{
    'name': 'Shipment Management System',
    'version': '1.0',
    'category': 'Logistics',
    'summary': 'Complete Shipment Management System for Shipping Intermediaries',
    'description': """
        Shipment Management System
        ===========================
        This module helps manage shipments for shipping intermediaries including:
        - Customer shipment requests
        - Product details and categorization
        - Shipping company selection
        - Pricing and profit tracking
        - Shipment status tracking
    """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': [
        'base',
        'mail',
        'product',
        'account',
        'sale',
        'website',
        'portal',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/shipment_views.xml',
        'views/shipment_invoice_views.xml',
        'views/shipping_company_views.xml',
        'views/broker_fees_views.xml',
        'views/customer_pricing_views.xml',
        'views/website_templates.xml',
        'views/portal_templates.xml',
        'views/torood_homepage.xml',
        'views/global_navbar.xml',
        'views/global_footer.xml',
        'views/governorate_pricing_views.xml',
        'views/pickup_configuration_views.xml',
        'views/shipment_dashboard_view.xml',
        'views/shipment_status_menus.xml',
    ],
    'assets': {
    'web.assets_backend': [
        # Dashboard files - ترتيب مهم!
        'shipping_management_system/static/src/css/dashboard.css',
        'shipping_management_system/static/src/xml/shipment_dashboard.xml',
        'shipping_management_system/static/src/js/shipment_dashboard.js',
    ],
    'web.assets_frontend': [
        'shipping_management_system/static/src/css/portal_style.css',
        'shipping_management_system/static/src/css/torood_theme.css',
        'shipping_management_system/static/src/css/invoice_portal.css',
    ],
},

    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'uninstall_hook': 'uninstall_hook',
}