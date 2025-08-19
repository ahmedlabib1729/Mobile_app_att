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
        - Student portal for online sessions
    """,
    'author': 'Your Company',
    'depends': ['base', 'mail', 'hr', 'website', 'portal'],  # إضافة portal
    'data': [
        'security/portal_security.xml',  # أولاً: security rules للبورتال
        'security/teacher_security.xml',  # ثانياً: تعريف المجموعات الجديدة
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        #'data/portal_email_template.xml',  # إضافة قوالب البريد الإلكتروني
        #'data/meeting_mail_template.xml',
        'wizard/generate_sessions_wizard_views.xml',
        'wizard/start_meeting_wizard_views.xml',
        'wizard/enrollment_link_wizard_views.xml',
        'views/enrollment_application_views.xml',
        'views/student_views.xml',
        'views/hr_employee_views.xml',
        'views/website_homepage.xml',



        'views/study_covenant_views.xml',
        'views/quran_class_views.xml',
        'views/session_views.xml',
        'views/menu_views.xml',
        'views/website_enrollment_templates.xml',
        'views/website_menu.xml',
        'views/portal_error_page.xml',  # إضافة صفحة الخطأ للبورتال
        'views/meeting_redirect_template.xml',
        'views/portal_dashboard_placeholder.xml',
        'views/portal_navigation_templates.xml', # إضافة placeholder templates
        'views/website_programs.xml',

    ],
    'assets': {
        'web.assets_frontend': [
            'quran_center/static/src/css/website_enrollment.css',
            'quran_center/static/src/css/portal_base.css',  # إضافة CSS البورتال
            'quran_center/static/src/js/website_enrollment.js',
            'quran_center/static/src/js/portal_base.js',  # إضافة JS البورتال
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}