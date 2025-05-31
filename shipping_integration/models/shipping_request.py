from odoo import models, fields, api


class ShippingRequest(models.Model):
    _name = 'shipping.request'
    _description = 'Shipping Request Log'
    _order = 'create_date desc'

    name = fields.Char(string='Request Number', required=True, default='New')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    provider_id = fields.Many2one('shipping.provider', string='Shipping Provider', required=True)

    # Request details
    request_type = fields.Selection([
        ('create', 'Create Shipment'),
        ('label', 'Get Label'),
        ('track', 'Track Shipment'),
        ('cancel', 'Cancel Shipment')
    ], string='Request Type', required=True)

    request_data = fields.Text(string='Request Data')
    response_data = fields.Text(string='Response Data')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('success', 'Success'),
        ('error', 'Error')
    ], string='Status', default='draft')

    error_message = fields.Text(string='Error Message')

    # Tracking info
    tracking_number = fields.Char(string='Tracking Number')
    label_data = fields.Binary(string='Label PDF')
    label_filename = fields.Char(string='Label Filename')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.request') or 'New'
        return super(ShippingRequest, self).create(vals)