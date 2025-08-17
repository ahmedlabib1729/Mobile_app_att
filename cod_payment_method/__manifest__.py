# -*- coding: utf-8 -*-
{
    'name': 'Cash on Delivery Payment Method',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Add Cash on Delivery (COD) payment method with configurable fees and country restrictions',
    'description': """
Cash on Delivery Payment Method
===============================

This module adds a Cash on Delivery (COD) payment method to your Odoo e-commerce and sales.

Key Features:
-------------
* Cash on Delivery payment provider
* Configurable fees (fixed amount or percentage)
* Country-specific restrictions
* Different fees per country
* Automatic fee calculation and order line addition
* Minimum and maximum order amount limits
* Integration with sales orders and e-commerce

Configuration:
--------------
1. Go to Invoicing/Payment Providers
2. Configure the COD payment provider
3. Set up fees and country restrictions
4. Define minimum/maximum order amounts

Usage:
------
* Customers can select COD during checkout
* Fees are automatically added to orders
* Orders are marked with COD badge
* Special COD orders report available
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'payment',
        'website_sale',
        'product',
        'account',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data files
        'data/payment_provider_data.xml',
        'data/product_data.xml',

        # Views
        #'views/assets.xml',
        'views/payment_actions.xml',
        'views/payment_provider_views.xml',
        'views/cod_thank_you_template.xml',
        'views/payment_method_views.xml',
        'views/sale_order_views.xml',
        'views/res_country_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
           'cod_payment_method/static/src/js/payment_cod_mixin.js',
            'cod_payment_method/static/src/js/cod_custom_message.js',

           #'cod_payment_method/static/src/js/payment_form.js',

            'cod_payment_method/static/src/css/payment_cod.css',
        ],
        'web.assets_backend': [
            'cod_payment_method/static/src/css/payment_cod.css',
        ],
    },

    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,

}