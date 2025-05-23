from odoo import models, fields, api
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_commission(self):

        if self.state == 'posted' :
            print(f"Creating commission for invoice {self.id}")
            self.env['invoice.commission.line'].create_commission_lines(self)
            self.env['non.citizen.commission.line'].create_non_citizen_commission_lines(self)
        else:
            print(f"Skipping commission for invoice {self.id}. State: {self.state}, Payment State: {self.payment_state}")

    def _remove_commission(self):

        print(f"Removing commission for invoice {self.id}")
        self.env['invoice.commission.line'].remove_commission_lines(self)
        self.env['non.citizen.commission.line'].remove_commission_lines(self)

    def action_post(self):
        res = super(AccountMove, self).action_post()
        return res

    def action_register_payment(self):

        res = super(AccountMove, self).action_register_payment()
        self.env.cr.commit()
        self.env.cr.flush()
        print(
            f"After payment registration: Invoice ID: {self.id}, State: {self.state}, Payment State: {self.payment_state}")
        self._compute_commission()
        return res

    def button_cancel(self):

        self._remove_commission()
        res = super(AccountMove, self).button_cancel()
        return res

    def action_invoice_cancel(self):

        self._remove_commission()
        res = super(AccountMove, self).action_invoice_cancel()
        return res

    def button_draft(self):

        self._remove_commission()
        res = super(AccountMove, self).button_draft()
        return res

    def _compute_payment_state(self):
        for record in self:
            res = super(AccountMove, record)._compute_payment_state()

            if record.payment_state in ['not_paid', 'partial', 'reversed']:
                print(f"Removing commission due to payment state change for invoice {record.id}. Payment State: {record.payment_state}")
                record._remove_commission()
        return res



class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        payments = super(AccountPaymentRegister, self).action_create_payments()
        if payments and isinstance(payments, list):
            for payment in payments:
                if payment.move_id:
                    payment.move_id._compute_commission()
        return payments