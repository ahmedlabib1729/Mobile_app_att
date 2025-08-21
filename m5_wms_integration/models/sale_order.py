# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    m5_order_ids = fields.One2many(
        'm5.order',
        compute='_compute_m5_orders',
        string='M5 Orders',
        compute_sudo=True
    )

    m5_order_count = fields.Integer(
        compute='_compute_m5_orders',
        string='M5 Order Count',
        store=True
    )

    m5_order_state = fields.Selection([
        ('none', 'No Order'),
        ('draft', 'Draft'),
        ('sent', 'Sent to M5'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('error', 'Error'),
        ('mixed', 'Mixed Status')
    ], string='M5 Status', compute='_compute_m5_info', store=True)

    @api.depends('picking_ids.m5_order_id')
    def _compute_m5_orders(self):
        for order in self:
            m5_orders = order.picking_ids.mapped('m5_order_id')
            order.m5_order_ids = m5_orders
            order.m5_order_count = len(m5_orders)

    @api.depends('picking_ids.m5_order_id', 'picking_ids.m5_order_id.state')
    def _compute_m5_info(self):
        for order in self:
            m5_orders = order.picking_ids.mapped('m5_order_id')

            if not m5_orders:
                order.m5_order_state = 'none'
            else:
                states = m5_orders.mapped('state')
                unique_states = set(states)
                if len(unique_states) == 1:
                    order.m5_order_state = states[0]
                else:
                    order.m5_order_state = 'mixed'

    def action_view_m5_orders(self):
        """View related M5 orders"""
        self.ensure_one()

        m5_orders = self.picking_ids.mapped('m5_order_id')
        action = self.env["ir.actions.actions"]._for_xml_id("m5_wms_integration.action_m5_order")

        if len(m5_orders) > 1:
            action['domain'] = [('id', 'in', m5_orders.ids)]
        elif len(m5_orders) == 1:
            form_view = [(self.env.ref('m5_wms_integration.view_m5_order_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = m5_orders.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action