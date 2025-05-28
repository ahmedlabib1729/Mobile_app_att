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
    """,
    'author': 'Your Company',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'wizard/generate_sessions_wizard_views.xml',
        'views/enrollment_application_views.xml',
        'views/student_views.xml',
        'views/study_covenant_views.xml',
        'views/quran_class_views.xml',
        'views/session_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}