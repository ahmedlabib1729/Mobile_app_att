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

    def _compute_withdrawal_settings(self):
        """Get withdrawal settings from system configuration"""
        for record in self:
            record.withdrawal_enabled = self.env['ir.config_parameter'].sudo().get_param(
                'apartment_withdrawal.withdrawal_enabled', 'False') == 'True'
            record.withdrawal_months = int(self.env['ir.config_parameter'].sudo().get_param(
                'apartment_withdrawal.withdrawal_months', '10'))

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

        # Check if monitor already exists
        existing_monitor = self.env['withdrawal.monitor'].search([
            ('contract_id', '=', self.id),
            ('installment_id', '=', oldest_installment.id)
        ], limit=1)

        if existing_monitor and existing_monitor.status == 'withdrawn':
            raise UserError(_("This apartment is already withdrawn."))

        if existing_monitor and existing_monitor.status == 'restored':
            # Create new monitor for new withdrawal
            monitor = self.env['withdrawal.monitor'].create({
                'contract_id': self.id,
                'partner_id': self.partner_id.id,
                'building_unit_id': self.building_unit.id,
                'building_id': self.building.id,
                'installment_id': oldest_installment.id,
                'due_date': oldest_installment.date,
                'overdue_amount': oldest_installment.total_remaining_amount,
                'overdue_months': months_overdue,
                'status': 'withdrawn',
                'withdrawal_reason': _(
                    'Manual withdrawal requested for overdue installment: %s') % oldest_installment.name
            })
        else:
            # Create new monitor
            monitor = self.env['withdrawal.monitor'].create({
                'contract_id': self.id,
                'partner_id': self.partner_id.id,
                'building_unit_id': self.building_unit.id,
                'building_id': self.building.id,
                'installment_id': oldest_installment.id,
                'due_date': oldest_installment.date,
                'overdue_amount': oldest_installment.total_remaining_amount,
                'overdue_months': months_overdue,
                'status': 'withdrawn',
                'withdrawal_reason': _(
                    'Manual withdrawal requested for overdue installment: %s') % oldest_installment.name
            })

        monitor.action_withdraw_apartment()

        return {
            'name': _('Apartment Withdrawn'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'form',
            'res_id': monitor.id,
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
                        ('status', 'in', ['withdrawn', 'restored'])
                    ], limit=1)

                    # If no monitor exists and overdue months >= withdrawal threshold, withdraw immediately
                    if not existing_monitor and months_overdue >= withdrawal_months:
                        monitor = self.env['withdrawal.monitor'].create({
                            'contract_id': contract.id,
                            'partner_id': contract.partner_id.id,
                            'building_unit_id': contract.building_unit.id,
                            'building_id': contract.building.id,
                            'installment_id': line.id,
                            'due_date': line.date,
                            'overdue_amount': line.total_remaining_amount,
                            'overdue_months': months_overdue,
                            'status': 'withdrawn',
                            'withdrawal_reason': _('Automatic withdrawal - %d months overdue') % months_overdue
                        })
                        monitor.action_withdraw_apartment()
                        apartments_withdrawn += 1
                        _logger.info(f"Apartment withdrawn for contract {contract.name}")

            except Exception as e:
                _logger.error(f"Error processing contract {contract.name}: {e}")
                continue

        _logger.info(f"Overdue check completed. Withdrawn: {apartments_withdrawn}")

        return {
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
                    lambda m: m.status in ['withdrawn', 'restored']
                )
            )

    def write(self, vals):
        """Override write to trigger instant auto-restoration when payment is made"""
        # احفظ القيم القديمة قبل التحديث
        old_remaining_amounts = {record.id: record.total_remaining_amount for record in self}

        # نفذ التحديث العادي
        res = super(LoanLineRsOwn, self).write(vals)

        # تحقق من إعدادات الاستعادة التلقائية
        auto_restore = self.env['ir.config_parameter'].sudo().get_param(
            'apartment_withdrawal_management.auto_restore', 'False')

        if auto_restore == 'True':
            # تحقق من كل دفعة تم تحديثها
            for record in self:
                old_amount = old_remaining_amounts.get(record.id, 0)
                new_amount = record.total_remaining_amount

                # إذا تغير المبلغ المتبقي (يعني تم دفع شيء)
                if old_amount != new_amount:
                    # ابحث عن withdrawal monitors لهذه الدفعة
                    withdrawn_monitors = record.withdrawal_monitor_ids.filtered(
                        lambda m: m.status == 'withdrawn'
                    )

                    for monitor in withdrawn_monitors:
                        # إذا تم دفع الدفعة كاملة (المتبقي = صفر أو أقل)
                        if record.total_remaining_amount <= 0:
                            try:
                                # استعد الشقة فوراً
                                monitor.action_restore_apartment()
                                _logger.info(f"🎉 INSTANT RESTORE: {record.loan_id.name} - Payment completed!")

                                # أرسل إشعار للمستخدم
                                monitor.message_post(
                                    body=f"تم استعادة الشقة تلقائياً بعد دفع الدفعة المتأخرة: {record.name}",
                                    message_type='notification'
                                )

                            except Exception as e:
                                _logger.error(f"❌ RESTORE FAILED: {record.loan_id.name} - {e}")

        return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        """Override to check for auto-restoration when payment is posted"""
        res = super(AccountPayment, self).action_post()

        # تحقق من إعدادات الاستعادة التلقائية
        auto_restore = self.env['ir.config_parameter'].sudo().get_param(
            'apartment_withdrawal_management.auto_restore', 'False')

        if auto_restore == 'True':
            for payment in self:
                # إذا كان الدفع متعلق بعقد ملكية
                if hasattr(payment, 'ownership_line_id') and payment.ownership_line_id:
                    contract = payment.ownership_line_id

                    # إذا كان العقد مسحوب
                    if contract.state == 'withdrawn':
                        # ابحث عن withdrawal monitors مسحوبة
                        withdrawn_monitors = contract.withdrawal_monitor_ids.filtered(
                            lambda m: m.status == 'withdrawn'
                        )

                        # تحقق من كل monitor
                        for monitor in withdrawn_monitors:
                            # إذا تم دفع الدفعة المتأخرة كاملة
                            if monitor.installment_id.total_remaining_amount <= 0:
                                try:
                                    # استعد الشقة فوراً
                                    monitor.action_restore_apartment()
                                    _logger.info(
                                        f"🎉 PAYMENT RESTORE: {contract.name} - Posted payment triggered restore!")

                                    # أرسل رسالة للعميل
                                    contract.message_post(
                                        body=f"تم استعادة شقتكم تلقائياً بعد تسجيل الدفعة. شكراً لالتزامكم!",
                                        partner_ids=[contract.partner_id.id]
                                    )

                                except Exception as e:
                                    _logger.error(f"❌ PAYMENT RESTORE FAILED: {contract.name} - {e}")

        return res

