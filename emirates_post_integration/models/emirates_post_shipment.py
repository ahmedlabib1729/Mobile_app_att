# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EmiratesPostShipment(models.Model):
    _name = 'emirates.post.shipment'
    _description = 'Emirates Post Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='AWB Number',
        readonly=True,
        copy=False,
        tracking=True,
        help='Emirates Post AWB number'
    )

    reference_no = fields.Char(
        string='Reference Number',
        required=True,
        tracking=True,
        help='Your reference number'
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
        ondelete='cascade',
        required=True
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

    # Sender Details
    sender_name = fields.Char(string='Sender Name', required=True)
    sender_company = fields.Char(string='Sender Company')
    sender_address = fields.Text(string='Sender Address', required=True)
    sender_city = fields.Many2one('emirates.post.emirate', string='Sender City', required=True)
    sender_phone = fields.Char(string='Sender Phone', required=True)
    sender_mobile = fields.Char(string='Sender Mobile', required=True)
    sender_email = fields.Char(string='Sender Email')

    # Receiver Details
    receiver_name = fields.Char(string='Receiver Name', required=True)
    receiver_company = fields.Char(string='Receiver Company')
    receiver_address = fields.Text(string='Receiver Address', required=True)

    # Modified receiver location fields to support international shipping
    receiver_country_id = fields.Many2one(
        'res.country',
        string='Receiver Country',
        required=True,
        default=lambda self: self.env.ref('base.ae')  # Default to UAE
    )
    receiver_state_id = fields.Many2one(
        'res.country.state',
        string='Receiver State/Province',
        domain="[('country_id', '=', receiver_country_id)]"
    )
    # For UAE shipments, still use emirate
    receiver_emirate_id = fields.Many2one(
        'emirates.post.emirate',
        string='Receiver Emirate',
        domain="[('active', '=', True)]"
    )
    # Free text city field for international shipments
    receiver_city_name = fields.Char(
        string='Receiver City',
        help='City name for international shipments'
    )

    # Computed field to determine if it's domestic (UAE) shipment
    is_domestic_shipment = fields.Boolean(
        string='Is Domestic Shipment',
        compute='_compute_is_domestic_shipment',
        store=True
    )

    receiver_phone = fields.Char(string='Receiver Phone', required=True)
    receiver_mobile = fields.Char(string='Receiver Mobile', required=True)
    receiver_email = fields.Char(string='Receiver Email')

    # Shipment Details
    cod_amount = fields.Float(string='COD Amount')
    pieces = fields.Integer(string='Pieces', default=1, required=True)
    weight = fields.Float(string='Weight (g)', required=True)
    length = fields.Float(string='Length (cm)')
    width = fields.Float(string='Width (cm)')
    height = fields.Float(string='Height (cm)')
    item_value = fields.Float(string='Item Value')
    commodity_description = fields.Text(string='Description', required=True)

    # Label
    label_data = fields.Binary(string='Label PDF', readonly=True)
    label_filename = fields.Char(string='Label Filename')

    # Tracking
    tracking_url = fields.Char(
        string='Tracking URL',
        compute='_compute_tracking_url',
        store=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    @api.depends('receiver_country_id')
    def _compute_is_domestic_shipment(self):
        uae_country = self.env.ref('base.ae', raise_if_not_found=False)
        for record in self:
            record.is_domestic_shipment = record.receiver_country_id == uae_country

    @api.depends('name')
    def _compute_tracking_url(self):
        for record in self:
            if record.name:
                # Update with actual Emirates Post tracking URL
                record.tracking_url = f"https://www.emiratespost.ae/track/{record.name}"
            else:
                record.tracking_url = False

    @api.onchange('receiver_country_id')
    def _onchange_receiver_country_id(self):
        """Clear state/emirate when country changes"""
        self.receiver_state_id = False
        self.receiver_emirate_id = False
        self.receiver_city_name = False

    def action_track_shipment(self):
        """Open tracking URL in browser"""
        self.ensure_one()
        if not self.tracking_url:
            raise UserError(_('No tracking URL available.'))

        return {
            'type': 'ir.actions.act_url',
            'url': self.tracking_url,
            'target': '_blank',
        }

    def get_receiver_city_for_api(self):
        """Get the appropriate city value for API calls"""
        self.ensure_one()
        if self.is_domestic_shipment and self.receiver_emirate_id:
            return int(self.receiver_emirate_id.emirate_id)
        else:
            # For international shipments, you might need to map cities or use a different API field
            return self.receiver_city_name or self.receiver_state_id.name or 'N/A'

    def get_receiver_country_code_for_api(self):
        """Get country code for API"""
        self.ensure_one()
        if self.receiver_country_id.phone_code:
            return int(self.receiver_country_id.phone_code)
        return 971  # Default to UAE if no phone code