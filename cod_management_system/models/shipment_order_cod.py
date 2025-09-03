# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ShipmentOrderCOD(models.Model):
    """إضافات COD على الشحنة"""
    _inherit = 'shipment.order'

    # ===== حقول COD الجديدة =====
    cod_collection_id = fields.Many2one(
        'cod.collection',
        string='COD Collection',
        readonly=True,
        ondelete='set null',
        copy=False
    )

    has_cod_collection = fields.Boolean(
        string='Has COD Collection',
        compute='_compute_cod_fields',
        store=True
    )

    cod_collection_state = fields.Selection(
        related='cod_collection_id.collection_state',
        string='COD Status',
        readonly=True,
        store=True
    )

    cod_settlement_batch_id = fields.Many2one(
        related='cod_collection_id.settlement_batch_id',
        string='Settlement Batch',
        readonly=True,
        store=True
    )

    cod_expected_settlement = fields.Date(
        related='cod_collection_id.expected_settlement_date',
        string='Expected Settlement',
        readonly=True
    )

    cod_actual_settlement = fields.Date(
        related='cod_collection_id.actual_settlement_date',
        string='Actual Settlement',
        readonly=True
    )

    cod_net_amount = fields.Float(
        related='cod_collection_id.net_amount',
        string='COD Net Amount',
        readonly=True
    )

    cod_commission = fields.Float(
        related='cod_collection_id.commission_amount',
        string='COD Commission',
        readonly=True
    )

    # ===== تفاصيل COD محسنة =====
    cod_collection_summary = fields.Text(
        string='COD Summary',
        compute='_compute_cod_summary',
        store=False
    )

    # ===== Compute Methods =====

    @api.depends('payment_method', 'cod_collection_id')
    def _compute_cod_fields(self):
        """حساب حقول COD"""
        for order in self:
            order.has_cod_collection = bool(order.cod_collection_id)

    @api.depends('cod_collection_id', 'cod_collection_state', 'cod_amount')
    def _compute_cod_summary(self):
        """حساب ملخص COD"""
        for order in self:
            if not order.cod_collection_id:
                order.cod_collection_summary = _('No COD collection record')
                continue

            collection = order.cod_collection_id
            lines = []

            # المبالغ
            lines.append("=== AMOUNTS ===")
            lines.append(f"COD Collected: {collection.cod_amount:.2f} EGP")
            lines.append(f"Product Value: {collection.product_value:.2f} EGP")

            # الخصومات
            lines.append("\n=== DEDUCTIONS ===")
            lines.append(f"Shipping Cost: {collection.shipping_cost:.2f} EGP")
            lines.append(f"COD Commission: {collection.cod_commission:.2f} EGP")
            lines.append(f"Total Deductions: {collection.total_deductions:.2f} EGP")

            # الصافي
            lines.append("\n=== NET AMOUNTS ===")
            lines.append(f"Net to Receive from Shipping: {collection.net_amount:.2f} EGP")

            # للعميل
            if collection.customer_refund_amount > 0:
                lines.append(f"Refund to Customer: {collection.customer_refund_amount:.2f} EGP")

            # الحالة
            lines.append("\n=== STATUS ===")
            state_dict = dict(collection._fields['collection_state'].selection)
            state_name = state_dict.get(collection.collection_state, collection.collection_state)
            lines.append(f"Status: {state_name}")

            # التواريخ
            if collection.delivered_date:
                lines.append(f"Delivered: {collection.delivered_date.date()}")
            if collection.expected_settlement_date:
                lines.append(f"Expected Settlement: {collection.expected_settlement_date}")
            if collection.actual_settlement_date:
                lines.append(f"Actual Settlement: {collection.actual_settlement_date}")

            # الدفعة
            if collection.settlement_batch_id:
                lines.append(f"\nBatch: {collection.settlement_batch_id.name}")
                lines.append(f"Batch Status: {collection.settlement_batch_id.state}")

            order.cod_collection_summary = '\n'.join(lines)

    # ===== Override Methods =====

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-create COD collection"""
        records = super().create(vals_list)

        for record in records:
            if record.payment_method == 'cod' and record.cod_amount > 0:
                record._create_cod_collection()

        return records

    def write(self, vals):
        """Override write to update COD collection"""
        # حفظ القيم القديمة
        old_payment_methods = {r.id: r.payment_method for r in self}
        old_cod_amounts = {r.id: r.cod_amount for r in self}

        result = super().write(vals)

        for record in self:
            # التحقق من تغيير طريقة الدفع أو المبلغ
            if 'payment_method' in vals or 'cod_amount' in vals:
                if record.payment_method == 'cod' and record.cod_amount > 0:
                    if not record.cod_collection_id:
                        record._create_cod_collection()
                    else:
                        # تحديث المبلغ إذا تغير
                        if record.cod_amount != old_cod_amounts.get(record.id):
                            record.cod_collection_id.cod_amount = record.cod_amount
                elif record.cod_collection_id:
                    # إلغاء COD collection إذا تغيرت طريقة الدفع
                    if record.cod_collection_id.collection_state == 'pending':
                        record.cod_collection_id.unlink()
                    else:
                        # لا يمكن حذفها، فقط إلغاؤها
                        record.cod_collection_id.collection_state = 'cancelled'

        return result

    # ===== Action Methods =====

    def action_deliver(self):
        """Override deliver action to update COD collection"""
        result = super().action_deliver()

        for record in self:
            if record.cod_collection_id and record.cod_collection_id.collection_state == 'pending':
                record.cod_collection_id.action_mark_delivered()

        return result

    def action_cancel(self):
        """Override cancel action to cancel COD collection"""
        for record in self:
            if record.cod_collection_id and record.cod_collection_id.collection_state == 'pending':
                record.cod_collection_id.collection_state = 'cancelled'

        return super().action_cancel()

    def action_view_cod_collection(self):
        """عرض سجل COD collection"""
        self.ensure_one()

        if not self.cod_collection_id:
            raise UserError(_('No COD collection record for this shipment.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('COD Collection'),
            'res_model': 'cod.collection',
            'res_id': self.cod_collection_id.id,
            'view_mode': 'form',
            'context': {
                'form_view_initial_mode': 'readonly',
            }
        }

    def action_create_cod_collection(self):
        """إنشاء COD collection يدوياً"""
        self.ensure_one()

        if self.payment_method != 'cod':
            raise UserError(_('This shipment is not COD.'))

        if self.cod_collection_id:
            raise UserError(_('COD collection already exists for this shipment.'))

        if not self.cod_amount or self.cod_amount <= 0:
            raise UserError(_('Please set COD amount first.'))

        self._create_cod_collection()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('COD collection record created successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_mark_cod_collected(self):
        """تحديد أن شركة الشحن حصلت الفلوس من العميل"""
        self.ensure_one()

        if not self.cod_collection_id:
            raise UserError(_('No COD collection record for this shipment.'))

        if self.state != 'delivered':
            raise UserError(_('Shipment must be delivered first.'))

        self.cod_collection_id.action_mark_collected()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('COD marked as collected by shipping company.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_add_to_settlement(self):
        """إضافة لدفعة تسوية"""
        self.ensure_one()

        if not self.cod_collection_id:
            raise UserError(_('No COD collection record for this shipment.'))

        return self.cod_collection_id.action_add_to_batch()

    # ===== Private Methods =====

    def _create_cod_collection(self):
        """إنشاء سجل COD collection"""
        self.ensure_one()

        if self.cod_collection_id:
            _logger.warning(f'COD collection already exists for shipment {self.order_number}')
            return self.cod_collection_id

        collection_vals = {
            'shipment_id': self.id,
            'cod_amount': self.cod_amount,
            'shipping_cost': self.shipping_cost if self.cod_includes_shipping else 0,
            'collection_state': 'pending',
        }

        # إذا كانت الشحنة delivered بالفعل
        if self.state == 'delivered':
            collection_vals['collection_state'] = 'delivered'
            collection_vals['delivered_date'] = self.actual_delivery or fields.Datetime.now()

        collection = self.env['cod.collection'].create(collection_vals)
        self.cod_collection_id = collection

        _logger.info(f'Created COD collection {collection.display_name} for shipment {self.order_number}')

        # إضافة رسالة في الشحنة
        self.message_post(
            body=_(
                'COD collection record created.\n'
                'Amount: %s EGP\n'
                'Expected Net: %s EGP'
            ) % (collection.cod_amount, collection.net_amount),
            subject=_('COD Collection Created')
        )

        return collection

    # ===== Search Methods =====

    @api.model
    def search_pending_cod(self, company_id=None):
        """البحث عن شحنات COD المعلقة"""
        domain = [
            ('payment_method', '=', 'cod'),
            ('state', 'in', ['delivered']),
            ('cod_collection_id', '!=', False),
            ('cod_collection_state', 'in', ['delivered', 'collected'])
        ]

        if company_id:
            domain.append(('shipping_company_id', '=', company_id))

        return self.search(domain)