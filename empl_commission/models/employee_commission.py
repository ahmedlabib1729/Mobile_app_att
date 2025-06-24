from odoo import models, fields, api
from odoo.exceptions import UserError


class NonCitizenCommissionLine(models.Model):
    _name = 'non.citizen.commission.line'
    _description = 'Non-Citizen Commission Line'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True, readonly=True)
    commission_amount = fields.Float(string='Commission Amount', required=True, readonly=True)
    invoice_date = fields.Date(string='Invoice Date', related='invoice_id.invoice_date', store=True, readonly=True)
    additional_commission = fields.Float(string='Additional Commission', help="Commission added with this invoice.",
                                         readonly=True)
    commission_class = fields.Many2one('non.citizen.commission.config', string="Commission Class", readonly=True)
    commission_rate = fields.Float(string="Applied Rate", readonly=True)

    def create_non_citizen_commission_lines(self, invoice):

        employee = invoice.user_id.employee_id if invoice.user_id.employee_id else False
        if not employee or employee.is_citizen:
            return

        target_amount = employee.target_amount
        employee_class = employee.commission_class_id
        # استخدم الحقل الجديد، مع العودة للحقل القديم إذا لم يكن محدداً
        commission_class = employee.commission_class_id

        if not commission_class:
            # ترحيل البيانات من الحقل القديم
            old_class = employee.employee_class
            if old_class:
                commission_class = self.env['non.citizen.commission.config'].search([('class_id', '=', old_class)],
                                                                                    limit=1)
                if commission_class:
                    # تحديث سجل الموظف
                    employee.write({'commission_class_id': commission_class.id})

        if not target_amount or not commission_class:
            raise UserError('Employee target or class is not set.')

        commission_rate = commission_class.commission_rate

        if not commission_rate:
            raise UserError('Commission rate is not set for this employee class.')

        start_date = fields.Date.today().replace(day=1)
        end_date = fields.Date.end_of(start_date, 'month')

        approved_invoices = self.env['account.move'].search([
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
            ('state', '=', 'posted'),
            ('user_id', '=', employee.user_id.id)
        ])

        total_approved_amount = sum(inv.amount_untaxed for inv in approved_invoices)  # حساب المبلغ بدون الضريبة

        if total_approved_amount > target_amount:
            excess_amount = total_approved_amount - target_amount

            self.search([('invoice_id', '=', invoice.id)]).unlink()

            invoice_amount = invoice.amount_untaxed  # استخدام المبلغ بدون الضريبة
            if total_approved_amount - invoice_amount < target_amount:
                applicable_amount = invoice_amount - (target_amount - (total_approved_amount - invoice_amount))
            else:
                applicable_amount = invoice_amount

            additional_commission = applicable_amount * commission_rate
            total_commission = excess_amount * commission_rate

            self.create({
                'employee_id': employee.id,
                'invoice_id': invoice.id,
                'commission_amount': total_commission,
                'additional_commission': additional_commission,
                'commission_class': employee_class.id,
                'commission_rate': commission_rate
            })

    def remove_commission_lines(self, invoice):
        # Adjusted to handle both payment and invoice cancellation
        commission_lines = self.search([('invoice_id', '=', invoice.id)])
        if commission_lines:
            commission_lines.unlink()
        else:
            print(f"No non-citizen commission lines found for invoice ID: {invoice.id}")