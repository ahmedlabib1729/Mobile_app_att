{
    'name': 'Stock Card Report',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Stock Card Reports with Multiple Views',
    'description': """
        Stock Card Reporting Module
        ============================
        Features:
        - Stock Card by Product
        - Stock Card by Category
        - Date range filtering
        - Product/Category filtering
        - Location filtering
        - Summary cards with KPIs
        - Export to Excel, CSV
        - Dynamic data refresh
    """,
    'author': 'Your Company',
    'depends': ['base', 'stock', 'product', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_card_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dynamic_inventory_reports/static/src/css/stock_card.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}