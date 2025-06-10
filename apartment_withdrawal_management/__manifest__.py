# -*- coding: utf-8 -*-
{
    'name': 'Apartment Withdrawal Management',
    'version': '16.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Automatic apartment withdrawal for overdue installments',
    'description': """
Apartment Withdrawal Management
===============================

This module automatically withdraws apartments when installments are overdue for a specified period.

Features:
- Configurable withdrawal period (months)
- Automatic status change for units and contracts
- Monitoring and tracking system
- Automatic restoration on payment
- Notification system
- Reporting capabilities
- Excel export functionality

The system works by:
1. Daily monitoring of overdue installments
2. Automatic withdrawal after configured months
3. Status tracking and history
4. Automatic restoration when payment is made
5. Comprehensive reporting with Excel export
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['itsys_real_estate', 'base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/withdrawal_monitor_views.xml',
        'views/ownership_contract_views.xml',
        'views/building_unit_views.xml',
        'views/withdrawal_report_views.xml',
        'views/menu_views.xml',
        'data/cron_data.xml',
        'data/mail_template_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
}