{
    'name': 'HallWay Educational System',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Student Application and Management System for Educational Centers',
    'description': """
        HallWay Educational System
        ==========================

        This module provides:
        - Student application management
        - Student records management
        - Automatic student detection based on Passport/Emirates ID
        - Course enrollment tracking
        - Multi-language course support (Arabic/English)

        Features:
        ---------
        * Create and manage student applications
        * Automatically detect existing students
        * Link applications to students
        * Track vocational qualifications
        * Manage language course enrollments
        * Schedule preferences
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail', 'web'],
    'data': [
        # Security
        'security/hallway_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence.xml',
        'data/week_days_data.xml',

        # Views
        'views/hallway_student_views.xml',
        'views/student_application_views.xml',

    ],
    'demo': [
        # 'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            # 'HallWay_System/static/src/css/hallway.css',
        ],
    },
}