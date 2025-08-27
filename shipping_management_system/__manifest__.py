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
    'depends': ['base', 'mail', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/demo_shipping_data.xml',
        'views/shipment_views.xml',
        'views/shipping_company_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}