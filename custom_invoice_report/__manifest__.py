# -*- coding: utf-8 -*-
{
    'name': 'Custom Invoice Report - Dot Matrix Style',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom Invoice Report with Dot Matrix Print Style - No Header/Footer',
    'description': """
        Custom Invoice Report Template
        ================================
        * Custom invoice layout matching dot matrix print style
        * No header or footer in print
        * VAT summary table
        * Amount in words (English)
        * Declaration and signature section
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account', 'sale'],
    'data': [
        'views/report_invoice_custom.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
