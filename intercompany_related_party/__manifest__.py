# -*- coding: utf-8 -*-
{
    'name': 'Intercompany Related Party Payments',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Auto-generate intercompany journal entries for related party payments',
    'description': """
Intercompany Related Party Payments
====================================

This module automatically generates journal entries in related companies when 
one company makes a payment on behalf of another company.

Key Features:
------------
* Automatic generation of intercompany journal entries
* Support for multiple companies in the same database
* Configurable related party account mapping
* Prevention of infinite loops
* Detailed logging and error handling
* Audit trail for all intercompany transactions

Use Case Example:
----------------
Company 1 pays 10,000 to supplier Ahmed:
- 2,000 for itself
- 3,000 for Company 2
- 5,000 for Company 3

The module will automatically create journal entries in Company 2 and Company 3
crediting the related party account and debiting the supplier account.

Configuration:
-------------
1. Setup Related Party accounts in all companies
2. Configure the mapping in Accounting > Configuration > Intercompany Configuration
3. Make payments as usual - the system will handle the rest!

Technical:
---------
* Odoo Version: 18.0+
* Python Version: 3.10+
* Dependencies: account
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        # Security
        'security/intercompany_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/intercompany_data.xml',

        # Views
        'views/intercompany_config_views.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}