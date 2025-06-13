# -*- coding: utf-8 -*-
{
    'name': 'إدارة مقرات الجمعية الخيرية',
    'version': '1.0',
    'category': 'Charity/Management',
    'summary': 'إدارة المقرات والأقسام والنوادي للجمعية الخيرية',
    'description': """
        موديول لإدارة:
        - المقرات الخاصة بالجمعية الخيرية
        - الأقسام داخل كل مقر
        - النوادي داخل كل قسم
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/headquarters_views.xml',
        'views/departments_views.xml',
        'views/clubs_views.xml',
        'views/registrations_views.xml',
        'views/club_registration_views.xml',
        'views/booking_registration_views.xml',
        'views/headquarters_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}