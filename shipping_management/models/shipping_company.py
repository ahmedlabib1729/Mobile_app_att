# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShippingCompany(models.Model):
    _name = 'shipping.company'
    _description = 'Shipping Company'
    _order = 'sequence, name'

    name = fields.Char(
        string='Company Name',
        required=True
    )

    code = fields.Char(
        string='Company Code',
        required=True,
        help='Short code for the company (e.g., ARAMEX, FEDEX, DHL)'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    # ===== Contact Information =====
    phone = fields.Char(
        string='Phone'
    )

    email = fields.Char(
        string='Email'
    )

    website = fields.Char(
        string='Website'
    )

    address = fields.Text(
        string='Address'
    )

    # ===== Services =====
    service_ids = fields.One2many(
        'shipping.company.service',
        'company_id',
        string='Services'
    )

    # ===== Statistics =====
    total_orders = fields.Integer(
        string='Total Orders',
        compute='_compute_statistics'
    )

    delivered_orders = fields.Integer(
        string='Delivered Orders',
        compute='_compute_statistics'
    )

    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_statistics'
    )

    def _compute_statistics(self):
        for company in self:
            orders = self.env['shipping.order'].search([
                ('shipping_company_id', '=', company.id)
            ])

            company.total_orders = len(orders)
            company.delivered_orders = len(orders.filtered(lambda o: o.state == 'delivered'))

            if company.total_orders:
                company.success_rate = (company.delivered_orders / company.total_orders) * 100
            else:
                company.success_rate = 0


class ShippingCompanyService(models.Model):
    """Services offered by shipping companies"""
    _name = 'shipping.company.service'
    _description = 'Shipping Company Service'
    _order = 'sequence, name'

    company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string='Service Name',
        required=True
    )

    code = fields.Char(
        string='Service Code',
        required=True
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    service_type = fields.Selection([
        ('normal', 'Normal'),
        ('express', 'Express'),
        ('same_day', 'Same Day')
    ], string='Service Type', required=True, default='normal')

    delivery_time = fields.Char(
        string='Delivery Time',
        help='e.g., 3-5 days, Next day, Same day'
    )

    # ===== Pricing =====
    base_price = fields.Float(
        string='Base Price (EGP)'
    )

    price_per_kg = fields.Float(
        string='Price per KG'
    )

    cod_fee = fields.Float(
        string='COD Fee',
        help='Cash on Delivery fee'
    )

    insurance_rate = fields.Float(
        string='Insurance Rate (%)',
        help='Insurance rate as percentage of product value'
    )

    # ===== Restrictions =====
    max_weight = fields.Float(
        string='Max Weight (kg)'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    def calculate_price(self, weight, value, cod=False):
        """Calculate shipping price based on service parameters"""
        self.ensure_one()

        price = self.base_price or 0

        if self.price_per_kg and weight:
            price += self.price_per_kg * weight

        if cod and self.cod_fee:
            price += self.cod_fee

        if value and self.insurance_rate:
            price += (value * self.insurance_rate / 100)

        return price