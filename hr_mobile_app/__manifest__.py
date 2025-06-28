{
    'name': 'Mobile App Access for Employees',
    'version': '1.0',
    'summary': 'Provides employees with access via the mobile app',
    'description': """
A module that allows employees to access Odoo data via a mobile application,
with permission management, security, attendance logging, and request management.

Features:
- Add username and PIN for each employee
- Encrypt employee credentials
- Custom API interface for the mobile app
- Ability to enable/disable employee access from the app
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Human Resources',
    'depends': [
        'base',
        'hr',
        'hr_attendance', 'hr_holidays' , 'hr_payroll'
    ],
    'data': [
        'security/mobile_security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        #'views/hr_mobile_app_settings_views.xml',
        'views/hr_announcement_views.xml',
        'views/hr_leave_mobile_views.xml',
        'data/mobile_user_data.xml',
        # 'data/hr_leave_mobile_data.xml',
        'data/announcement_data.xml',
        'views/hr_office_location_views.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}