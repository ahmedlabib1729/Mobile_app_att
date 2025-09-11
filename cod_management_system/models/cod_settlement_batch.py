# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CODSettlementBatch(models.Model):
    """دفعات تسوية COD مع شركات الشحن"""
    _name = 'cod.settlement.batch'
    _description = 'COD Settlement Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'settlement_date desc, id desc'

    # ===== الحقول الأساسية =====
    name = fields.Char(
        string='Settlement Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True
    )

    shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        required=True,
        tracking=True,
        ondelete='restrict',
        states={'draft': [('readonly', False)]}
    )

    settlement_date = fields.Date(
        string='Settlement Date',
        required=True,
        tracking=True,
        default=fields.Date.today,
        help='Expected or actual settlement date'
    )

    # ===== Collections =====
    collection_ids = fields.One2many(
        'cod.collection',
        'settlement_batch_id',
        string='COD Collections',
        states={'draft': [('readonly', False)]}
    )

    # ===== الحالة =====
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('sent', 'Sent to Company'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('reconciled', 'Reconciled'),
        ('cancelled', 'Cancelled')
    ], string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False
    )

    # ===== المبالغ المحسوبة =====
    total_cod_amount = fields.Float(
        string='Total COD',
        compute='_compute_amounts',
        store=True,
        readonly=True,
        help='Total COD amount to be collected'
    )

    total_commission = fields.Float(
        string='Total Commission',
        compute='_compute_amounts',
        store=True,
        readonly=True,
        help='Total commission for shipping company'
    )

    total_net_amount = fields.Float(
        string='Net Amount',
        compute='_compute_amounts',
        store=True,
        readonly=True,
        tracking=True,
        help='Net amount to be received'
    )

    shipment_count = fields.Integer(
        string='Shipments',
        compute='_compute_counts',
        store=True
    )

    # ===== معلومات الدفع =====
    payment_date = fields.Date(
        string='Payment Date',
        tracking=True,
        states={'paid': [('required', True)]}
    )

    payment_amount = fields.Float(
        string='Paid Amount',
        tracking=True,
        help='Actual amount received'
    )

    payment_difference = fields.Float(
        string='Difference',
        compute='_compute_payment_difference',
        store=True,
        help='Difference between expected and paid amount'
    )

    payment_reference = fields.Char(
        string='Payment Reference',
        tracking=True,
        help='Bank transfer reference or check number'
    )

    payment_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('wallet', 'E-Wallet'),
        ('offset', 'Offset/Deduction')
    ], string='Payment Method',
        tracking=True
    )

    bank_account = fields.Char(
        string='Bank Account',
        help='Bank account used for payment'
    )

    # ===== الملفات والمرفقات =====
    statement_file = fields.Binary(
        string='Statement File',
        attachment=True,
        help='Shipping company statement file'
    )

    statement_filename = fields.Char(
        string='Statement Filename'
    )

    # ===== معلومات إضافية =====
    notes = fields.Text(
        string='Notes'
    )

    internal_notes = fields.Text(
        string='Internal Notes',
        help='Internal notes not visible to partner'
    )

    # ===== Accounting =====
    journal_entry_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )

    # ===== التتبع =====
    created_automatically = fields.Boolean(
        string='Auto Created',
        default=False,
        readonly=True,
        help='Created by automated process'
    )

    notification_sent = fields.Boolean(
        string='Notification Sent',
        default=False,
        readonly=True
    )

    notification_sent_date = fields.Datetime(
        string='Notification Date',
        readonly=True
    )

    # ===== Compute Methods =====

    @api.depends('collection_ids', 'collection_ids.cod_amount',
                 'collection_ids.cod_commission', 'collection_ids.total_deductions',
                 'collection_ids.net_amount')
    def _compute_amounts(self):
        """حساب المجاميع"""
        for batch in self:
            collections = batch.collection_ids.filtered(lambda c: c.collection_state != 'cancelled')
            batch.total_cod_amount = sum(collections.mapped('cod_amount'))
            batch.total_commission = sum(collections.mapped('total_deductions'))  # إجمالي كل الخصومات
            batch.total_net_amount = sum(collections.mapped('net_amount'))

    @api.depends('collection_ids')
    def _compute_counts(self):
        """حساب عدد الشحنات"""
        for batch in self:
            batch.shipment_count = len(batch.collection_ids.filtered(
                lambda c: c.collection_state != 'cancelled'
            ))

    @api.depends('total_net_amount', 'payment_amount')
    def _compute_payment_difference(self):
        """حساب الفرق بين المتوقع والمدفوع"""
        for batch in self:
            batch.payment_difference = batch.payment_amount - batch.total_net_amount

    # ===== Action Methods =====

    def action_confirm(self):
        """تأكيد الدفعة"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft batches can be confirmed.'))

        if not self.collection_ids:
            raise UserError(_('Cannot confirm batch without collections.'))

        # التحقق من حالة Collections
        invalid_collections = self.collection_ids.filtered(
            lambda c: c.collection_state not in ['collected', 'in_settlement', 'disputed']
        )
        if invalid_collections:
            raise UserError(_(
                'Some collections are not ready for settlement:\n%s'
            ) % '\n'.join(invalid_collections.mapped('display_name')))

        self.write({
            'state': 'confirmed'
        })

        # تحديث حالة Collections
        self.collection_ids.write({'collection_state': 'in_settlement'})

        self.message_post(
            body=_(
                'Settlement batch confirmed.\n'
                'Shipments: %s\n'
                'Total COD: %s %s\n'
                'Net Amount: %s %s'
            ) % (
                     self.shipment_count,
                     self.total_cod_amount, self.currency_id.symbol,
                     self.total_net_amount, self.currency_id.symbol
                 ),
            subject=_('Batch Confirmed')
        )

        return True

    def action_send_to_company(self):
        """إرسال للشركة"""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_('Only confirmed batches can be sent.'))

        self.state = 'sent'
        self.notification_sent = True
        self.notification_sent_date = fields.Datetime.now()

        # إرسال إيميل للشركة
        self._send_settlement_notification()

        self.message_post(
            body=_('Settlement statement sent to %s') % self.shipping_company_id.name,
            subject=_('Statement Sent')
        )

        return True

    def action_register_payment(self):
        """تسجيل الدفعة"""
        self.ensure_one()
        if self.state not in ['sent', 'partially_paid']:
            raise UserError(_('Cannot register payment for this batch.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Payment'),
            'res_model': 'cod.payment.register.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_batch_id': self.id,
                'default_amount': self.total_net_amount,
                'default_payment_date': fields.Date.today(),
            }
        }

    def action_mark_paid(self):
        """تحديد كمدفوع"""
        self.ensure_one()
        if self.state not in ['sent', 'partially_paid']:
            raise UserError(_('Invalid state for marking as paid.'))

        if not self.payment_amount:
            raise UserError(_('Please register payment amount first.'))

        self.state = 'paid'

        # تحديث Collections
        self.collection_ids.filtered(
            lambda c: c.collection_state == 'in_settlement'
        ).write({
            'collection_state': 'settled',
            'actual_settlement_date': fields.Date.today()
        })

        # إنشاء قيد محاسبي
        self._create_journal_entry()

        self.message_post(
            body=_(
                'Payment received.\n'
                'Amount: %s %s\n'
                'Reference: %s'
            ) % (
                     self.payment_amount,
                     self.currency_id.symbol,
                     self.payment_reference or 'N/A'
                 ),
            subject=_('Payment Received')
        )

        return True

    def action_reconcile(self):
        """المطابقة المحاسبية"""
        self.ensure_one()
        if self.state != 'paid':
            raise UserError(_('Only paid batches can be reconciled.'))

        # المطابقة مع الفواتير
        self._reconcile_with_invoices()

        self.state = 'reconciled'

        # تحديث Collections
        self.collection_ids.write({'collection_state': 'reconciled'})

        self.message_post(
            body=_('Settlement reconciled with accounting.'),
            subject=_('Reconciled')
        )

        return True

    def action_cancel(self):
        """إلغاء الدفعة"""
        self.ensure_one()
        if self.state not in ['draft', 'confirmed']:
            raise UserError(_('Cannot cancel batch in current state.'))

        # إزالة Collections من الدفعة
        self.collection_ids.write({
            'settlement_batch_id': False,
            'collection_state': 'collected'
        })

        self.state = 'cancelled'

        self.message_post(
            body=_('Settlement batch cancelled.'),
            subject=_('Cancelled')
        )

        return True

    def action_print_statement(self):
        """طباعة كشف الحساب"""
        self.ensure_one()

        # TODO: ربط مع التقرير
        return self.env.ref('cod_management_system.action_report_cod_settlement').report_action(self)

    def action_view_collections(self):
        """عرض التحصيلات"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Collections'),
            'res_model': 'cod.collection',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.collection_ids.ids)],
            'context': {
                'default_settlement_batch_id': self.id,
            }
        }

    # ===== Private Methods =====

    def _send_settlement_notification(self):
        """إرسال إشعار التسوية للشركة"""
        self.ensure_one()

        # TODO: تنفيذ إرسال الإيميل
        # سيتم في المرحلة الثانية
        _logger.info(f'Sending settlement notification for batch {self.name}')

    def _create_journal_entry(self):
        """إنشاء قيد محاسبي للتسوية"""
        self.ensure_one()

        # TODO: تنفيذ القيد المحاسبي
        # سيتم في مرحلة التكامل مع الحسابات
        pass

    def _reconcile_with_invoices(self):
        """المطابقة مع الفواتير"""
        self.ensure_one()

        # TODO: تنفيذ المطابقة
        # سيتم في مرحلة التكامل مع الحسابات
        pass

    # ===== CRUD Methods =====

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('cod.settlement.batch') or _('New')

        return super().create(vals_list)

    def unlink(self):
        """Check before deletion"""
        for batch in self:
            if batch.state not in ['draft', 'cancelled']:
                raise UserError(_(
                    'Cannot delete settlement batch %s which is not in draft or cancelled state.'
                ) % batch.name)

        return super().unlink()

    # ===== Cron Methods =====

    @api.model
    def _cron_create_weekly_settlements(self):
        """Cron job لإنشاء التسويات الأسبوعية"""
        today = fields.Date.today()
        today_weekday = today.weekday()

        # البحث عن الشركات التي موعد تسويتها اليوم
        companies = self.env['shipping.company'].search([
            ('cod_settlement_day', '=', str(today_weekday)),
            ('cod_auto_create_settlement', '=', True)
        ])

        for company in companies:
            # البحث عن Collections جاهزة للتسوية
            collections = self.env['cod.collection'].search([
                ('shipping_company_id', '=', company.id),
                ('collection_state', 'in', ['collected', 'disputed']),
                ('settlement_batch_id', '=', False),
                ('expected_settlement_date', '<=', today)
            ])

            if collections:
                # إنشاء دفعة جديدة
                batch = self.create({
                    'shipping_company_id': company.id,
                    'settlement_date': today,
                    'created_automatically': True,
                    'collection_ids': [(6, 0, collections.ids)]
                })

                _logger.info(f'Created automatic settlement batch {batch.name} for {company.name}')

                # إرسال إشعار
                batch.message_post(
                    body=_(
                        'Automatic settlement batch created.\n'
                        'Collections: %s\n'
                        'Total Amount: %s EGP'
                    ) % (len(collections), batch.total_net_amount),
                    subject=_('Auto-Created Batch')
                )

        return True

    @api.model
    def _cron_send_settlement_reminders(self):
        """Cron job لإرسال التذكيرات"""
        tomorrow = fields.Date.today() + timedelta(days=1)

        # البحث عن الدفعات المستحقة غداً
        batches = self.search([
            ('state', 'in', ['confirmed', 'sent']),
            ('settlement_date', '=', tomorrow),
            ('notification_sent', '=', False)
        ])

        for batch in batches:
            batch._send_settlement_notification()

            batch.message_post(
                body=_('Settlement reminder sent for tomorrow.'),
                subject=_('Reminder Sent')
            )

        return True