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

    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Carrier',
        compute='_compute_carrier_id',
        store=True
    )

    is_m5_carrier = fields.Boolean(
        compute='_compute_is_m5_carrier',
        store=True
    )

    @api.depends('sale_id.carrier_id')
    def _compute_carrier_id(self):
        """Get carrier from sale order"""
        for picking in self:
            if picking.sale_id and picking.sale_id.carrier_id:
                picking.carrier_id = picking.sale_id.carrier_id
            else:
                picking.carrier_id = False

    @api.depends('carrier_id', 'carrier_id.delivery_type', 'picking_type_id.warehouse_id.m5_enabled')
    def _compute_is_m5_carrier(self):
        """Check if M5 is enabled via carrier or warehouse"""
        for picking in self:
            # Method 1: Via delivery carrier
            if picking.carrier_id and picking.carrier_id.delivery_type == 'm5_wms':
                picking.is_m5_carrier = True
            # Method 2: Via warehouse (legacy support)
            elif picking.picking_type_id.warehouse_id.m5_enabled:
                picking.is_m5_carrier = True
            else:
                picking.is_m5_carrier = False

    @api.depends('picking_type_id.warehouse_id.m5_enabled')
    def _compute_is_m5_enabled(self):
        for picking in self:
            picking.is_m5_enabled = picking.picking_type_id.warehouse_id.m5_enabled or picking.is_m5_carrier

    def action_create_m5_order(self):
        """Open wizard to create M5 order"""
        self.ensure_one()

        if self.picking_type_code != 'outgoing':
            raise UserError(_('M5 orders can only be created for delivery orders!'))

        if self.m5_order_id:
            raise UserError(_('M5 order already created for this delivery!'))

        # Get M5 config from carrier or warehouse
        m5_config = False
        if self.carrier_id and self.carrier_id.delivery_type == 'm5_wms':
            m5_config = self.carrier_id.m5_config_id
        elif self.picking_type_id.warehouse_id.m5_config_id:
            m5_config = self.picking_type_id.warehouse_id.m5_config_id

        if not m5_config:
            raise UserError(_('No M5 configuration found!'))

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
        """Override to remove auto-send to M5"""
        # Just call parent without any M5 auto-creation
        return super().button_validate()