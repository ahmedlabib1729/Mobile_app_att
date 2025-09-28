# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AdditionalService(models.Model):
    """الخدمات الإضافية العامة"""
    _name = 'additional.service'
    _description = 'Additional Services'
    _order = 'name, sequence'

    name = fields.Char(
        string='Service Name',
        required=True,
        help='Name of the additional service'
    )

    code = fields.Char(
        string='Service Code',
        required=True,
        help='Unique code for the service'
    )

    description = fields.Text(
        string='Description',
        help='Service description'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    # العلاقة مع أسعار الفئات
    category_price_ids = fields.One2many(
        'additional.service.category.price',
        'service_id',
        string='Category Prices'
    )

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Service code must be unique!')
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result


class AdditionalServiceCategoryPrice(models.Model):
    """أسعار الخدمات الإضافية لكل فئة عميل - مبسط"""
    _name = 'additional.service.category.price'
    _description = 'Additional Service Category Pricing'
    _rec_name = 'service_id'

    service_id = fields.Many2one(
        'additional.service',
        string='Service',
        required=True,
        ondelete='cascade'
    )

    category_id = fields.Many2one(
        'customer.price.category',
        string='Customer Category',
        required=True,
        ondelete='cascade'
    )

    # سعر واحد فقط
    fee_amount = fields.Float(
        string='Price (EGP)',
        default=0.0,
        required=True,
        help='Service price for this category'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    _sql_constraints = [
        ('unique_service_category',
         'UNIQUE(service_id, category_id)',
         'Each service can have only one price per category!')
    ]

    @api.constrains('fee_amount')
    def _check_fee_amount(self):
        for record in self:
            if record.fee_amount < 0:
                raise ValidationError(_('Price cannot be negative!'))


class ShipmentAdditionalService(models.Model):
    """الخدمات الإضافية المختارة للشحنة - مبسط"""
    _name = 'shipment.additional.service'
    _description = 'Shipment Additional Services'
    _rec_name = 'display_name'

    shipment_id = fields.Many2one(
        'shipment.order',
        string='Shipment',
        required=True,
        ondelete='cascade'
    )

    service_id = fields.Many2one(
        'additional.service',
        string='Service',
        required=True
    )

    category_id = fields.Many2one(
        related='shipment_id.customer_category_id',
        string='Customer Category',
        store=True
    )

    # السعر المحسوب
    fee_amount = fields.Float(
        string='Price',
        compute='_compute_fee_amount',
        store=True,
        readonly=False
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('service_id')
    def _compute_display_name(self):
        for record in self:
            if record.service_id:
                record.display_name = record.service_id.name
            else:
                record.display_name = 'New Service'

    # أو override name_get
    def name_get(self):
        result = []
        for record in self:
            if record.service_id:
                name = record.service_id.name
                if record.fee_amount:
                    name = f"{name} ({record.fee_amount:.0f} EGP)"
            else:
                name = f'Service #{record.id}'
            result.append((record.id, name))
        return result

    @api.depends('service_id', 'category_id')
    def _compute_fee_amount(self):
        """حساب السعر بناءً على فئة العميل"""
        for record in self:
            if not record.service_id or not record.category_id:
                record.fee_amount = 0
                continue

            # البحث عن السعر للفئة
            price_config = self.env['additional.service.category.price'].search([
                ('service_id', '=', record.service_id.id),
                ('category_id', '=', record.category_id.id),
                ('active', '=', True)
            ], limit=1)

            if price_config:
                record.fee_amount = price_config.fee_amount
            else:
                record.fee_amount = 0