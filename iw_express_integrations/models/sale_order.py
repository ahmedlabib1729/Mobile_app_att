# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # IW Shipment Information
    iw_shipment_ids = fields.One2many(
        'iw.shipment',
        compute='_compute_iw_shipments',
        string='IW Shipments',
        compute_sudo=True
    )

    iw_shipment_count = fields.Integer(
        compute='_compute_iw_shipments',
        string='IW Shipment Count',
        store=True
    )

    # Direct IW Info
    iw_consignment_refs = fields.Text(
        string='IW Consignment References',
        compute='_compute_iw_info',
        store=True
    )

    iw_tracking_urls = fields.Text(
        string='IW Tracking URLs',
        compute='_compute_iw_info',
        store=True
    )

    iw_shipment_state = fields.Selection([
        ('none', 'No Shipment'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('pickup_scheduled', 'Pickup Scheduled'),
        ('pickup_completed', 'Pickup Completed'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('attempted', 'Attempted'),
        ('rto', 'Return to Origin'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
        ('mixed', 'Mixed Status')
    ], string='IW Status', compute='_compute_iw_info', store=True)

    # IW specific carrier info
    is_iw_carrier = fields.Boolean(
        string='Is IW Carrier',
        compute='_compute_is_iw_carrier',
        store=True
    )

    iw_service_type = fields.Selection(
        related='carrier_id.iw_service_type',
        string='IW Service Type',
        readonly=True,
        store=True
    )

    iw_load_type = fields.Selection(
        related='carrier_id.iw_load_type',
        string='IW Load Type',
        readonly=True,
        store=True
    )

    @api.depends('carrier_id', 'carrier_id.delivery_type')
    def _compute_is_iw_carrier(self):
        for order in self:
            order.is_iw_carrier = order.carrier_id and order.carrier_id.delivery_type == 'iw_express'

    @api.depends('picking_ids.iw_shipment_id')
    def _compute_iw_shipments(self):
        for order in self:
            shipments = order.picking_ids.mapped('iw_shipment_id')
            order.iw_shipment_ids = shipments
            order.iw_shipment_count = len(shipments)

    @api.depends('picking_ids.iw_shipment_id', 'picking_ids.iw_shipment_id.name',
                 'picking_ids.iw_shipment_id.state')
    def _compute_iw_info(self):
        for order in self:
            shipments = order.picking_ids.mapped('iw_shipment_id')

            # Consignment References
            refs = shipments.mapped('name')
            order.iw_consignment_refs = ', '.join(refs) if refs else False

            # Tracking URLs
            tracking_urls = shipments.mapped('tracking_url')
            order.iw_tracking_urls = '\n'.join([url for url in tracking_urls if url]) if tracking_urls else False

            # Overall Status
            if not shipments:
                order.iw_shipment_state = 'none'
            else:
                states = shipments.mapped('state')
                unique_states = set(states)
                if len(unique_states) == 1:
                    order.iw_shipment_state = states[0]
                else:
                    order.iw_shipment_state = 'mixed'

    def action_view_iw_shipments(self):
        """View related IW shipments"""
        self.ensure_one()

        shipments = self.picking_ids.mapped('iw_shipment_id')
        action = self.env["ir.actions.actions"]._for_xml_id("iw_express_integration.action_iw_shipment")

        if len(shipments) > 1:
            action['domain'] = [('id', 'in', shipments.ids)]
        elif len(shipments) == 1:
            form_view = [(self.env.ref('iw_express_integration.view_iw_shipment_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = shipments.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def action_open_iw_tracking(self):
        """Open IW tracking page"""
        self.ensure_one()

        if not self.iw_tracking_urls:
            raise UserError(_('No IW Express tracking URL available.'))

        # If multiple URLs, open the first one
        url = self.iw_tracking_urls.split('\n')[0]

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': '_blank',
        }