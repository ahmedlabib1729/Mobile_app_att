{
    'name': 'Emirates Post Integration',
    'version': '17.0.1.0.0',
    'category': 'Delivery',
    'summary': 'Integration with Emirates Post shipping services',
    'description': """
        This module integrates Odoo with Emirates Post API for:
        - Creating bookings
        - Printing labels
        - Tracking shipments
    """,
    'depends': ['sale', 'stock', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'data/delivery_carrier_data.xml',
        'views/emirates_post_config_views.xml',
        'views/emirates_post_shipment_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
        'wizard/emirates_post_shipment_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
