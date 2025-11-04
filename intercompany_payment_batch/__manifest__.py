# -*- coding: utf-8 -*-
{
    'name': 'Intercompany Payment Batch',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Centralized payment processing for multi-company vendor bills',
    'description': """
        Intercompany Payment Batch Management
        ======================================
        This module allows centralized payment processing for multi-company environments.
        
        Features:
        ---------
        * Process vendor payments from a central company
        * Automatically generate intercompany journal entries
        * Batch payment reconciliation across companies
        * Support for multiple vendor bills in single payment
        * Automatic distribution based on intercompany configuration
        * Full audit trail and tracking
        
        Workflow:
        ---------
        1. Create payment batch and select vendor bills from multiple companies
        2. Confirm the batch to validate selections
        3. Post payment to create central payment and intercompany entries
        4. Reconcile to match payments with vendor bills
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'account_payment', 
        'mail',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/sequence_data.xml',
        
        # Wizards
        'wizard/payment_batch_wizard_views.xml',
        'wizard/invoice_selection_wizard_views.xml',
        
        # Views
        'views/payment_batch_views.xml',
        'views/account_move_views.xml',
        'views/intercompany_config_views.xml',
        'views/payment_batch_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'intercompany_payment_batch/static/src/**/*',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
