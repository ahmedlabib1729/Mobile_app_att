{
    'name': 'Mobile App Access for Employees',
    'version': '1.0',
    'summary': 'توفير الوصول للموظفين من خلال تطبيق الموبايل',
    'description': """
وحدة تسمح للموظفين بالوصول إلى بيانات Odoo من خلال تطبيق المحمول
مع إدارة الصلاحيات والأمان وتسجيل الحضور والطلبات.

الميزات:
- إضافة اسم مستخدم ورمز PIN لكل موظف
- تشفير بيانات الاعتماد للموظف
- واجهة API مخصصة للتطبيق المحمول
- إمكانية تفعيل/تعطيل وصول الموظف من التطبيق
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Human Resources',
    'depends': [
        'base',
        'hr',
        'hr_attendance', 'hr_holidays'
    ],
    'data': [
        'security/mobile_security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_mobile_app_settings_views.xml',
        'views/hr_announcement_views.xml',
        #'views/hr_leave_mobile_views.xml',
        'data/mobile_user_data.xml',
        #'data/hr_leave_mobile_data.xml',
        'data/announcement_data.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

