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
        'account',  # إضافة account للفواتير
        'sale',
        'website',
        'portal',# اختياري: لو عايز تستخدم بعض features من المبيعات
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/demo_shipping_data.xml',
        'views/shipment_views.xml',
        'views/shipment_invoice_views.xml',
        'views/shipping_company_views.xml',
        'views/broker_fees_views.xml',
        'views/customer_pricing_views.xml',
        'views/website_templates.xml',
        'views/portal_templates.xml',
       # 'views/portal_navigation_templates.xml',
'views/torood_homepage.xml',
    ],

'assets': {
    'web.assets_frontend': [
        'shipping_management_system/static/src/css/portal_style.css',
        'shipping_management_system/static/src/css/invoice_portal.css',
    ],
},
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}