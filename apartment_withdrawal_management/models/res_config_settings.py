# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Apartment Withdrawal Settings
    withdrawal_enabled = fields.Boolean(
        string='Enable Apartment Withdrawal',
        config_parameter='apartment_withdrawal.withdrawal_enabled',
        default=False,
        help="Enable automatic apartment withdrawal for overdue installments"
    )

    withdrawal_months = fields.Integer(
        string='Months Before Withdrawal',
        config_parameter='apartment_withdrawal.withdrawal_months',
        default=10,
        help="Number of months after due date before apartment is withdrawn"
    )

    withdrawal_notification = fields.Boolean(
        string='Send Withdrawal Notifications',
        config_parameter='apartment_withdrawal.withdrawal_notification',
        default=True,
        help="Send email notifications when apartment is withdrawn"
    )

    auto_restore = fields.Boolean(
        string='Auto Restore on Payment',
        config_parameter='apartment_withdrawal.auto_restore',
        default=True,
        help="Automatically restore apartment when overdue payment is made"
    )

    @api.constrains('withdrawal_months')
    def _check_withdrawal_months(self):
        for record in self:
            if record.withdrawal_months and record.withdrawal_months < 1:
                raise models.ValidationError(
                    "Withdrawal months must be at least 1 month."
                )