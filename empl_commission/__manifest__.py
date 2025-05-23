# -*- coding: utf-8 -*-
{
    'name': "empl_commission",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account','base', 'hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/employee.xml',
        'views/employee_commission.xml',
        'views/invoice_commission_line_views.xml',
        'views/citizen_commission_config_views.xml',
        'views/non_citizen_commission_config_views.xml',
        #'data/hr_salary_rule_data.xml',
        'views/hr_employee_commission_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
