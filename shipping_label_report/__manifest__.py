{
    'name': 'Shipping Label Report',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Print shipping labels/waybills for shipment orders',
    'description': """
        Shipping Label Report
        =====================
        This module adds shipping label printing functionality to the Shipping Management System.
        
        Features:
        ---------
        * Print professional shipping labels (waybills)
        * Barcode generation for tracking
        * Support for COD and Prepaid shipments
        * Arabic and English support
        * A4 paper format optimized
        
        بوليصة الشحن
        ============
        هذا الموديول يضيف إمكانية طباعة بوليصات الشحن لنظام إدارة الشحن.
        
        المميزات:
        ---------
        * طباعة بوليصات شحن احترافية
        * توليد باركود للتتبع
        * دعم الدفع عند الاستلام والمدفوع مسبقاً
        * دعم اللغة العربية والإنجليزية
        * تنسيق ورق A4
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'shipping_management_system',
    ],
    'data': [
        'report/report_shipment_label.xml',
        'views/report_shipment_label_views.xml',
    ],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': False,
}
