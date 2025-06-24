from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    total_commission = fields.Float(string='Total Commission', compute='_compute_total_commission', store=True)

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_total_commission(self):
        for payslip in self:
            if not payslip.employee_id or not payslip.date_from or not payslip.date_to:
                payslip.total_commission = 0.0
                continue

            # حساب إجمالي العمولات للفترة
            employee = payslip.employee_id
            date_from = payslip.date_from
            date_to = payslip.date_to

            # حساب عمولات المواطنين
            citizen_commissions = 0.0
            if employee.is_citizen:
                commission_lines = self.env['invoice.commission.line'].search([
                    ('employee_id', '=', employee.id),
                    ('invoice_id.invoice_date', '>=', date_from),
                    ('invoice_id.invoice_date', '<=', date_to)
                ])
                citizen_commissions = sum(line.commission_amount for line in commission_lines)

            # حساب عمولات غير المواطنين
            non_citizen_commissions = 0.0
            if not employee.is_citizen:
                commission_lines = self.env['non.citizen.commission.line'].search([
                    ('employee_id', '=', employee.id),
                    ('invoice_id.invoice_date', '>=', date_from),
                    ('invoice_id.invoice_date', '<=', date_to)
                ])
                non_citizen_commissions = sum(
                    line.commission_amount + line.additional_commission for line in commission_lines)

            # تعيين إجمالي العمولات
            payslip.total_commission = citizen_commissions + non_citizen_commissions

    # تجاوز طريقة حساب البنود للتأكد من تضمين العمولات
    def _get_payslip_lines(self):
        result = super(HrPayslip, self)._get_payslip_lines()

        # إضافة قيمة العمولة كمتغير سياق للقواعد
        for payslip in self:
            self.env.context = dict(self.env.context)
            self.env.context.update({
                'employee_commission': payslip.total_commission
            })

        return result