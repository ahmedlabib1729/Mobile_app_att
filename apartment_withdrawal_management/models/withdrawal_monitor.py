# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class WithdrawalMonitor(models.Model):
    _name = 'withdrawal.monitor'
    _description = 'Apartment Withdrawal Monitor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'withdrawal_date desc, due_date desc'
    _rec_name = 'display_name'

    @api.depends('contract_id', 'building_unit_id', 'status')
    def _compute_display_name(self):
        for record in self:
            if record.contract_id and record.building_unit_id:
                record.display_name = f"{record.contract_id.name} - {record.building_unit_id.name} ({record.status})"
            else:
                record.display_name = f"Withdrawal Monitor - {record.status}"

    display_name = fields.Char(compute='_compute_display_name', store=True)

    installment_id = fields.Many2one(
        'loan.line.rs.own',
        string='Overdue Installment',
        required=True,
        ondelete='cascade',
        help="The installment that is overdue and being monitored"
    )

    installment_number = fields.Char(
        string='Installment Number',
        related='installment_id.number',
        readonly=True,
        store=True,
        help="The installment number (OCL/2025/0002, etc.)"
    )

    # Related Records
    contract_id = fields.Many2one(
        'ownership.contract',
        string='Contract',
        required=True,
        ondelete='cascade',
        index=True
    )
    building_unit_id = fields.Many2one(
        'product.template',
        string='Building Unit',
        required=True,
        domain=[('is_property', '=', True)]
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True
    )
    building_id = fields.Many2one(
        'building',
        string='Building',
        related='building_unit_id.building_id',
        store=True
    )

    # Dates and Timeline
    due_date = fields.Date(
        string='Original Due Date',
        required=True,
        help="Original due date of the overdue installment"
    )
    withdrawal_date = fields.Date(
        string='Withdrawal Date',
        help="Date when apartment was withdrawn",
        tracking=True
    )
    restoration_date = fields.Date(
        string='Restoration Date',
        help="Date when apartment was restored after payment",
        tracking=True
    )

    # Amounts and Calculations
    overdue_amount = fields.Float(
        string='Overdue Amount',
        digits='Product Price',
        help="Amount that was overdue at time of withdrawal"
    )

    @api.depends('due_date')
    def _compute_overdue_months(self):
        for record in self:
            if record.due_date:
                today = fields.Date.today()
                delta = relativedelta(today, record.due_date)
                record.overdue_months = delta.months + (delta.years * 12)
            else:
                record.overdue_months = 0

    overdue_months = fields.Integer(
        string='Months Overdue',
        compute='_compute_overdue_months',
        store=True,
        help="Number of months the installment is overdue"
    )

    # Status and Control - SIMPLIFIED TO ONLY 2 OPTIONS
    status = fields.Selection([
        ('withdrawn', 'Withdrawn'),
        ('restored', 'Restored')
    ], string='Status', default='withdrawn', required=True, tracking=True)

    # Additional Information
    notes = fields.Text(string='Notes')
    withdrawal_reason = fields.Text(
        string='Withdrawal Reason',
        help="Detailed reason for apartment withdrawal"
    )

    # System Fields
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # SQL Constraints
    _sql_constraints = [
        ('unique_contract_installment',
         'UNIQUE(contract_id, installment_id)',
         'A withdrawal monitor record already exists for this contract and installment.'),
    ]

    @api.model
    def create(self, vals):
        # Auto-populate related fields
        if vals.get('contract_id'):
            contract = self.env['ownership.contract'].browse(vals['contract_id'])
            if not vals.get('building_unit_id'):
                vals['building_unit_id'] = contract.building_unit.id
            if not vals.get('partner_id'):
                vals['partner_id'] = contract.partner_id.id

        if vals.get('installment_id'):
            installment = self.env['loan.line.rs.own'].browse(vals['installment_id'])
            if not vals.get('due_date'):
                vals['due_date'] = installment.date
            if not vals.get('overdue_amount'):
                vals['overdue_amount'] = installment.total_remaining_amount

        # Auto-set withdrawal date if creating with withdrawn status
        if vals.get('status') == 'withdrawn' and not vals.get('withdrawal_date'):
            vals['withdrawal_date'] = fields.Date.today()

        return super().create(vals)

    def action_withdraw_apartment(self):
        """Withdraw the apartment"""
        self.ensure_one()
        if self.status == 'restored':
            raise UserError(_("Cannot withdraw a restored apartment. Create a new monitor instead."))

        # Update contract status
        self.contract_id.write({
            'state': 'withdrawn',
            'withdrawal_date': fields.Date.today(),
            'withdrawal_reason': f"Overdue installment since {self.due_date}"
        })

        # Update building unit status
        self.building_unit_id.write({
            'state': 'withdrawn',
            'withdrawal_date': fields.Date.today()
        })

        # Update monitor record
        self.write({
            'status': 'withdrawn',
            'withdrawal_date': fields.Date.today(),
            'withdrawal_reason': f"Installment overdue for {self.overdue_months} months"
        })

        # Send notification
        if self.env.company.withdrawal_notification:
            template = self.env.ref('apartment_withdrawal.email_template_withdrawal_notification', False)
            if template:
                template.send_mail(self.id, force_send=True)

        _logger.info(f"Apartment withdrawn: Contract {self.contract_id.name}, Unit {self.building_unit_id.name}")

    def action_restore_apartment(self):
        """Restore the apartment after payment"""
        self.ensure_one()
        if self.status != 'withdrawn':
            raise UserError(_("Only withdrawn apartments can be restored."))

        # Check if installment is paid
        if self.installment_id.total_remaining_amount > 0:
            raise UserError(_("Cannot restore apartment. The overdue installment is not fully paid yet."))

        # Update contract status
        self.contract_id.write({
            'state': 'confirmed',
            'withdrawal_date': False,
            'withdrawal_reason': False
        })

        # Update building unit status
        self.building_unit_id.write({
            'state': 'sold',
            'withdrawal_date': False
        })

        # Update monitor record
        self.write({
            'status': 'restored',
            'restoration_date': fields.Date.today()
        })



        _logger.info(f"Apartment restored: Contract {self.contract_id.name}, Unit {self.building_unit_id.name}")

    @api.model
    def check_overdue_installments(self):
        """Main method called by cron job to check for overdue installments"""

        # Check if withdrawal is enabled
        withdrawal_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'apartment_withdrawal.withdrawal_enabled', False)

        if not withdrawal_enabled:
            _logger.info("Apartment withdrawal is disabled. Skipping check.")
            return

        withdrawal_months = int(self.env['ir.config_parameter'].sudo().get_param(
            'apartment_withdrawal.withdrawal_months', 10))

        auto_restore = self.env['ir.config_parameter'].sudo().get_param(
            'apartment_withdrawal.auto_restore', True)

        # Calculate cutoff dates
        today = fields.Date.today()
        withdrawal_cutoff = today - relativedelta(months=withdrawal_months)

        _logger.info(f"Checking overdue installments. Withdrawal cutoff: {withdrawal_cutoff}")

        # Find overdue installments that are not already being monitored
        existing_monitors = self.search([]).mapped('installment_id').ids

        overdue_installments = self.env['loan.line.rs.own'].search([
            ('date', '<=', withdrawal_cutoff),
            ('total_remaining_amount', '>', 0),
            ('loan_id.state', '=', 'confirmed'),
            ('id', 'not in', existing_monitors)
        ])

        _logger.info(f"Found {len(overdue_installments)} new overdue installments to withdraw")

        # Create withdrawal records and withdraw immediately
        for installment in overdue_installments:
            monitor = self.create({
                'contract_id': installment.loan_id.id,
                'installment_id': installment.id,
                'due_date': installment.date,
                'overdue_amount': installment.total_remaining_amount,
                'status': 'withdrawn'
            })
            try:
                monitor.action_withdraw_apartment()
                _logger.info(f"Apartment withdrawn for contract {monitor.contract_id.name}")
            except Exception as e:
                _logger.error(f"Failed to withdraw apartment for contract {monitor.contract_id.name}: {e}")

        # Auto-restore paid installments if enabled
        if auto_restore:
            self.check_auto_restore()

    @api.model
    def check_auto_restore(self):
        """Check for withdrawn apartments that should be restored"""
        withdrawn_monitors = self.search([
            ('status', '=', 'withdrawn')
        ])

        for monitor in withdrawn_monitors:
            # Check if the overdue installment is now paid
            if monitor.installment_id.total_remaining_amount <= 0:
                try:
                    monitor.action_restore_apartment()
                    _logger.info(f"Apartment auto-restored for contract {monitor.contract_id.name}")
                except Exception as e:
                    _logger.error(f"Failed to auto-restore apartment for contract {monitor.contract_id.name}: {e}")

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.contract_id.name} - {record.building_unit_id.name} ({record.status})"
            result.append((record.id, name))
        return result

    @api.model
    def check_and_restore_paid_contracts(self):
        """Manual method to check and restore all paid contracts"""
        restored_count = 0

        # ابحث عن كل withdrawal monitors المسحوبة
        withdrawn_monitors = self.search([('status', '=', 'withdrawn')])

        for monitor in withdrawn_monitors:
            # إذا تم دفع الدفعة المتأخرة
            if monitor.installment_id.total_remaining_amount <= 0:
                try:
                    monitor.action_restore_apartment()
                    restored_count += 1
                    _logger.info(f"✅ MANUAL RESTORE: {monitor.contract_id.name}")
                except Exception as e:
                    _logger.error(f"❌ MANUAL RESTORE FAILED: {monitor.contract_id.name} - {e}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'استعادة العقود',
                'message': f'تم استعادة {restored_count} عقد تم دفع دفعاتهم المتأخرة',
                'type': 'success',
                'sticky': False,
            }
        }