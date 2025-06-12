# -*- coding: utf-8 -*-
{
    'name': 'Game Booking Management',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'إدارة حجوزات الألعاب',
    'description': """
        موديول لإدارة حجوزات الألعاب
        - إدارة الألعاب
        - إدارة مواعيد الألعاب
        - إدارة الحجوزات مع تحديد عدد اللاعبين
        - صفحة ويب للحجز المباشر
    """,
    'author': 'Your Company',
    'website': 'http://www.yourcompany.com',
    'depends': ['base', 'web', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/game_views.xml',
        'views/game_schedule_views.xml',
        'views/game_booking_views.xml',
        'views/menu_views.xml',
        'views/website_templates.xml',
        'views/homepage_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'game_booking_management/static/src/css/game_booking.css',
            'game_booking_management/static/src/css/homepage_styles.css',
            'game_booking_management/static/src/js/game_booking.js',
            'game_booking_management/static/src/js/homepage.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}