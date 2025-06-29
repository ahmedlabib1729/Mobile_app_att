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
        - تسجيلات النوادي
        - حجوزات الأقسام
        - ملفات الطلاب والعائلات
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['base', 'mail', 'contacts', 'account', 'base_automation', 'website', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'data/member_sequences.xml',
        'data/member_cron.xml',

        'views/headquarters_views.xml',
        'views/departments_views.xml',
        'views/ladies_program_views.xml',  # أضف هذا السطر هنا
        'views/clubs_views.xml',
        'views/student_family_views.xml',
        'views/club_registration_views.xml',
        'views/member_views.xml',
        'views/booking_registration_views.xml',
        'views/headquarters_menu.xml', # القوائم في النهاية


        # Website files
        'views/website_templates.xml',
        'views/website_menu.xml',

    ],

'assets': {
        'web.assets_frontend': [
            'charity_clubs/static/src/css/website_registration.css',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}