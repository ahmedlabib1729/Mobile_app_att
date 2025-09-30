{
    'name': 'Payment Provider - Cash on Delivery',
    'version': '17.0.1.0.0',
    'category': 'Payment',
    'summary': 'Cash on Delivery payment provider with country-specific fees',
    'description': """
        Cash on Delivery (COD) Payment Provider
        =========================================

        This module adds a Cash on Delivery payment method with:
        - Country-specific fee configuration
        - Fixed or percentage-based fees
        - Minimum/Maximum order limits per country
        - Automatic fee addition to orders
        - Multi-language instructions support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'payment',
        'website_sale',
        'account',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data
        'data/payment_provider_data.xml',

        # Views
        'views/payment_provider_views.xml',
        'views/cod_country_fee_views.xml',
        'views/payment_templates.xml',
#'views/payment_cod_notice.xml',

    ],
    'assets': {
        'web.assets_frontend': [
            'payment_cod/static/src/css/payment_cod.css',
            'payment_cod/static/src/js/cod_dynamic_notice.js',
            'payment_cod/static/src/js/payment_form.js',
            'payment_cod/static/src/js/cod_payment.js',
            'payment_cod/static/src/js/cod_fee_display.js',

        ],
    },
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}