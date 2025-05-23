import calendar
from odoo import models, fields, api


class InvoiceCommissionLine(models.Model):
    _name = 'invoice.commission.line'
    _description = 'Invoice Commission Line'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True, readonly=True)
    invoice_date = fields.Date(string='Invoice Date', related='invoice_id.invoice_date', store=True,
                               readonly=True)  # Añadir este campo
    commission_amount = fields.Float(string='Commission Amount', required=True, readonly=True)
    commission_per_unit = fields.Float(string='Commission Per Unit', readonly=True)
    commission_quantity = fields.Float(string='Quantity for Commission', readonly=True)

    @api.model
    def create_commission_lines(self, invoice):
        print(f"Creating commission lines for invoice ID: {invoice.id}")

        employee = invoice.user_id.employee_id if invoice.user_id.employee_id else False
        if not employee or not employee.is_citizen:
            print("No employee found or employee is not a citizen.")
            return

        config = self.env['citizen.commission.config'].search([], limit=1)
        required_quantity = config.required_quantity if config else 50  # تعيين الحد الأدنى للكمية
        commission_per_unit = config.commission_per_unit if config else 35  # استخدام قيمة العمولة من التكوين

        start_date = fields.Date.today().replace(day=1)
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        end_date = start_date.replace(day=last_day)

        approved_invoices = self.env['account.move'].search([
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
            ('state', '=', 'posted'),
            ('payment_state', '=', 'paid'),
            ('user_id', '=', invoice.user_id.id),
            ('id', '!=', invoice.id)
        ])

        previous_quantity = sum(sum(line.quantity for line in inv.invoice_line_ids) for inv in approved_invoices)

        remaining_required_quantity = max(0, required_quantity - previous_quantity)

        total_invoice_quantity = sum(line.quantity for line in invoice.invoice_line_ids)

        if total_invoice_quantity > remaining_required_quantity:
            extra_quantity = total_invoice_quantity - remaining_required_quantity
        else:
            extra_quantity = 0

        if extra_quantity > 0:
            # حذف أي سجلات عمولة سابقة لهذه الفاتورة
            self.search([('invoice_id', '=', invoice.id)]).unlink()

            for line in invoice.invoice_line_ids:
                if extra_quantity > 0:
                    commission_quantity = min(line.quantity, extra_quantity)
                    # استخدام قيمة العمولة من التكوين
                    commission_amount = commission_quantity * commission_per_unit
                    self.create({
                        'employee_id': employee.id,
                        'invoice_id': invoice.id,
                        'commission_amount': commission_amount,
                        'commission_per_unit': commission_per_unit,
                        'commission_quantity': commission_quantity
                    })
                    print(f"Commission line created with amount: {commission_amount} (Rate: {commission_per_unit} per unit)")
                    extra_quantity -= commission_quantity

    def remove_commission_lines(self, invoice):
        # Adjusted to handle both payment and invoice cancellation
        commission_lines = self.search([('invoice_id', '=', invoice.id)])
        if commission_lines:
            commission_lines.unlink()
        else:
            print(f"No commission lines found for invoice ID: {invoice.id}")