# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class PaymentBatch(models.Model):
    _name = 'payment.batch'
    _description = 'Intercompany Payment Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Batch Reference',
        required=True,
        readonly=True,
        copy=False,
        default='New',
        tracking=True
    )

    date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today,
        readonly=False,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('posted', 'Posted'),
        ('reconciled', 'Reconciled'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, required=True)

    # الشركة الدافعة (المركزية)
    paying_company_id = fields.Many2one(
        'res.company',
        string='Paying Company',
        required=True,
        readonly=False,
        default=lambda self: self.env.company,
        help="The central company that will make the payment"
    )

    payment_journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        required=True,
        readonly=False,
        domain="[('type', 'in', ['bank', 'cash']), ('company_id', '=', paying_company_id)]",
        help="Journal used for the payment in paying company"
    )

    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Payment Method',
        readonly=False,
        help="Payment method to be used"
    )

    # سطور الفواتير
    invoice_line_ids = fields.One2many(
        'payment.batch.line',
        'batch_id',
        string='Vendor Bills',
        readonly=False
    )

    # عدد الفواتير
    invoice_count = fields.Integer(
        string='Bills Count',
        compute='_compute_counts'
    )

    company_count = fields.Integer(
        string='Companies Count',
        compute='_compute_counts'
    )

    # المبالغ المحسوبة
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # تفاصيل المبالغ حسب الشركة
    company_amounts = fields.Text(
        string='Company Amounts',
        compute='_compute_amounts'
    )

    # القيود المولدة
    generated_move_ids = fields.One2many(
        'account.move',
        'payment_batch_id',
        string='Generated Entries',
        readonly=True
    )

    payment_ids = fields.One2many(
        'account.payment',
        'payment_batch_id',
        string='Payments',
        readonly=True
    )

    # الموردين
    partner_ids = fields.Many2many(
        'res.partner',
        string='Vendors',
        compute='_compute_partners',
        store=True
    )

    notes = fields.Text(string='Notes')

    # للتحقق من الكونفيجريشن
    has_config = fields.Boolean(
        string='Has Configuration',
        compute='_compute_has_config'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('payment.batch') or 'BATCH/001'
        return super().create(vals_list)

    @api.depends('invoice_line_ids')
    def _compute_counts(self):
        for batch in self:
            batch.invoice_count = len(batch.invoice_line_ids)
            batch.company_count = len(batch.invoice_line_ids.mapped('company_id'))

    @api.depends('invoice_line_ids.amount')
    def _compute_amounts(self):
        for batch in self:
            batch.total_amount = sum(batch.invoice_line_ids.mapped('amount'))

            # حساب المبالغ حسب الشركة
            company_amounts_text = []
            for company in batch.invoice_line_ids.mapped('company_id'):
                company_lines = batch.invoice_line_ids.filtered(
                    lambda l: l.company_id == company
                )
                amount = sum(company_lines.mapped('amount'))
                company_amounts_text.append(f"{company.name}: {amount:,.2f} {batch.currency_id.symbol}")

            batch.company_amounts = '\n'.join(company_amounts_text)

    @api.depends('invoice_line_ids.partner_id')
    def _compute_partners(self):
        for batch in self:
            batch.partner_ids = batch.invoice_line_ids.mapped('partner_id')

    @api.depends('paying_company_id', 'invoice_line_ids.company_id')
    def _compute_has_config(self):
        for batch in self:
            batch.has_config = True
            companies = batch.invoice_line_ids.mapped('company_id')
            for company in companies:
                if company != batch.paying_company_id:
                    config = self.env['intercompany.config'].search([
                        ('company_id', '=', batch.paying_company_id.id),
                        ('target_company_id', '=', company.id),
                        ('active', '=', True)
                    ], limit=1)
                    if not config:
                        batch.has_config = False
                        break

    @api.onchange('payment_journal_id')
    def _onchange_payment_journal(self):
        if self.payment_journal_id:
            # Get available payment methods
            self.payment_method_line_id = self.payment_journal_id.outbound_payment_method_line_ids[:1]

    def action_confirm(self):
        """تأكيد الدفعة"""
        for batch in self:
            if not batch.invoice_line_ids:
                raise UserError(_('Please add at least one invoice to the batch.'))

            if batch.state != 'draft':
                raise UserError(_('Only draft batches can be confirmed.'))

            # التحقق من الكونفيجريشن
            if not batch.has_config:
                companies = batch.invoice_line_ids.mapped('company_id')
                missing_configs = []
                for company in companies:
                    if company != batch.paying_company_id:
                        config = self.env['intercompany.config'].search([
                            ('company_id', '=', batch.paying_company_id.id),
                            ('target_company_id', '=', company.id),
                            ('active', '=', True)
                        ], limit=1)
                        if not config:
                            missing_configs.append(f"{batch.paying_company_id.name} → {company.name}")

                if missing_configs:
                    raise UserError(_(
                        'Missing intercompany configuration for:\n%s\n\n'
                        'Please configure intercompany settings first.'
                    ) % '\n'.join(missing_configs))

            batch.write({'state': 'confirmed'})
            batch.message_post(body=_('Batch confirmed'))

    def action_create_payment(self):
        """إنشاء الدفعة والقيود"""
        self.ensure_one()

        if self.state != 'confirmed':
            raise UserError(_('Only confirmed batches can be posted.'))

        try:
            # 1. إنشاء دفعة في الشركة المركزية لكل مورد
            self._create_central_payments()

            # 2. إنشاء القيود في الشركات الأخرى
            self._create_intercompany_entries()

            # 3. تحديث الحالة
            self.write({'state': 'posted'})
            self.message_post(body=_('Batch posted successfully'))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Payment batch posted successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(str(e))

    def _create_central_payments(self):
        """إنشاء دفعة مجمعة في الشركة المركزية لكل مورد"""
        # تجميع حسب المورد
        for partner in self.partner_ids:
            partner_lines = self.invoice_line_ids.filtered(lambda l: l.partner_id == partner)
            if partner_lines:
                self._create_payment_for_partner(partner, partner_lines)

    def _create_payment_for_partner(self, partner, lines):
        """إنشاء دفعة لمورد معين"""
        amount = sum(lines.mapped('amount'))

        payment_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': partner.id,
            'amount': amount,
            'date': self.date,
            'journal_id': self.payment_journal_id.id,
            'company_id': self.paying_company_id.id,
            'currency_id': self.currency_id.id,
            'payment_reference': f'{self.name} - {partner.name}',  # تغيير ref إلى payment_reference
            'payment_batch_id': self.id,
        }

        # إضافة payment method line لو موجود
        if self.payment_method_line_id:
            payment_vals['payment_method_line_id'] = self.payment_method_line_id.id

        payment = self.env['account.payment'].with_company(
            self.paying_company_id
        ).create(payment_vals)

        payment.action_post()

        return payment

    def _create_intercompany_entries(self):
        """إنشاء القيود في الشركات الأخرى"""
        for company in self.invoice_line_ids.mapped('company_id'):
            if company == self.paying_company_id:
                continue

            # التحقق من وجود partner للشركة الدافعة
            if not self.paying_company_id.partner_id:
                raise UserError(_(
                    'Company %s does not have a partner configured.\n'
                    'Please go to Companies and set a partner for the company.'
                ) % self.paying_company_id.name)

            company_lines = self.invoice_line_ids.filtered(lambda l: l.company_id == company)

            # البحث عن config
            config = self.env['intercompany.config'].search([
                ('company_id', '=', self.paying_company_id.id),
                ('target_company_id', '=', company.id),
                ('active', '=', True)
            ], limit=1)

            if not config:
                raise UserError(_(
                    'No intercompany configuration found between %s and %s.\n'
                    'Please configure intercompany settings first.'
                ) % (self.paying_company_id.name, company.name))

            # إنشاء قيد لكل مورد في هذه الشركة
            for partner in company_lines.mapped('partner_id'):
                partner_company_lines = company_lines.filtered(lambda l: l.partner_id == partner)
                self._create_intercompany_move(config, partner, partner_company_lines)

    def _create_intercompany_move(self, config, partner, lines):
        """إنشاء قيد في الشركة المستهدفة"""
        amount = sum(lines.mapped('amount'))

        # الحصول على حساب المورد في الشركة المستهدفة
        with_company = partner.with_company(config.target_company_id)
        vendor_account = with_company.property_account_payable_id

        if not vendor_account:
            raise UserError(_(
                'Vendor %s does not have a payable account configured for company %s'
            ) % (partner.name, config.target_company_id.name))

        # التأكد من أن الحساب ينتمي للشركة الصحيحة
        if vendor_account.company_id and vendor_account.company_id != config.target_company_id:
            # محاولة إيجاد حساب مماثل في الشركة المستهدفة
            similar_account = self.env['account.account'].sudo().search([
                ('company_id', '=', config.target_company_id.id),
                ('code', '=', vendor_account.code),
                ('account_type', '=', 'liability_payable')
            ], limit=1)

            if similar_account:
                vendor_account = similar_account
            else:
                raise UserError(_(
                    'Cannot find payable account for vendor %s in company %s.\n'
                    'Please configure the vendor accounts for all companies.'
                ) % (partner.name, config.target_company_id.name))

        move_vals = {
            'date': self.date,
            'journal_id': config.journal_id.id,
            'company_id': config.target_company_id.id,
            'ref': f'Payment Batch: {self.name} - {partner.name}',
            'payment_batch_id': self.id,
            'line_ids': [
                # من حساب الشريك (الشركة الدافعة)
                (0, 0, {
                    'account_id': config.target_account_id.id,
                    'name': f'Payment from {self.paying_company_id.name}',
                    'debit': amount,
                    'credit': 0,
                    'partner_id': self.paying_company_id.partner_id.id if self.paying_company_id.partner_id else False,
                }),
                # إلى حساب المورد (في الشركة المستهدفة)
                (0, 0, {
                    'account_id': vendor_account.id,
                    'name': f'Payment to {partner.name}',
                    'debit': 0,
                    'credit': amount,
                    'partner_id': partner.id,
                })
            ]
        }

        move = self.env['account.move'].with_company(config.target_company_id).create(move_vals)

        if config.auto_post:
            move.action_post()

        # ربط الفواتير للمطابقة لاحقا
        for line in lines:
            line.generated_move_id = move.id

        return move

    def action_reconcile(self):
        """مطابقة الفواتير مع الدفعات"""
        for batch in self:
            if batch.state != 'posted':
                raise UserError(_('Only posted batches can be reconciled.'))

            # المطابقة في الشركات
            for line in batch.invoice_line_ids:
                if line.generated_move_id and line.generated_move_id.state == 'posted':
                    # مطابقة الفاتورة مع القيد المولد
                    self._reconcile_invoice_with_move(line.invoice_id, line.generated_move_id)

            batch.write({'state': 'reconciled'})
            batch.message_post(body=_('Batch reconciled'))

    def _reconcile_invoice_with_move(self, invoice, move):
        """مطابقة فاتورة مع قيد"""
        # البحث عن سطور المطابقة
        invoice_payable_lines = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )
        move_payable_lines = move.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )

        if invoice_payable_lines and move_payable_lines:
            (invoice_payable_lines + move_payable_lines).reconcile()

    def action_cancel(self):
        """إلغاء الدفعة"""
        for batch in self:
            if batch.state == 'posted':
                # إلغاء الدفعات
                batch.payment_ids.action_cancel()
                # إلغاء القيود
                batch.generated_move_ids.button_cancel()

            batch.write({'state': 'cancelled'})
            batch.message_post(body=_('Batch cancelled'))

    def action_draft(self):
        """إعادة للمسودة"""
        for batch in self:
            if batch.state != 'cancelled':
                raise UserError(_('Only cancelled batches can be reset to draft.'))

            batch.write({'state': 'draft'})
            batch.message_post(body=_('Batch reset to draft'))

    def action_view_payments(self):
        """عرض الدفعات"""
        self.ensure_one()
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.payment_ids.ids)],
            'context': {'create': False}
        }

    def action_view_moves(self):
        """عرض القيود"""
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.generated_move_ids.ids)],
            'context': {'create': False}
        }

    def action_add_invoices(self):
        """فتح wizard لإضافة فواتير"""
        return {
            'name': _('Add Vendor Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'invoice.selection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_batch_id': self.id,
                'default_paying_company_id': self.paying_company_id.id,
            }
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted(self):
        if any(batch.state == 'posted' for batch in self):
            raise UserError(_('You cannot delete posted payment batches.'))