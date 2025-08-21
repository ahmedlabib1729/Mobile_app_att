# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class M5Order(models.Model):
    _name = 'm5.order'
    _description = 'M5 WMS Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='M5 Order ID',
        readonly=True,
        copy=False,
        tracking=True
    )

    plat_order_id = fields.Char(
        string='Platform Order ID',
        required=True,
        tracking=True,
        help='Order ID sent to M5 WMS'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent to M5'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('error', 'Error'),
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

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        related='picking_id.picking_type_id.warehouse_id',
        store=True
    )

    # M5 Data
    m5_client_id = fields.Char(
        string='M5 Client ID',
        readonly=True
    )

    m5_warehouse_id = fields.Char(
        string='M5 Warehouse ID',
        readonly=True
    )

    # Order Details
    order_date = fields.Date(
        string='Order Date',
        required=True,
        default=fields.Date.today
    )

    grand_total = fields.Float(
        string='Grand Total',
        required=True
    )

    cod_amount = fields.Float(
        string='COD Amount',
        default=0.0
    )

    # Customer Details
    first_name = fields.Char(string='First Name', required=True)
    last_name = fields.Char(string='Last Name', required=True)
    email = fields.Char(string='Email', required=True)
    mobile = fields.Char(string='Mobile', required=True)
    address = fields.Text(string='Address', required=True)
    city_id = fields.Integer(string='City ID')
    city_name = fields.Char(string='City Name')

    notes = fields.Text(string='Notes')

    # Response
    response_data = fields.Text(string='API Response')
    error_message = fields.Text(string='Error Message')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        """Generate plat_order_id if not provided"""
        if not vals.get('plat_order_id') and vals.get('picking_id'):
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking.sale_id:
                vals['plat_order_id'] = picking.sale_id.name
            else:
                vals['plat_order_id'] = picking.name
        return super().create(vals)

    def action_send_to_m5(self):
        """Send order to M5 WMS"""
        self.ensure_one()

        if self.state not in ['draft', 'error']:
            raise UserError(_('Order already sent to M5!'))

        # Get M5 config
        config = self.warehouse_id.m5_config_id
        if not config:
            raise UserError(_('No M5 configuration found for warehouse %s!') % self.warehouse_id.name)

        # Prepare order data
        order_data = self._prepare_order_data()

        try:
            # Send to M5
            response = config._make_api_request(
                'sales',
                method='POST',
                data=order_data
            )

            # Update order
            self.write({
                'state': 'sent',
                'response_data': str(response),
                'error_message': False,
                'name': response.get('id') or response.get('order_id') or 'M5-' + self.plat_order_id
            })

            # Add note
            self.message_post(
                body=_('Order sent successfully to M5 WMS'),
                subject=_('M5 Order Created')
            )

            return True

        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise

    def _prepare_order_data(self):
        """Prepare order data for M5 API"""
        self.ensure_one()

        # Get config
        config = self.warehouse_id.m5_config_id

        # Prepare line items
        details = []
        for move in self.picking_id.move_ids:
            if move.product_id.default_code:
                details.append({
                    "quantity": int(move.product_uom_qty),
                    "parent_id": 0,  # Always 0 as per API
                    "product_id": int(move.product_id.default_code),  # Assuming default_code is the M5 product ID
                    "Unit_price": move.product_id.lst_price,
                    "subtotal": move.product_id.lst_price * move.product_uom_qty
                })

        # Prepare data
        data = {
            "date": self.order_date.strftime('%Y-%m-%d'),
            "client_id": int(config.client_id),
            "warehouse_id": int(config.warehouse_id),
            "notes": self.notes or '',
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "mobile": self.mobile,
            "address": self.address,
            "city_id": {
                "label": self.city_name or "Unknown",
                "value": self.city_id or 1
            },
            "cod_amount": self.cod_amount,
            "GrandTotal": self.grand_total,
            "details": details,
            "plat_order_id": self.plat_order_id
        }

        return data