# -*- coding: utf-8 -*-
{
    'name': 'إدارة مقرات الجمعية الخيرية',
    'version': '18.0.1.0.3',
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
    'author': 'ِAhmed Labib',
    'website': 'https://www.yourwebsite.com',
    'depends': ['base', 'mail', 'contacts', 'account', 'base_automation', 'website', 'portal', 'payment'],
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
        'views/wizard_review_registration_views.xml',
        'views/nursery_registration_views.xml',
        'views/nursery_child_profile_views.xml',
        'views/nursery_registration_wizard.xml',
        'views/ladies_workshop_views.xml',
        'views/nursery_class_config_views.xml',
        'views/nursery_payment_schedule_views.xml',
        'views/nursery_cheque_wizard_views.xml',
        'views/headquarters_menu.xml', # القوائم في النهاية


        # Website files
        'views/website_templates.xml',
        'views/website_menu.xml',

    ],


'assets': {
        'web.assets_frontend': [
            'charity_clubs/static/src/css/website_registration.css',

            'charity_clubs/static/src/css/website_registration.css',

            # External Libraries - تحميل SweetAlert2
            ('include', 'https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css'),

            'charity_clubs/static/src/js/website_registration_simple.js',
            'charity_clubs/static/src/js/website_registration_language.js',
            #'charity_clubs/static/src/js/language_switcher.js',
            'charity_clubs/static/src/js/website_registration_language.js',
        ],

    },

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',


    'languages': ['ar_001', 'en_US'],
    'i18n': True,
}