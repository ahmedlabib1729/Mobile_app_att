# -*- coding: utf-8 -*-
{
    'name': 'النوادي الخيرية - Charity Clubs',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'إدارة النوادي التعليمية والبرامج التربوية للجمعيات الخيرية',
    'description': """
نظام إدارة النوادي الخيرية
============================

نظام متكامل لإدارة النوادي التعليمية والتربوية التابعة للجمعيات الخيرية

المميزات الرئيسية:
-----------------
* إدارة متعددة للنوادي والفروع
* إنشاء وإدارة البرامج التعليمية
* نظام تسجيل متكامل للطلاب
* متابعة المدفوعات والحالة المالية
* لوحات تحكم للإدارة والموظفين
* تقارير شاملة وإحصائيات

الوظائف:
--------
* إدارة النوادي: إنشاء وتنظيم النوادي المختلفة
* البرامج: إنشاء البرامج التعليمية مع تحديد الأعمار والأوقات والأسعار
* التسجيل: نظام تسجيل متكامل مع رفع المستندات
* المدفوعات: متابعة المدفوعات وحالة السداد
* قائمة الانتظار: إدارة تلقائية عند امتلاء البرامج
* التقارير: تقارير الحضور والمالية والإحصائيات
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',

    # Dependencies
    'depends': [
        'base',
        'mail',
        'web',
        'website',
        'account',# للواجهة العامة
    ],

    # Data files
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',
        #'data/mail_template_data.xml',

        # Views
        'views/charity_club_views.xml',
        'views/club_program_views.xml',
        'views/program_registration_views.xml',

        'views/website_templates.xml',
        'views/registration_form_template.xml',
        'views/website_menu.xml',


    ],



    # Other configurations
    'installable': True,
    'application': True,
    'auto_install': False,
}