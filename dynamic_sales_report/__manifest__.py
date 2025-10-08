{
    'name': 'Dynamic Sales Report',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Dynamic Sales Reports with Multiple Views',
    'description': """
        Dynamic Sales Reporting Module
        ===============================
        Features:
        - Multiple report types (Itemwise, Employeewise, Customerwise)
        - Date range filtering
        - Party/Customer filtering
        - Summary cards with KPIs
        - Export to Excel, CSV, PDF
        - Dynamic data refresh
    """,
    'author': 'Your Company',
    'depends': ['base', 'sale', 'account', 'web', 'deplomacy_custom'],
    'data': [
        'security/ir.model.access.csv',
        'views/sales_report_views.xml',
        #'views/menu_views.xml',
        #'static/src/xml/sales_report_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dynamic_sales_report/static/src/css/sales_report.css',
            #'dynamic_sales_report/static/src/js/sales_report_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}