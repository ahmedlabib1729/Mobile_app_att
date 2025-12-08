# -*- coding: utf-8 -*-
{
    'name': 'Accounting Reports',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Reporting',
    'summary': 'Advanced Accounting Reports with Modern UI',
    'description': """
        Accounting Reports Module
        ==========================
        Modern and Interactive Accounting Reports:
        
        * General Ledger
        * Partner Ledger
        * Trial Balance (Coming Soon)
        * Aged Receivable (Coming Soon)
        * Aged Payable (Coming Soon)
        
        Features:
        ---------
        * Modern Dashboard Style UI
        * Interactive Tree View
        * Multiple Filters
        * Export to Excel
        * Print to PDF
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Views
        'views/general_ledger_action.xml',
        'views/partner_ledger_action.xml',
        'views/trial_balance_action.xml',
        'views/aged_receivable_action.xml',
        'views/aged_payable_action.xml',
        'views/tax_report_action.xml',
        'views/profit_loss_action.xml',
        'views/balance_sheet_action.xml',
        
        # Menu
        'data/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # CSS
            'accounting_reports/static/src/css/report_common.css',
            'accounting_reports/static/src/css/general_ledger.css',
            'accounting_reports/static/src/css/partner_ledger.css',
            'accounting_reports/static/src/css/trial_balance.css',
            'accounting_reports/static/src/css/aged_reports.css',
            'accounting_reports/static/src/css/tax_report.css',
            'accounting_reports/static/src/css/profit_loss.css',
            'accounting_reports/static/src/css/balance_sheet.css',
            
            # JS
            'accounting_reports/static/src/js/general_ledger.js',
            'accounting_reports/static/src/js/partner_ledger.js',
            'accounting_reports/static/src/js/trial_balance.js',
            'accounting_reports/static/src/js/aged_receivable.js',
            'accounting_reports/static/src/js/aged_payable.js',
            'accounting_reports/static/src/js/tax_report.js',
            'accounting_reports/static/src/js/profit_loss.js',
            'accounting_reports/static/src/js/balance_sheet.js',
            
            # XML Templates
            'accounting_reports/static/src/xml/general_ledger.xml',
            'accounting_reports/static/src/xml/partner_ledger.xml',
            'accounting_reports/static/src/xml/trial_balance.xml',
            'accounting_reports/static/src/xml/aged_receivable.xml',
            'accounting_reports/static/src/xml/aged_payable.xml',
            'accounting_reports/static/src/xml/tax_report.xml',
            'accounting_reports/static/src/xml/profit_loss.xml',
            'accounting_reports/static/src/xml/balance_sheet.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
