# -*- coding: utf-8 -*-
{
    'name': "Club Management System",
    'summary': """نظام إدارة النوادي الرياضية""",
    'description': """
        نظام متكامل لإدارة النوادي يشمل:
        - إدارة العضويات
        - إدارة الأعضاء
        - نظام الحجوزات
        - النظام المالي
        - إدارة الأنشطة والتدريب
    """,
    'author': "Your Company",
    'website': "https://www.yourcompany.com",
    'category': 'Sports/Club',
    'version': '18.0.1.0.0',
    'depends': ['base', 'mail', 'account', 'contacts'],
    'data': [
        # Security
        'security/club_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/membership_data.xml',

        # Views - Actions first, then menus
        'views/membership_type_views.xml',
        'views/membership_views.xml',
        'views/sport_activity_views.xml',
        'views/member_activity_views.xml',
        'views/menu_views.xml',

        # Reports
        # 'reports/membership_card_report.xml',
    ],
    'demo': [
        # 'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}