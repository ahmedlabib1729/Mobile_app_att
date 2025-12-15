# -*- coding: utf-8 -*-
{
    'name': 'MRP Sync Child Orders',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Synchronize parent and child manufacturing orders on close/backorder',
    'description': """
        This module adds synchronization between parent and child manufacturing orders.
        
        Features:
        - When closing a parent MO, a wizard appears asking to sync child MOs
        - Option to close child MOs with the same quantity
        - Option to create backorders for child MOs
        - Option to cancel child MOs when cancelling parent
        
        عربي:
        - عند إقفال أمر التصنيع الرئيسي، يظهر معالج للتزامن مع الأوامر الفرعية
        - خيار إقفال الأوامر الفرعية بنفس الكمية
        - خيار إنشاء Backorder للأوامر الفرعية
        - خيار إلغاء الأوامر الفرعية عند إلغاء الرئيسي
    """,
    'author': 'Ahmed - ERP Accounting and Auditing',
    'website': '',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/mrp_sync_wizard_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
