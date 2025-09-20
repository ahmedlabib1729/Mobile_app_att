# -*- coding: utf-8 -*-

from . import models
from . import controller


def uninstall_hook(env):
    """Clean up when module is uninstalled"""
    try:
        # حذف البيانات المتعلقة بالنماذج المحذوفة
        env.cr.execute("""
            DELETE FROM ir_model_fields 
            WHERE model = 'shipping.company.service'
        """)

        env.cr.execute("""
            DELETE FROM ir_model 
            WHERE model = 'shipping.company.service'
        """)

        env.cr.execute("""
            DROP TABLE IF EXISTS shipping_company_service CASCADE
        """)

    except Exception as e:
        pass
