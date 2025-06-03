# -*- coding: utf-8 -*-
{
    'name': 'إدارة النادي الصغير',
    'version': '1.0',
    'category': 'Club Management',
    'summary': 'موديول بسيط لإدارة النادي الصغير',
    'description': """
        موديول إدارة النادي الصغير
        ========================
        يحتوي على:
        - إدارة اللاعبين
        - إدارة أولياء الأمور
        - إدارة الألعاب الرياضية
    """,
    'author': 'Your Name',
    'website': 'http://www.yourcompany.com',
    'depends': ['base', 'mail', 'hr', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/player_views.xml',
        'views/parent_views.xml',
        'views/sport_views.xml',
        'views/subscription_views.xml',
        'views/payment_receipt_views.xml',
        'views/subscription_request_views.xml',
        'wizard/payment_wizard_views.xml',
        'wizard/subscription_request_reject_wizard_views.xml',
        'views/website_subscription_templates.xml',
        'views/menu_views.xml',  # يجب أن يكون آخر ملف
        'data/ir_cron.xml',
    ],

    'assets': {
    'web.assets_frontend': [
        'club/static/src/js/subscription_request.js',
    ],
},
    'installable': True,
    'application': True,
    'auto_install': False,
}