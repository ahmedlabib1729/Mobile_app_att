from odoo import models, fields, api
class Employee(models.Model):
    _inherit = 'hr.employee'

    is_citizen = fields.Boolean(string="Is Citizen", default=False)
    target_amount = fields.Float(string='Monthly Target Amount',
                                 help="Target amount of approved invoices for the month.")
    commission_class_id = fields.Many2one('non.citizen.commission.config', string='Employee Class',
                                          help="Class of the employee determining commission percentage.")

    citizen_commission_ids = fields.One2many('invoice.commission.line', 'employee_id',
                                             string='Citizen Commission Lines')
    non_citizen_commission_ids = fields.One2many('non.citizen.commission.line', 'employee_id',
                                                 string='Non-Citizen Commission Lines')

    @api.onchange('is_citizen')
    def _onchange_is_citizen(self):
        if self.is_citizen:
            self.commission_class_id = False
        else:
            self.commission_class_id = self.commission_class_id or False

    def _get_current_month_commission(self):
        """
        حساب عمولة الشهر الحالي
        """
        self.ensure_one()
        today = fields.Date.today()
        start_date = today.replace(day=1)
        end_date = fields.Date.end_of(start_date, 'month')

        if self.is_citizen:
            commission_lines = self.env['invoice.commission.line'].search([
                ('employee_id', '=', self.id),
                ('invoice_id.invoice_date', '>=', start_date),
                ('invoice_id.invoice_date', '<=', end_date)
            ])
            return sum(line.commission_amount for line in commission_lines)
        else:
            commission_lines = self.env['non.citizen.commission.line'].search([
                ('employee_id', '=', self.id),
                ('invoice_id.invoice_date', '>=', start_date),
                ('invoice_id.invoice_date', '<=', end_date)
            ])
            return sum(line.commission_amount + line.additional_commission for line in commission_lines)

class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    is_citizen = fields.Boolean(string="Is Citizen", default=False)

    target_amount = fields.Float(string='Monthly Target Amount',
                                 help="Target amount of approved invoices for the month.")
    commission_class_id = fields.Many2one('non.citizen.commission.config', string='Employee Class',
                                          help="Class of the employee determining commission percentage.")