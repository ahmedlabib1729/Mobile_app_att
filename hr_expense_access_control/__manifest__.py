# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Access Control - نظام صلاحيات المصاريف',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Expenses',
    'summary': 'نظام صلاحيات متقدم لإدارة المصاريف مع 4 مستويات وصول',
    'description': """
نظام صلاحيات المصاريف المتقدم
================================

المميزات الرئيسية:
------------------
* 4 مستويات صلاحيات واضحة ومنطقية
* تطبيق تلقائي على المستخدمين الجدد
* منع الموظفين من رؤية مصاريف الآخرين
* نظام موافقات متدرج

مستويات الصلاحيات:
-----------------
1. موظف - مصاريف شخصية: يرى ويدير مصاريفه فقط
2. مدير قسم - موافقة الفريق: يوافق على مصاريف فريقه
3. محاسب - معالجة المصاريف: يعالج المصاريف المعتمدة
4. مدير مالي - كل الصلاحيات: وصول كامل لكل المصاريف

التثبيت:
--------
* ثبت الموديول من قائمة التطبيقات
* اذهب لإعدادات المستخدمين
* حدد مستوى الصلاحيات لكل مستخدم من "مصاريف الشركة"
    """,
    'author': 'Ahmed - Odoo Expert',
    'website': 'https://www.your-company.com',
    'depends': ['hr_expense', 'hr'],
    'data': [
        # Security files - الترتيب مهم
        'security/expense_groups.xml',
        'security/expense_security.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/user_default_groups.xml',
        
        # Views and Actions
        'views/actions.xml',
        'views/expense_views.xml',
        #'views/menu_items.xml',
    ],
    'demo': [],
    # 'post_init_hook': 'post_init_hook',  # معطّل مؤقتاً لتجنب المشاكل
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'external_dependencies': {
        'python': [],
        'bin': [],
    },
    'qweb': [],
}
