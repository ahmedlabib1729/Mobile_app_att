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

    # Product Lines for display
    product_line_ids = fields.One2many(
        'm5.order.wizard.line',
        'wizard_id',
        string='Products',
        compute='_compute_product_lines'
    )

    @api.depends('picking_id', 'picking_id.move_ids')
    def _compute_product_lines(self):
        """Create product lines for display"""
        for wizard in self:
            lines = []
            if wizard.picking_id:
                for move in wizard.picking_id.move_ids:
                    lines.append((0, 0, {
                        'product_id': move.product_id.id,
                        'm5_product_id': move.product_id.default_code or 'NOT SET',
                        'quantity': move.product_uom_qty,
                        'unit_price': move.product_id.lst_price,
                    }))
            wizard.product_line_ids = lines

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

    def action_create_shipment(self):
        """إرسال مباشر لـ M5 API"""
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

        # Get M5 config
        config = self.warehouse_id.m5_config_id
        if not config:
            # Try from carrier if exists
            if hasattr(self.picking_id, 'carrier_id') and self.picking_id.carrier_id:
                if hasattr(self.picking_id.carrier_id, 'm5_config_id'):
                    config = self.picking_id.carrier_id.m5_config_id

        if not config:
            raise UserError(_('No M5 configuration found!'))

        # Prepare line items for API
        details = []
        for move in self.picking_id.move_ids:
            if move.product_id.default_code:
                details.append({
                    "quantity": int(move.product_uom_qty),
                    "parent_id": 0,  # Always 0 as per API
                    "product_id": int(move.product_id.default_code),
                    "Unit_price": move.product_id.lst_price,
                    "subtotal": move.product_id.lst_price * move.product_uom_qty
                })

        # Prepare API data
        api_data = {
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

        try:
            # Send directly to M5 API
            response = config._make_api_request(
                'sales',
                method='POST',
                data=api_data
            )

            # Extract M5 order ID from response
            m5_order_id = response.get('id') or response.get('order_id') or 'M5-' + self.plat_order_id

            # Now create the order record in Odoo with the response
            m5_order = self.env['m5.order'].create({
                'name': m5_order_id,  # M5 Order ID from response
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
                'm5_client_id': config.client_id,
                'm5_warehouse_id': config.warehouse_id,
                'state': 'sent',  # Already sent
                'response_data': str(response),
                'error_message': False
            })

            # Link to picking
            self.picking_id.m5_order_id = m5_order

            # Add note to picking
            self.picking_id.message_post(
                body=_(
                    '<b>M5 Order Created Successfully!</b><br/>'
                    '<b>M5 Order ID:</b> %(m5_id)s<br/>'
                    '<b>Platform Order ID:</b> %(plat_id)s<br/>'
                    '<b>Total:</b> %(total).2f<br/>'
                    '<b>COD:</b> %(cod).2f',
                    m5_id=m5_order_id,
                    plat_id=self.plat_order_id,
                    total=self.grand_total,
                    cod=self.cod_amount
                ),
                subject=_('M5 Order Created')
            )

            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _(
                        'Order sent to M5 WMS successfully!\n'
                        'M5 Order ID: %(m5_id)s',
                        m5_id=m5_order_id
                    ),
                    'type': 'success',
                    'sticky': True,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        except Exception as e:
            # في حالة الخطأ، لا نحفظ أي شيء
            raise UserError(_(
                'Failed to send order to M5:\n%(error)s',
                error=str(e)
            ))


class M5OrderWizardLine(models.TransientModel):
    _name = 'm5.order.wizard.line'
    _description = 'M5 Order Wizard Product Line'

    wizard_id = fields.Many2one('m5.order.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    m5_product_id = fields.Char(string='M5 Product ID', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    unit_price = fields.Float(string='Unit Price', readonly=True)