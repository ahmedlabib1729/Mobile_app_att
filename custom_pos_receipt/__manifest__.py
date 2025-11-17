# -*- coding: utf-8 -*-
{
    'name': 'POS Receipt Custom - Professional Design',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Custom professional POS receipt design for Odoo 18',
    'description': """
        Professional POS Receipt Customization
        =======================================
        
        Features:
        * Custom receipt layout with company logo
        * Enhanced company information display
        * Product line numbering
        * Discount display
        * Tax breakdown
        * Barcode support
        * Custom footer text
        * Bilingual support (Arabic/English)
    """,
    'author': 'Ahmed - ERP Accounting',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_receipt_custom/static/src/xml/receipt_template.xml',
            'pos_receipt_custom/static/src/js/receipt_override.js',
            'pos_receipt_custom/static/src/css/receipt_style.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
