# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class HrPayslipMobile(models.Model):
    _inherit = 'hr.payslip'

    # حقول إضافية للتطبيق المحمول (اختياري)
    mobile_notes = fields.Text(
        string="ملاحظات للتطبيق المحمول",
        help="ملاحظات خاصة تظهر في التطبيق المحمول"
    )

    is_viewed_on_mobile = fields.Boolean(
        string="تمت المشاهدة عبر الموبايل",
        default=False,
        readonly=True
    )

    mobile_view_date = fields.Datetime(
        string="تاريخ المشاهدة عبر الموبايل",
        readonly=True
    )

    def mark_as_viewed_on_mobile(self):
        """تسجيل أن الكشف تمت مشاهدته عبر التطبيق المحمول"""
        self.write({
            'is_viewed_on_mobile': True,
            'mobile_view_date': fields.Datetime.now()
        })
        return True

    @api.model
    def get_payslip_summary_for_employee(self, employee_id):
        """حساب ملخص كشوف المرتبات للموظف"""
        payslips = self.search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'done')
        ])

        if not payslips:
            return {
                'total_net': 0,
                'average_net': 0,
                'count': 0,
                'last_payment': None
            }

        total_net = sum(payslips.mapped('net_wage'))
        count = len(payslips)

        return {
            'total_net': total_net,
            'average_net': total_net / count if count > 0 else 0,
            'count': count,
            'last_payment': payslips[0].date_from if payslips else None
        }


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    # يمكن إضافة حقول إضافية هنا إذا احتجت
    mobile_display_order = fields.Integer(
        string="ترتيب العرض في الموبايل",
        default=100,
        help="ترتيب ظهور البند في التطبيق المحمول"
    )

    show_on_mobile = fields.Boolean(
        string="إظهار في التطبيق المحمول",
        default=True,
        help="تحديد ما إذا كان هذا البند يظهر في التطبيق المحمول"
    )