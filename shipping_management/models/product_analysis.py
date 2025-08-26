# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ProductAnalysis(models.Model):
    _name = 'product.analysis'
    _description = 'Product Shipping Analysis'
    _order = 'shipping_date desc'

    # ===== Product Information =====
    product_name = fields.Char(
        string='Product Name',
        required=True,
        index=True
    )

    category_id = fields.Many2one(
        'product.category',
        string='Main Category',
        required=True,
        index=True
    )

    subcategory_id = fields.Many2one(
        'product.category',
        string='Subcategory'
    )

    brand = fields.Char(
        string='Brand',
        index=True
    )

    # ===== Order Information =====
    order_id = fields.Many2one(
        'shipping.order',
        string='Shipping Order',
        required=True,
        ondelete='cascade'
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True
    )

    customer_type = fields.Selection(
        related='customer_id.customer_type',
        string='Customer Type',
        store=True
    )

    # ===== Shipping Information =====
    shipping_date = fields.Datetime(
        string='Shipping Date',
        required=True,
        index=True
    )

    shipping_month = fields.Char(
        string='Month',
        compute='_compute_date_fields',
        store=True
    )

    shipping_week = fields.Integer(
        string='Week',
        compute='_compute_date_fields',
        store=True
    )

    shipping_day = fields.Char(
        string='Day of Week',
        compute='_compute_date_fields',
        store=True
    )

    # ===== Geographic Information =====
    governorate_id = fields.Many2one(
        'res.country.state',
        string='Governorate',
        domain="[('country_id.code', '=', 'EG')]"
    )

    city = fields.Char(
        string='City'
    )

    # ===== Quantity & Value =====
    quantity = fields.Integer(
        string='Quantity',
        required=True
    )

    unit_price = fields.Float(
        string='Unit Price'
    )

    total_value = fields.Float(
        string='Total Value',
        compute='_compute_total_value',
        store=True
    )

    # ===== Analysis Fields =====
    is_repeat_product = fields.Boolean(
        string='Repeat Product',
        compute='_compute_repeat_product',
        store=True
    )

    days_since_last_order = fields.Integer(
        string='Days Since Last Order',
        compute='_compute_repeat_product',
        store=True
    )

    @api.depends('shipping_date')
    def _compute_date_fields(self):
        for record in self:
            if record.shipping_date:
                dt = record.shipping_date
                record.shipping_month = dt.strftime('%Y-%m')
                record.shipping_week = dt.isocalendar()[1]
                record.shipping_day = dt.strftime('%A')
            else:
                record.shipping_month = False
                record.shipping_week = 0
                record.shipping_day = False

    @api.depends('quantity', 'unit_price')
    def _compute_total_value(self):
        for record in self:
            record.total_value = record.quantity * record.unit_price

    @api.depends('product_name', 'customer_id', 'shipping_date')
    def _compute_repeat_product(self):
        for record in self:
            # Check if customer ordered this product before
            previous = self.search([
                ('customer_id', '=', record.customer_id.id),
                ('product_name', '=', record.product_name),
                ('shipping_date', '<', record.shipping_date),
                ('id', '!=', record.id)
            ], order='shipping_date desc', limit=1)

            record.is_repeat_product = bool(previous)

            if previous:
                delta = record.shipping_date - previous.shipping_date
                record.days_since_last_order = delta.days
            else:
                record.days_since_last_order = 0