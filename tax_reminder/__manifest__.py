# -*- coding: utf-8 -*-
{
    'name': 'Tax Declaration Reminder',
    'version': '1.0',
    'summary': 'نظام تذكير الإقرارات الضريبية للعملاء',
    'description': """
        مديول لإدارة وتذكير العملاء بمواعيد الإقرارات الضريبية
        الميزات:
        - إدارة بيانات العملاء
        - جدولة الإقرارات الضريبية
        - إرسال تذكيرات تلقائية بالبريد الإلكتروني
        - رفع وإدارة المستندات المطلوبة
    """,
    'category': 'Accounting',
    'author': 'Your Company',
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/cron_jobs.xml',
        'views/tax_settings_views.xml',
        'views/tax_declaration_views.xml',
        'views/client_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}