# -*- coding: utf-8 -*-
{
    'name': "Sections New Construction",

    'summary': """first setp create contract - WBS-OBS-Techical office - invoice""",

    'description': """
        Long description of module's purpose
    """,

    'author': "MOHAMED ABDELRHMAN",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'purchase', 'purchase_request', 'stock', 'project', 'master_data_construction','access_right_tender_cons'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        # 'wizard/wizard.xml',
        'views/ab_account_payment.xml',
        'views/config.xml',
        'views/engineer_template.xml',
        'views/invoice.xml',
        'views/boq.xml',
        'views/contract.xml',
        'views/webs.xml',
        'views/contract_user.xml',
        'views/deduction_allowance.xml',
        'views/purchase.xml',
        'views/stock.xml',
        'views/actions.xml',
        'views/menus.xml',
        'views/views.xml',
        'views/move_journal.xml',
        # 'views/product_template.xml',
        # 'views/ab_stock_picking.xml',
        # 'views/job_cost.xml',
        # 'views/item.xml',
        'wizard/item_wizard.xml',
        'reports/manu_action.xml',
        'reports/contraction_report.xml',
        'reports/report_subcontractors.xml',
        'reports/report_owner_contractors.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
