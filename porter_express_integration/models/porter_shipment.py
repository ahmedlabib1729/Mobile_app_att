# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PorterShipment(models.Model):
    _name = 'porter.shipment'
    _description = 'Porter Express Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='AWB Number',
        readonly=True,
        copy=False,
        tracking=True
    )

    reference2 = fields.Char(
        string='Reference',
        required=True,
        tracking=True
    )

    pickup_number = fields.Char(
        string='Pickup Number',
        help='Porter pickup reference number'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        ondelete='cascade'
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        related='picking_id.sale_id',
        store=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='picking_id.partner_id',
        store=True
    )

    # ========== إضافة حقول المناطق ==========
    consignee_area_id = fields.Many2one(
        'porter.area',
        string='Delivery Area',
        tracking=True,
        help='Delivery area for the customer'
    )

    collection_area_id = fields.Many2one(
        'porter.area',
        string='Collection Area',
        tracking=True,
        help='Collection/pickup area'
    )

    # حقول محسوبة للمعلومات
    consignee_area_name = fields.Char(
        string='Delivery Area Name',
        related='consignee_area_id.name',
        store=True
    )

    consignee_country_id = fields.Many2one(
        'res.country',
        string='Delivery Country',
        related='consignee_area_id.country_id',
        store=True
    )
    # =====================================

    # Shipment Details
    product_code = fields.Selection([
        ('DE', 'Delivery Express'),
        ('SD', 'Same Day'),
        ('ND', 'Next Day'),
    ], string='Service Type', default='DE', required=True)

    pieces = fields.Integer(string='Pieces', default=1)
    weight = fields.Float(string='Weight (KG)', required=True)

    cod_amount = fields.Float(string='COD Amount')
    cod_currency = fields.Many2one('res.currency', string='COD Currency')

    # Tracking
    tracking_url = fields.Char(
        string='Tracking URL',
        compute='_compute_tracking_url',
        store=True
    )

    label_pdf = fields.Binary(string='Shipping Label', attachment=True)
    label_filename = fields.Char(string='Label Filename')

    # Dates
    pickup_date = fields.Date(string='Pickup Date')
    delivery_date = fields.Datetime(string='Delivery Date')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    @api.depends('name')
    def _compute_tracking_url(self):
        for record in self:
            if record.name:
                # يمكنك تغيير هذا الرابط حسب Porter Express
                record.tracking_url = f"https://porterex.com/track/{record.name}"
            else:
                record.tracking_url = False

    def name_get(self):
        """تحسين عرض اسم الشحنة"""
        result = []
        for shipment in self:
            if shipment.consignee_area_id:
                name = f"{shipment.name} - {shipment.consignee_area_id.name}"
            else:
                name = shipment.name or 'New'
            result.append((shipment.id, name))
        return result