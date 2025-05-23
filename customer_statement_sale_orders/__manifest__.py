# -*- coding: utf-8 -*-
{
    'name': "Customer Statement Based On Sale Orders",

    'summary': """
        Print the sale order details with all customer invoices and payments.
        """,
    'description': """
        Generate a pdf report containing all customer sales with invoices details and payments.
       
    """,
    'author': "Just Try",
    'website': "",
    'category': 'Sales',
    'version': '17.0.1.0.0',
    'license': 'OPL-1',
    'depends': ['sale'],
    'images': ['static/description/banner.png'],
    'price': 9,
    'currency': 'USD',
    'data': [
        'security/group_data.xml',
        'security/ir.model.access.csv',
        'reports/reports.xml',
        'reports/customer_statement_report.xml',
        'views/res_partner_views.xml',
        'wizard/sales_customer_statement_wizard.xml',
    ],

}
