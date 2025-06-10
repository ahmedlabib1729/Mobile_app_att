# -*- coding: utf-8 -*-

from odoo import api, fields, models


class InstallmentPaymentCheck(models.TransientModel):
    _inherit = 'installment.payment.check'

    @api.model
    def default_get(self, fields_list):
        """Override default_get to fix the communication field bug"""
        # Get default values from the base TransientModel class (skip the problematic parent)
        res = models.TransientModel.default_get(self, fields_list)

        if self.env.context.get('active_model') == 'loan.line.rs.own' and self.env.context.get('active_id'):
            installment = self.env['loan.line.rs.own'].browse(self.env.context['active_id'])

            # Build communication text safely
            loan_name = ""
            installment_name = ""

            if installment.loan_id and installment.loan_id.name:
                loan_name = str(installment.loan_id.name)

            if installment.name:
                installment_name = str(installment.name)

            communication_text = loan_name
            if installment_name:
                communication_text += " - " + installment_name

            # Set all the required default values
            res.update({
                'installment_id': installment.id,
                'amount': installment.total_remaining_amount,
                'communication': communication_text,
                'payment_date': fields.Date.context_today(self),
            })

        return res