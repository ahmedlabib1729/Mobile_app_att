# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class OwnershipContract(models.Model):
    _inherit = 'ownership.contract'

    # Add withdrawal state to existing states
    state = fields.Selection(
        selection_add=[('withdrawn', 'Apartment Withdrawn')],
        ondelete={'withdrawn': 'cascade'}
    )

    payment_ids = fields.One2many('account.payment', 'ownership_line_id', string='Payments')

    # Withdrawal tracking fields
    withdrawal_date = fields.Date(
        string='Withdrawal Date',
        readonly=True,
        help="Date when apartment was withdrawn due to overdue payments"
    )

    withdrawal_reason = fields.Text(
        string='Withdrawal Reason',
        readonly=True,
        help="Reason for apartment withdrawal"
    )

    # Withdrawal monitoring
    withdrawal_monitor_ids = fields.One2many(
        'withdrawal.monitor',
        'contract_id',
        string='Withdrawal Monitors',
        help="Withdrawal monitoring records for this contract"
    )

    withdrawal_monitor_count = fields.Integer(
        string='Withdrawal Monitors',
        compute='_compute_withdrawal_monitor_count'
    )

    # Additional monitoring fields
    has_overdue_installments = fields.Boolean(
        compute='_compute_overdue_status',
        string='Has Overdue Installments'
    )
    overdue_months = fields.Integer(
        compute='_compute_overdue_status',
        string='Max Overdue Months'
    )
    total_overdue_amount = fields.Float(
        compute='_compute_overdue_status',
        string='Total Overdue Amount'
    )

    # Get settings from system configuration instead of per-contract fields
    withdrawal_enabled = fields.Boolean(
        string='Withdrawal Enabled',
        compute='_compute_withdrawal_settings',
        help="Based on system configuration"
    )
    withdrawal_months = fields.Integer(
        string='Withdrawal Threshold (Months)',
        compute='_compute_withdrawal_settings',
        help="Based on system configuration"
    )
    withdrawal_warning_days = fields.Integer(
        string='Warning Days',
        compute='_compute_withdrawal_settings',
        help="Based on system configuration"
    )

    def _compute_withdrawal_settings(self):
        """Get withdrawal settings from system configuration"""
        for record in self:
            record.withdrawal_enabled = self.env['ir.config_parameter'].sudo().get_param(
                'apartment_withdrawal.withdrawal_enabled', 'False') == 'True'
            record.withdrawal_months = int(self.env['ir.config_parameter'].sudo().get_param(
                'apartment_withdrawal.withdrawal_months', '10'))
            record.withdrawal_warning_days = int(self.env['ir.config_parameter'].sudo().get_param(
                'apartment_withdrawal.withdrawal_warning_days', '30'))

    @api.depends('withdrawal_monitor_ids')
    def _compute_withdrawal_monitor_count(self):
        for record in self:
            record.withdrawal_monitor_count = len(record.withdrawal_monitor_ids)

    @api.depends('loan_line.total_remaining_amount', 'loan_line.date')
    def _compute_overdue_status(self):
        for record in self:
            overdue_lines = record.loan_line.filtered(
                lambda l: l.total_remaining_amount > 0 and l.date and l.date < fields.Date.today()
            )

            if overdue_lines:
                record.has_overdue_installments = True
                # Calculate months overdue for each line
                max_months = 0
                total_amount = 0
                today = fields.Date.today()

                for line in overdue_lines:
                    months_diff = (today.year - line.date.year) * 12 + (today.month - line.date.month)
                    if months_diff > max_months:
                        max_months = months_diff
                    total_amount += line.total_remaining_amount

                record.overdue_months = max_months
                record.total_overdue_amount = total_amount
            else:
                record.has_overdue_installments = False
                record.overdue_months = 0
                record.total_overdue_amount = 0

    def action_view_withdrawal_monitors(self):
        """Open withdrawal monitors for this contract"""
        self.ensure_one()
        return {
            'name': _('Withdrawal Monitors'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'tree,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {
                'default_contract_id': self.id,
                'default_building_unit_id': self.building_unit.id,
                'default_partner_id': self.partner_id.id,
            },
            'target': 'current',
        }

    def action_create_withdrawal_monitor(self):
        """Create withdrawal monitor for overdue installments"""
        self.ensure_one()

        if not self.has_overdue_installments:
            raise UserError(_("No overdue installments found for this contract."))

        # Find the most overdue installment
        overdue_lines = self.loan_line.filtered(
            lambda l: l.total_remaining_amount > 0 and l.date and l.date < fields.Date.today()
        )

        if not overdue_lines:
            raise UserError(_("No overdue installments found."))

        # Get the oldest overdue installment
        most_overdue = min(overdue_lines, key=lambda l: l.date)

        # Check if monitor already exists
        existing_monitor = self.env['withdrawal.monitor'].search([
            ('contract_id', '=', self.id),
            ('installment_id', '=', most_overdue.id),
            ('status', 'in', ['monitoring', 'warning_sent', 'withdrawn'])
        ])

        if existing_monitor:
            raise UserError(_("Withdrawal monitor already exists for this installment."))

        # Calculate months overdue
        today = fields.Date.today()
        months_overdue = (today.year - most_overdue.date.year) * 12 + (today.month - most_overdue.date.month)

        # Create withdrawal monitor
        monitor = self.env['withdrawal.monitor'].create({
            'contract_id': self.id,
            'partner_id': self.partner_id.id,
            'building_unit_id': self.building_unit.id,
            'building_id': self.building.id,
            'installment_id': most_overdue.id,
            'due_date': most_overdue.date,
            'overdue_amount': most_overdue.total_remaining_amount,
            'overdue_months': months_overdue,
            'status': 'monitoring',
            'withdrawal_reason': _('Automatic monitoring due to overdue installment: %s') % most_overdue.name
        })

        return {
            'name': _('Withdrawal Monitor Created'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'form',
            'res_id': monitor.id,
            'target': 'current'
        }

    def action_manual_withdraw(self):
        """Manually withdraw apartment"""
        self.ensure_one()

        if self.state != 'confirmed':
            raise UserError(_("Only confirmed contracts can be withdrawn."))

        # Find overdue installments
        overdue_installments = self.loan_line.filtered(
            lambda line: line.total_remaining_amount > 0 and
                         line.date < fields.Date.today()
        )

        if not overdue_installments:
            raise UserError(_("No overdue installments found for this contract."))

        # Get the oldest overdue installment
        oldest_installment = overdue_installments.sorted('date')[0]

        # Calculate months overdue
        today = fields.Date.today()
        months_overdue = (today.year - oldest_installment.date.year) * 12 + (
                    today.month - oldest_installment.date.month)

        # Create or update withdrawal monitor
        existing_monitor = self.env['withdrawal.monitor'].search([
            ('contract_id', '=', self.id),
            ('installment_id', '=', oldest_installment.id)
        ], limit=1)

        if existing_monitor:
            if existing_monitor.status != 'withdrawn':
                existing_monitor.action_withdraw_apartment()
        else:
            # Create new monitor and withdraw immediately
            monitor = self.env['withdrawal.monitor'].create({
                'contract_id': self.id,
                'partner_id': self.partner_id.id,
                'building_unit_id': self.building_unit.id,
                'building_id': self.building.id,
                'installment_id': oldest_installment.id,
                'due_date': oldest_installment.date,
                'overdue_amount': oldest_installment.total_remaining_amount,
                'overdue_months': months_overdue,
                'status': 'monitoring',
                'withdrawal_reason': _(
                    'Manual withdrawal requested for overdue installment: %s') % oldest_installment.name
            })
            monitor.action_withdraw_apartment()

        return {
            'name': _('Apartment Withdrawn'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'form',
            'res_id': existing_monitor.id if existing_monitor else monitor.id,
            'target': 'current'
        }

    def action_manual_restore(self):
        """Manually restore withdrawn apartment"""
        self.ensure_one()

        if self.state != 'withdrawn':
            raise UserError(_("Only withdrawn contracts can be restored."))

        # Find active withdrawal monitor
        active_monitor = self.withdrawal_monitor_ids.filtered(
            lambda m: m.status == 'withdrawn'
        )

        if not active_monitor:
            raise UserError(_("No active withdrawal monitor found."))

        if len(active_monitor) > 1:
            active_monitor = active_monitor[0]  # Take the first one

        # Check if overdue installment is paid
        if active_monitor.installment_id.total_remaining_amount > 0:
            raise UserError(_(
                "Cannot restore apartment. The overdue installment '%s' is not fully paid yet. "
                "Remaining amount: %s"
            ) % (
                                active_monitor.installment_id.name,
                                active_monitor.installment_id.total_remaining_amount
                            ))

        active_monitor.action_restore_apartment()

        return {
            'name': _('Apartment Restored'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'form',
            'res_id': active_monitor.id,
            'target': 'current'
        }

    def write(self, vals):
        """Override write to handle automatic restoration"""
        res = super(OwnershipContract, self).write(vals)

        # Check for auto-restoration if payment is made
        auto_restore = self.env['ir.config_parameter'].sudo().get_param(
            'apartment_withdrawal_management.auto_restore', 'False')

        if auto_restore == 'True':
            for record in self:
                if record.state == 'withdrawn':
                    # Check if there are any withdrawn monitors that should be restored
                    withdrawn_monitors = record.withdrawal_monitor_ids.filtered(
                        lambda m: m.status == 'withdrawn'
                    )

                    for monitor in withdrawn_monitors:
                        if monitor.installment_id.total_remaining_amount <= 0:
                            try:
                                monitor.action_restore_apartment()
                                _logger.info(f"Auto-restored apartment for contract {record.name}")
                            except Exception as e:
                                _logger.error(f"Failed to auto-restore contract {record.name}: {e}")

        return res

    def unlink(self):
        """Override unlink to handle withdrawal monitors"""
        # Archive related withdrawal monitors instead of deleting
        for record in self:
            record.withdrawal_monitor_ids.write({'active': False})

        return super(OwnershipContract, self).unlink()

    @api.model
    def cron_check_overdue_installments(self):
        """Cron job to automatically check for overdue installments and create monitors"""
        _logger.info("Starting automatic overdue installments check...")

        # Get all confirmed contracts
        confirmed_contracts = self.search([('state', '=', 'confirmed')])

        monitors_created = 0
        warnings_sent = 0
        apartments_withdrawn = 0

        for contract in confirmed_contracts:
            try:
                # Check if withdrawal monitoring is enabled globally
                withdrawal_enabled = self.env['ir.config_parameter'].sudo().get_param(
                    'apartment_withdrawal.withdrawal_enabled', 'False') == 'True'

                if not withdrawal_enabled:
                    continue

                # Get global settings
                withdrawal_months = int(self.env['ir.config_parameter'].sudo().get_param(
                    'apartment_withdrawal.withdrawal_months', '10'))
                withdrawal_warning_days = int(self.env['ir.config_parameter'].sudo().get_param(
                    'apartment_withdrawal.withdrawal_warning_days', '30'))

                # Convert warning days to months (approximately)
                warning_months = max(1, withdrawal_warning_days // 30)

                # Check overdue installments
                overdue_lines = contract.loan_line.filtered(
                    lambda l: l.total_remaining_amount > 0 and l.date and l.date < fields.Date.today()
                )

                for line in overdue_lines:
                    today = fields.Date.today()
                    months_overdue = (today.year - line.date.year) * 12 + (today.month - line.date.month)

                    # Check if monitor already exists
                    existing_monitor = self.env['withdrawal.monitor'].search([
                        ('contract_id', '=', contract.id),
                        ('installment_id', '=', line.id),
                        ('status', 'in', ['monitoring', 'warning_sent', 'withdrawn'])
                    ], limit=1)

                    if not existing_monitor and months_overdue >= 1:
                        # Create new monitor
                        monitor = self.env['withdrawal.monitor'].create({
                            'contract_id': contract.id,
                            'partner_id': contract.partner_id.id,
                            'building_unit_id': contract.building_unit.id,
                            'building_id': contract.building.id,
                            'installment_id': line.id,
                            'due_date': line.date,
                            'overdue_amount': line.total_remaining_amount,
                            'overdue_months': months_overdue,
                            'status': 'monitoring',
                            'withdrawal_reason': _('Automatic monitoring - %d months overdue') % months_overdue
                        })
                        monitors_created += 1
                        _logger.info(f"Created monitor for contract {contract.name}, installment {line.name}")

                    elif existing_monitor:
                        # Update existing monitor
                        existing_monitor.write({
                            'overdue_months': months_overdue,
                            'overdue_amount': line.total_remaining_amount
                        })

                        # Check if warning should be sent
                        if (existing_monitor.status == 'monitoring' and
                                months_overdue >= warning_months):
                            existing_monitor.action_send_warning()
                            warnings_sent += 1
                            _logger.info(f"Warning sent for contract {contract.name}")

                        # Check if apartment should be withdrawn
                        elif (existing_monitor.status in ['monitoring', 'warning_sent'] and
                              months_overdue >= withdrawal_months):
                            existing_monitor.action_withdraw_apartment()
                            apartments_withdrawn += 1
                            _logger.info(f"Apartment withdrawn for contract {contract.name}")

            except Exception as e:
                _logger.error(f"Error processing contract {contract.name}: {e}")
                continue

        _logger.info(
            f"Overdue check completed. Created: {monitors_created}, Warnings: {warnings_sent}, Withdrawn: {apartments_withdrawn}")

        return {
            'monitors_created': monitors_created,
            'warnings_sent': warnings_sent,
            'apartments_withdrawn': apartments_withdrawn
        }


class LoanLineRsOwn(models.Model):
    _inherit = 'loan.line.rs.own'

    # Withdrawal monitoring
    withdrawal_monitor_ids = fields.One2many(
        'withdrawal.monitor',
        'installment_id',
        string='Withdrawal Monitors'
    )

    is_monitored = fields.Boolean(
        string='Being Monitored',
        compute='_compute_is_monitored',
        help="This installment is being monitored for potential withdrawal"
    )

    @api.depends('withdrawal_monitor_ids.status')
    def _compute_is_monitored(self):
        for record in self:
            record.is_monitored = bool(
                record.withdrawal_monitor_ids.filtered(
                    lambda m: m.status in ['monitoring', 'warning_sent', 'withdrawn']
                )
            )

    def write(self, vals):
        """Override write to trigger auto-restoration check"""
        res = super(LoanLineRsOwn, self).write(vals)

        # If payment amount is updated, check for auto-restoration
        if 'total_paid_amount' in vals:
            auto_restore = self.env['ir.config_parameter'].sudo().get_param(
                'apartment_withdrawal_management.auto_restore', 'False')

            if auto_restore == 'True':
                # Check withdrawal monitors for this installment
                for record in self:
                    withdrawn_monitors = record.withdrawal_monitor_ids.filtered(
                        lambda m: m.status == 'withdrawn'
                    )

                    for monitor in withdrawn_monitors:
                        if record.total_remaining_amount <= 0:
                            try:
                                monitor.action_restore_apartment()
                                _logger.info(f"Auto-restored due to payment: {record.loan_id.name}")
                            except Exception as e:
                                _logger.error(f"Auto-restoration failed for {record.loan_id.name}: {e}")

        return res

    def action_create_withdrawal_monitor(self):
        """Create withdrawal monitor for this specific installment"""
        self.ensure_one()

        if self.total_remaining_amount <= 0:
            raise UserError(_("This installment is already fully paid."))

        if not self.date or self.date >= fields.Date.today():
            raise UserError(_("This installment is not overdue yet."))

        # Check if monitor already exists
        existing_monitor = self.env['withdrawal.monitor'].search([
            ('installment_id', '=', self.id),
            ('status', 'in', ['monitoring', 'warning_sent', 'withdrawn'])
        ])

        if existing_monitor:
            raise UserError(_("Withdrawal monitor already exists for this installment."))

        # Calculate months overdue
        today = fields.Date.today()
        months_overdue = (today.year - self.date.year) * 12 + (today.month - self.date.month)

        # Create withdrawal monitor
        monitor = self.env['withdrawal.monitor'].create({
            'contract_id': self.loan_id.id,
            'partner_id': self.loan_id.partner_id.id,
            'building_unit_id': self.loan_id.building_unit.id,
            'building_id': self.loan_id.building.id,
            'installment_id': self.id,
            'due_date': self.date,
            'overdue_amount': self.total_remaining_amount,
            'overdue_months': months_overdue,
            'status': 'monitoring',
            'withdrawal_reason': _('Manual monitoring created for installment: %s') % self.name
        })

        return {
            'name': _('Withdrawal Monitor Created'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'form',
            'res_id': monitor.id,
            'target': 'current'
        }