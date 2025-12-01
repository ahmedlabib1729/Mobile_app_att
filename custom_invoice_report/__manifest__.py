# -*- coding: utf-8 -*-
{
    'name': 'Custom Invoice Report - Dot Matrix Style',
    'version': '18.0.1.4.0',
    'category': 'Accounting',
    'summary': 'Custom Reports: Invoice, Delivery Note, Journal Voucher, Vendor Bill, Payment Receipt',
    'description': """
        Custom Reports Package - Complete Accounting & Inventory Reports
        ==================================================================
        * Custom invoice layout matching dot matrix print style
        * Custom delivery note layout matching dot matrix print style
        * Custom journal voucher report with company logo
        * Custom vendor bill report with company logo
        * Custom customer payment receipt with company logo
        * No header or footer in print
        * VAT summary table
        * Amount in words (English)
        * Declaration and signature section
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account', 'sale', 'stock'],
    'data': [
        'views/report_invoice_custom.xml',
        'views/report_delivery_note.xml',
        'views/report_journal_voucher.xml',
        'views/report_vendor_bill.xml',
        'views/report_payment_receipt.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}