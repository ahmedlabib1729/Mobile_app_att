{
    'name': 'Journal User Access Control',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'التحكم في صلاحيات الجورنال على مستوى المستخدم',
    'description': """
        هذا المديول يسمح بـ:
        - تحديد المستخدمين المسموح لهم برؤية كل جورنال
        - إخفاء الجورنالات عن المستخدمين غير المصرح لهم
        - إدارة سهلة للصلاحيات من واجهة المستخدم
    """,
    'author': 'Your Company',
    'depends': ['account', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/account_journal_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}