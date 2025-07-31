# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    m5_order_id = fields.Many2one(
        'm5.order',
        string='M5 Order',
        readonly=True,
        copy=False
    )

    m5_order_state = fields.Selection(
        related='m5_order_id.state',
        string='M5 Status',
        store=True
    )

    is_m5_enabled = fields.Boolean(
        compute='_compute_is_m5_enabled',
        store=True
    )

    @api.depends('picking_type_id.warehouse_id.m5_enabled')
    def _compute_is_m5_enabled(self):
        for picking in self:
            picking.is_m5_enabled = picking.picking_type_id.warehouse_id.m5_enabled

    def action_create_m5_order(self):
        """Open wizard to create M5 order"""
        self.ensure_one()

        if self.picking_type_code != 'outgoing':
            raise UserError(_('M5 orders can only be created for delivery orders!'))

        if self.m5_order_id:
            raise UserError(_('M5 order already created for this delivery!'))

        if not self.picking_type_id.warehouse_id.m5_config_id:
            raise UserError(_('No M5 configuration found for warehouse %s!') % self.picking_type_id.warehouse_id.name)

        # Check all products have default_code
        missing_code_products = []
        for move in self.move_ids:
            if not move.product_id.default_code:
                missing_code_products.append(move.product_id.name)

        if missing_code_products:
            raise UserError(_(
                'Cannot create M5 order!\n\n'
                'The following products need Internal Reference (M5 Product ID):\n%s\n\n'
                'Please add Internal Reference to these products first.'
            ) % '\n'.join(['• ' + name for name in missing_code_products]))

        # Open Wizard
        return {
            'name': _('Create M5 Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'm5.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
            }
        }

    def action_view_m5_order(self):
        """View related M5 order"""
        self.ensure_one()

        if not self.m5_order_id:
            raise UserError(_('No M5 order found!'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('M5 Order'),
            'res_model': 'm5.order',
            'res_id': self.m5_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def button_validate(self):
        """Override to auto-send to M5 if configured"""
        res = super().button_validate()

        # Auto-send to M5 if enabled
        for picking in self:
            if (picking.picking_type_code == 'outgoing' and
                    picking.is_m5_enabled and
                    not picking.m5_order_id and
                    picking.picking_type_id.warehouse_id.m5_config_id.auto_send_orders):

                try:
                    # Create M5 order automatically
                    self._auto_create_m5_order()
                except Exception as e:
                    # Log error but don't block validation
                    picking.message_post(
                        body=_('Failed to auto-create M5 order: %s') % str(e),
                        subject=_('M5 Order Error'),
                        message_type='warning'
                    )

        return res

    def _auto_create_m5_order(self):
        """Auto-create M5 order"""
        self.ensure_one()

        partner = self.partner_id
        sale_order = self.sale_id

        # Calculate totals
        grand_total = sum(self.move_ids.mapped(lambda m: m.product_id.lst_price * m.product_uom_qty))

        # Determine COD
        cod_amount = 0.0
        if sale_order and sale_order.payment_term_id and 'cod' in sale_order.payment_term_id.name.lower():
            cod_amount = grand_total

        # Create M5 order
        m5_order = self.env['m5.order'].create({
            'picking_id': self.id,
            'plat_order_id': sale_order.name if sale_order else self.name,
            'order_date': fields.Date.today(),
            'grand_total': grand_total,
            'cod_amount': cod_amount,
            'first_name': partner.name.split()[0] if partner.name else 'Customer',
            'last_name': partner.name.split()[-1] if partner.name and len(partner.name.split()) > 1 else '',
            'email': partner.email or 'noemail@example.com',
            'mobile': partner.mobile or partner.phone or '0000000000',
            'address': partner.street or 'No Address',
            'city_name': partner.city or 'Unknown',
            'city_id': 1,  # Default city ID
            'notes': f'Auto-created from {self.name}'
        })

        # Send to M5
        m5_order.action_send_to_m5()

        # Link to picking
        self.m5_order_id = m5_order