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
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/member_sequences.xml',
        'data/member_cron.xml',
        'views/headquarters_views.xml',
        'views/departments_views.xml',
        'views/clubs_views.xml',
        'views/student_family_views.xml',  # ملف الطلاب والعائلات الجديد
        'views/club_registration_views.xml',
        'views/member_views.xml',
        'views/booking_registration_views.xml',
        'views/headquarters_menu.xml',  # القوائم في النهاية
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}