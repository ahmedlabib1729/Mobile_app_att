# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CustomerPriceCategory(models.Model):
    """فئات تسعير العملاء"""
    _name = 'customer.price.category'
    _description = 'Customer Price Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Category Name',
        required=True,
        help='e.g., Standard, Silver, Gold'
    )

    code = fields.Char(
        string='Code',
        required=True,
        help='Short code for the category'
    )

    discount_percentage = fields.Float(
        string='Discount %',
        default=0.0,
        help='Discount percentage for this category (0-100)'
    )

    min_monthly_shipments = fields.Integer(
        string='Min. Monthly Shipments',
        default=0,
        help='Minimum shipments per month to qualify'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    color = fields.Integer(
        string='Color',
        default=0
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    description = fields.Text(
        string='Description',
        help='Description of this category benefits'
    )

    # إحصائيات
    customer_count = fields.Integer(
        string='Customers',
        compute='_compute_customer_count'
    )

    @api.constrains('discount_percentage')
    def _check_discount(self):
        for record in self:
            if record.discount_percentage < 0 or record.discount_percentage > 100:
                raise ValidationError(_('Discount must be between 0% and 100%'))

    def _compute_customer_count(self):
        for record in self:
            record.customer_count = self.env['res.partner'].search_count([
                ('price_category_id', '=', record.id)
            ])

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            if record.discount_percentage > 0:
                name += f" (-{record.discount_percentage:.0f}%)"
            result.append((record.id, name))
        return result


class ResPartner(models.Model):
    """إضافة فئة التسعير للعميل"""
    _inherit = 'res.partner'

    price_category_id = fields.Many2one(
        'customer.price.category',
        string='Price Category',
        help='Customer pricing category'
    )

    # إحصائيات للمساعدة في التصنيف
    monthly_shipment_count = fields.Integer(
        string='Monthly Shipments',
        compute='_compute_monthly_shipments'
    )

    total_shipment_value = fields.Float(
        string='Total Shipment Value',
        compute='_compute_shipment_stats'
    )

    def _compute_monthly_shipments(self):
        """حساب عدد الشحنات في آخر 30 يوم"""
        from datetime import datetime, timedelta

        for partner in self:
            date_from = datetime.now() - timedelta(days=30)
            partner.monthly_shipment_count = self.env['shipment.order'].search_count([
                ('sender_id', '=', partner.id),
                ('create_date', '>=', date_from)
            ])

    def _compute_shipment_stats(self):
        """حساب إجمالي قيمة الشحنات"""
        for partner in self:
            shipments = self.env['shipment.order'].search([
                ('sender_id', '=', partner.id),
                ('state', 'not in', ['cancelled'])
            ])
            partner.total_shipment_value = sum(shipments.mapped('final_customer_price'))

    def action_update_price_category(self):
        """تحديث فئة السعر بناءً على عدد الشحنات"""
        for partner in self:
            # البحث عن الفئة المناسبة
            categories = self.env['customer.price.category'].search([
                ('active', '=', True)
            ], order='min_monthly_shipments desc')

            for category in categories:
                if partner.monthly_shipment_count >= category.min_monthly_shipments:
                    partner.price_category_id = category
                    break

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Price categories updated successfully'),
                'type': 'success',
            }
        }


class ShipmentOrder(models.Model):
    _inherit = 'shipment.order'

    # الحقول الأساسية
    customer_category_id = fields.Many2one(
        related='sender_id.price_category_id',
        string='Customer Category',
        readonly=True
    )

    discount_percentage = fields.Float(
        related='sender_id.price_category_id.discount_percentage',
        string='Discount %',
        readonly=True
    )

    # السعر قبل الخصم (مجموع كل شيء)
    subtotal_before_discount = fields.Float(
        string='Subtotal Before Discount',
        compute='_compute_customer_pricing',
        store=True
    )

    discount_amount = fields.Float(
        string='Discount Amount',
        compute='_compute_customer_pricing',
        store=True
    )

    # السعر النهائي المحسوب تلقائياً بعد الخصم
    calculated_customer_price = fields.Float(
        string='Calculated Price',
        compute='_compute_customer_pricing',
        store=True
    )

    @api.depends('shipping_cost', 'total_broker_fees', 'discount_percentage')
    def _compute_customer_pricing(self):
        """حساب السعر النهائي مع الخصم"""
        for record in self:
            # 1. حساب المجموع قبل الخصم
            # المجموع = تكلفة الشحن + الرسوم الإضافية
            record.subtotal_before_discount = record.shipping_cost + record.total_broker_fees

            # 2. حساب الخصم على المجموع الكامل
            if record.discount_percentage > 0:
                record.discount_amount = record.subtotal_before_discount * (record.discount_percentage / 100)
            else:
                record.discount_amount = 0

            # 3. السعر النهائي بعد الخصم
            record.calculated_customer_price = record.subtotal_before_discount - record.discount_amount

            # 4. إذا لم يكن هناك سعر يدوي، استخدم السعر المحسوب
            if not record.customer_price or record.customer_price == 0:
                record.customer_price = record.calculated_customer_price

    @api.depends('shipping_cost', 'total_broker_fees')
    def _compute_final_price(self):
        """السعر النهائي بدون خصم - للعرض فقط"""
        for record in self:
            record.final_customer_price = record.shipping_cost + record.total_broker_fees

    @api.onchange('sender_id')
    def _onchange_sender_pricing(self):
        """تطبيق فئة السعر عند اختيار العميل"""
        if self.sender_id:
            self._compute_customer_pricing()

class ResPartner(models.Model):
    """إضافة فئة التسعير للعميل"""
    _inherit = 'res.partner'

    price_category_id = fields.Many2one(
        'customer.price.category',
        string='Price Category',
        help='Customer pricing category'
    )

    # حقول إحصائية اختيارية
    monthly_shipment_count = fields.Integer(
        string='Monthly Shipments',
        compute='_compute_monthly_shipments'
    )

    def _compute_monthly_shipments(self):
        """حساب عدد الشحنات في آخر 30 يوم"""
        from datetime import datetime, timedelta

        for partner in self:
            date_from = datetime.now() - timedelta(days=30)
            partner.monthly_shipment_count = self.env['shipment.order'].search_count([
                ('sender_id', '=', partner.id),
                ('create_date', '>=', date_from)
            ])