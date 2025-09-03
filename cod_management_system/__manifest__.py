# -*- coding: utf-8 -*-
{
    'name': 'COD Management System',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Manage Cash on Delivery Collections and Settlements',
    'description': """
        COD Management System
        =====================
        Complete solution for managing Cash on Delivery operations:
        - Track COD collections from customers
        - Manage settlements with shipping companies
        - Automated batch processing
        - Integration with accounting
        - Smart scheduling and reminders
    """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'depends': [
        'base',
        'mail',
        'account',
        'shipping_management_system',  # التبعية للنظام الأساسي
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/cod_sequence_data.xml',
        'data/cod_cron_jobs.xml',

        # Views
        'views/cod_collection_views.xml',
        'views/cod_settlement_batch_views.xml',
        'views/shipping_company_cod_views.xml',
        'views/shipment_order_cod_views.xml',
        'views/cod_dashboard_views.xml',


        # Reports
        'reports/cod_settlement_report.xml',

        # Wizards
        #'wizard/cod_settlement_wizard_views.xml',

        'views/cod_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}