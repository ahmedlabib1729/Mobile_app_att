{
    'name': 'Quran Memorization Center',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Online Quran Memorization Center Management',
    'description': """
        This module helps manage online Quran memorization center including:
        - Student enrollment applications
        - Student information management
        - Memorization progress tracking
        - Online enrollment form on website
    """,
    'author': 'Your Company',
    'depends': ['base', 'mail', 'hr', 'website'],  # إضافة website
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        #'data/meeting_mail_template.xml',  # إضافة قالب البريد
        'wizard/generate_sessions_wizard_views.xml',
        'wizard/start_meeting_wizard_views.xml',
        'views/enrollment_application_views.xml',
        'views/student_views.xml',

        'views/study_covenant_views.xml',
        'views/quran_class_views.xml',
        'views/session_views.xml',
        'views/menu_views.xml',
        'views/website_enrollment_templates.xml',
        'views/website_menu.xml',



    ],
    'assets': {
        'web.assets_frontend': [
            'quran_center/static/src/css/website_enrollment.css',  # ملف CSS اختياري

            'quran_center/static/src/js/website_enrollment.js',    # ملف JS اختياري
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}