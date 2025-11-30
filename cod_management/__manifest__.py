# -*- coding: utf-8 -*-
{
    'name': 'COD Management',
    'version': '1.0.0',
    'category': 'Shipping',
    'summary': 'Complete COD tracking and settlement system',
    'description': """
        COD Management System
        =====================
        - Track COD status from collection to settlement
        - Calculate net amounts after all deductions
        - Manage settlements with shipping companies
        - Customer COD balance tracking
    """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': ['shipping_management_system'],
    'data': [
        'security/ir.model.access.csv',
        'data/cod_cron.xml',
        'views/shipment_cod_views.xml',
        'views/cod_batch_views.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}