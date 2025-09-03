# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ShippingCompanyCOD(models.Model):
    """إضافات COD على شركة الشحن"""
    _inherit = 'shipping.company'

    # ===== إعدادات التسوية =====
    cod_settlement_day = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], string='Settlement Day',
        help='Weekly day for COD settlement'
    )

    cod_settlement_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom')
    ], string='Settlement Frequency',
        default='weekly',
        help='How often settlements are done'
    )

    cod_payment_delay_days = fields.Integer(
        string='Payment Delay (Days)',
        default=3,
        help='Number of days after delivery before settlement'
    )

    cod_settlement_time = fields.Float(
        string='Settlement Time',
        default=14.0,
        help='Time of day for settlement (24-hour format)'
    )

    # ===== التسوية التلقائية =====
    cod_auto_create_settlement = fields.Boolean(
        string='Auto Create Settlement',
        default=False,
        help='Automatically create settlement batches'
    )

    cod_auto_send_statement = fields.Boolean(
        string='Auto Send Statement',
        default=False,
        help='Automatically send settlement statements'
    )

    # ===== معلومات الاتصال للتسويات =====
    cod_notification_emails = fields.Char(
        string='COD Notification Emails',
        help='Comma-separated emails for COD notifications'
    )

    cod_bank_account = fields.Char(
        string='Bank Account for COD',
        help='Bank account number for COD settlements'
    )

    cod_bank_name = fields.Char(
        string='Bank Name'
    )

    cod_contact_person = fields.Char(
        string='COD Contact Person',
        help='Contact person for COD settlements'
    )

    cod_contact_phone = fields.Char(
        string='COD Contact Phone'
    )

    # ===== إحصائيات COD =====
    total_cod_collections = fields.Float(
        string='Total COD Collections',
        compute='_compute_cod_statistics',
        help='Total COD amount in all collections'
    )

    pending_cod_amount = fields.Float(
        string='Pending COD',
        compute='_compute_cod_statistics',
        help='COD amount pending settlement'
    )

    settled_cod_amount = fields.Float(
        string='Settled COD',
        compute='_compute_cod_statistics',
        help='COD amount already settled'
    )

    cod_collection_count = fields.Integer(
        string='COD Collections',
        compute='_compute_cod_statistics'
    )

    cod_batch_count = fields.Integer(
        string='Settlement Batches',
        compute='_compute_cod_statistics'
    )

    last_settlement_date = fields.Date(
        string='Last Settlement',
        compute='_compute_cod_statistics'
    )

    next_settlement_date = fields.Date(
        string='Next Settlement',
        compute='_compute_next_settlement_date'
    )

    # ===== متقدم =====
    cod_reconciliation_account_id = fields.Many2one(
        'account.account',
        string='COD Clearing Account',
        domain=[('account_type', 'in', ['asset_receivable', 'liability_payable'])],
        help='Account used for COD reconciliation'
    )

    cod_commission_account_id = fields.Many2one(
        'account.account',
        string='Commission Expense Account',
        domain=[('account_type', '=', 'expense')],
        help='Account for recording COD commission expense'
    )

    # ===== Compute Methods =====

    @api.depends('name')  # Dummy dependency
    def _compute_cod_statistics(self):
        """حساب إحصائيات COD"""
        for company in self:
            # جميع التحصيلات
            all_collections = self.env['cod.collection'].search([
                ('shipping_company_id', '=', company.id)
            ])

            # التحصيلات المعلقة
            pending_collections = all_collections.filtered(
                lambda c: c.collection_state in ['delivered', 'collected', 'in_settlement']
            )

            # التحصيلات المسواة
            settled_collections = all_collections.filtered(
                lambda c: c.collection_state in ['settled', 'reconciled']
            )

            # الدفعات
            batches = self.env['cod.settlement.batch'].search([
                ('shipping_company_id', '=', company.id)
            ])

            # آخر تسوية
            last_batch = batches.filtered(
                lambda b: b.state in ['paid', 'reconciled']
            ).sorted('settlement_date', reverse=True)

            # تعيين القيم
            company.total_cod_collections = sum(all_collections.mapped('cod_amount'))
            company.pending_cod_amount = sum(pending_collections.mapped('net_amount'))
            company.settled_cod_amount = sum(settled_collections.mapped('net_amount'))
            company.cod_collection_count = len(all_collections)
            company.cod_batch_count = len(batches)
            company.last_settlement_date = last_batch[0].settlement_date if last_batch else False

    @api.depends('cod_settlement_day', 'cod_settlement_frequency', 'cod_payment_delay_days')
    def _compute_next_settlement_date(self):
        """حساب تاريخ التسوية القادم"""
        for company in self:
            if not company.cod_settlement_day:
                company.next_settlement_date = False
                continue

            today = fields.Date.today()
            settlement_weekday = int(company.cod_settlement_day)

            # حساب الأيام حتى يوم التسوية القادم
            days_ahead = (settlement_weekday - today.weekday()) % 7
            if days_ahead == 0:  # نفس اليوم
                # التحقق من الوقت
                now = datetime.now()
                settlement_time = company.cod_settlement_time or 14.0
                settlement_hour = int(settlement_time)
                settlement_minute = int((settlement_time - settlement_hour) * 60)

                if now.hour > settlement_hour or (now.hour == settlement_hour and now.minute > settlement_minute):
                    # فات الوقت، الأسبوع القادم
                    days_ahead = 7

            next_date = today + timedelta(days=days_ahead)

            # التعديل حسب التكرار
            if company.cod_settlement_frequency == 'bi_weekly':
                # كل أسبوعين
                last_settlement = company.last_settlement_date
                if last_settlement:
                    weeks_diff = (next_date - last_settlement).days // 7
                    if weeks_diff < 2:
                        next_date += timedelta(weeks=(2 - weeks_diff))
            elif company.cod_settlement_frequency == 'monthly':
                # شهرياً
                # أول occurrence في الشهر
                if next_date.day > 7:
                    # انتقل للشهر القادم
                    if next_date.month == 12:
                        next_date = next_date.replace(year=next_date.year + 1, month=1)
                    else:
                        next_date = next_date.replace(month=next_date.month + 1)

                    # إيجاد أول يوم مطابق
                    while next_date.weekday() != settlement_weekday:
                        next_date += timedelta(days=1)

            company.next_settlement_date = next_date

    # ===== Action Methods =====

    def action_view_cod_collections(self):
        """عرض تحصيلات COD للشركة"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('COD Collections - %s') % self.name,
            'res_model': 'cod.collection',
            'view_mode': 'list,form,kanban,pivot,graph',
            'domain': [('shipping_company_id', '=', self.id)],
            'context': {
                'default_shipping_company_id': self.id,
                'search_default_pending': 1,
            }
        }

    def action_view_settlement_batches(self):
        """عرض دفعات التسوية"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Settlement Batches - %s') % self.name,
            'res_model': 'cod.settlement.batch',
            'view_mode': 'list,form,kanban',
            'domain': [('shipping_company_id', '=', self.id)],
            'context': {
                'default_shipping_company_id': self.id,
            }
        }

    def action_create_settlement_batch(self):
        """إنشاء دفعة تسوية يدوياً"""
        self.ensure_one()

        # البحث عن التحصيلات الجاهزة
        collections = self.env['cod.collection'].search([
            ('shipping_company_id', '=', self.id),
            ('collection_state', 'in', ['collected', 'disputed']),
            ('settlement_batch_id', '=', False)
        ])

        if not collections:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Collections'),
                    'message': _('No collections ready for settlement.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # فتح معالج الإنشاء
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Settlement Batch'),
            'res_model': 'cod.settlement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shipping_company_id': self.id,
                'default_collection_ids': [(6, 0, collections.ids)],
                'default_settlement_date': self.next_settlement_date or fields.Date.today(),
            }
        }

    # ===== Helper Methods =====

    def get_pending_collections(self):
        """الحصول على التحصيلات المعلقة"""
        self.ensure_one()

        return self.env['cod.collection'].search([
            ('shipping_company_id', '=', self.id),
            ('collection_state', 'in', ['collected', 'disputed']),
            ('settlement_batch_id', '=', False)
        ])

    def get_next_settlement_collections(self):
        """الحصول على التحصيلات للتسوية القادمة"""
        self.ensure_one()

        if not self.next_settlement_date:
            return self.env['cod.collection']

        # التحصيلات التي يجب تسويتها
        cutoff_date = self.next_settlement_date - timedelta(days=self.cod_payment_delay_days or 3)

        return self.env['cod.collection'].search([
            ('shipping_company_id', '=', self.id),
            ('collection_state', 'in', ['collected', 'disputed']),
            ('settlement_batch_id', '=', False),
            ('delivered_date', '<=', cutoff_date)
        ])

    def create_automatic_settlement(self):
        """إنشاء تسوية تلقائية"""
        self.ensure_one()

        collections = self.get_next_settlement_collections()
        if not collections:
            _logger.info(f'No collections to settle for {self.name}')
            return False

        batch = self.env['cod.settlement.batch'].create({
            'shipping_company_id': self.id,
            'settlement_date': self.next_settlement_date or fields.Date.today(),
            'created_automatically': True,
            'collection_ids': [(6, 0, collections.ids)]
        })

        _logger.info(f'Created settlement batch {batch.name} for {self.name} with {len(collections)} collections')

        # إرسال إشعار
        if self.cod_auto_send_statement:
            batch.action_send_to_company()

        return batch