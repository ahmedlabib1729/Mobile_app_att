# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class M5OrderWizard(models.TransientModel):
    _name = 'm5.order.wizard'
    _description = 'M5 Order Creation Wizard'

    # Basic Information
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        required=True,
        readonly=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='picking_id.partner_id',
        readonly=True
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        related='picking_id.picking_type_id.warehouse_id',
        readonly=True
    )

    # Order Details
    plat_order_id = fields.Char(
        string='Platform Order ID',
        required=True,
        help='Order ID to send to M5 WMS'
    )

    order_date = fields.Date(
        string='Order Date',
        required=True,
        default=fields.Date.today
    )

    # Customer Details
    first_name = fields.Char(
        string='First Name',
        required=True
    )

    last_name = fields.Char(
        string='Last Name',
        required=True
    )

    email = fields.Char(
        string='Email',
        required=True
    )

    mobile = fields.Char(
        string='Mobile',
        required=True
    )

    address = fields.Text(
        string='Address',
        required=True
    )

    city_name = fields.Char(
        string='City Name',
        required=True
    )

    city_id = fields.Integer(
        string='City ID',
        default=1,
        required=True,
        help='M5 City ID (default: 1)'
    )

    # Financial
    grand_total = fields.Float(
        string='Grand Total',
        required=True,
        compute='_compute_totals',
        store=True,
        readonly=False
    )

    is_cod = fields.Boolean(
        string='Cash on Delivery'
    )

    cod_amount = fields.Float(
        string='COD Amount'
    )

    # Notes
    notes = fields.Text(
        string='Notes',
        default='Order created from Odoo'
    )

    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        res = super().default_get(fields_list)

        if self.env.context.get('default_picking_id'):
            picking = self.env['stock.picking'].browse(self.env.context['default_picking_id'])
            partner = picking.partner_id

            # Set order reference
            if picking.sale_id:
                res['plat_order_id'] = picking.sale_id.name
            else:
                res['plat_order_id'] = picking.name

            # Set customer details
            if partner:
                # Split name
                name_parts = partner.name.split() if partner.name else ['Customer']
                res['first_name'] = name_parts[0]
                res['last_name'] = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                # Contact info
                res['email'] = partner.email or 'noemail@example.com'
                res['mobile'] = partner.mobile or partner.phone or '0000000000'

                # Address
                address_parts = []
                if partner.street:
                    address_parts.append(partner.street)
                if partner.street2:
                    address_parts.append(partner.street2)
                if partner.city:
                    address_parts.append(partner.city)
                if partner.state_id:
                    address_parts.append(partner.state_id.name)
                if partner.country_id:
                    address_parts.append(partner.country_id.name)

                res['address'] = ', '.join(address_parts) or 'No Address'
                res['city_name'] = partner.city or 'Unknown'

            # Check if COD
            if picking.sale_id and picking.sale_id.payment_term_id:
                if 'cod' in picking.sale_id.payment_term_id.name.lower():
                    res['is_cod'] = True

        return res

    @api.depends('picking_id', 'picking_id.move_ids')
    def _compute_totals(self):
        """Calculate grand total"""
        for wizard in self:
            if wizard.picking_id:
                total = sum(
                    move.product_id.lst_price * move.product_uom_qty
                    for move in wizard.picking_id.move_ids
                )
                wizard.grand_total = total
            else:
                wizard.grand_total = 0.0

    @api.onchange('is_cod', 'grand_total')
    def _onchange_is_cod(self):
        """Set COD amount"""
        if self.is_cod:
            self.cod_amount = self.grand_total
        else:
            self.cod_amount = 0.0

    def action_create_order(self):
        """Create and send M5 order"""
        self.ensure_one()

        # Validate
        if not self.email or '@' not in self.email:
            raise ValidationError(_('Please enter a valid email address!'))

        if not self.mobile:
            raise ValidationError(_('Mobile number is required!'))

        # Check products have default_code
        missing_products = []
        for move in self.picking_id.move_ids:
            if not move.product_id.default_code:
                missing_products.append(move.product_id.name)

        if missing_products:
            raise UserError(_(
                'The following products need Internal Reference (M5 Product ID):\n%s'
            ) % '\n'.join(['• ' + name for name in missing_products]))

        # Create M5 order
        m5_order = self.env['m5.order'].create({
            'picking_id': self.picking_id.id,
            'plat_order_id': self.plat_order_id,
            'order_date': self.order_date,
            'grand_total': self.grand_total,
            'cod_amount': self.cod_amount,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'mobile': self.mobile,
            'address': self.address,
            'city_name': self.city_name,
            'city_id': self.city_id,
            'notes': self.notes,
            'm5_client_id': self.warehouse_id.m5_config_id.client_id,
            'm5_warehouse_id': self.warehouse_id.m5_config_id.warehouse_id,
        })

        # Send to M5
        try:
            m5_order.action_send_to_m5()

            # Link to picking
            self.picking_id.m5_order_id = m5_order

            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('M5 order created successfully!'),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        except Exception as e:
            raise UserError(_(
                'Failed to create M5 order:\n%(error)s',
                error=str(e)
            ))