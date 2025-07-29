# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Porter Shipment Information
    porter_shipment_ids = fields.One2many(
        'porter.shipment',
        compute='_compute_porter_shipments',
        string='Porter Shipments',
        compute_sudo=True
    )

    porter_shipment_count = fields.Integer(
        compute='_compute_porter_shipments',
        string='Porter Shipment Count',
        store=True  # إضافة store=True لجعله قابل للبحث
    )

    # Direct Porter Info
    porter_awb_numbers = fields.Text(
        string='Porter AWB Numbers',
        compute='_compute_porter_info',
        store=True
    )

    porter_tracking_urls = fields.Text(
        string='Porter Tracking URLs',
        compute='_compute_porter_info',
        store=True
    )

    porter_pickup_numbers = fields.Text(
        string='Porter Pickup Numbers',
        compute='_compute_porter_info',
        store=True
    )

    porter_shipment_state = fields.Selection([
        ('none', 'No Shipment'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('mixed', 'Mixed Status')
    ], string='Porter Status', compute='_compute_porter_info', store=True)

    # Porter specific carrier info
    is_porter_carrier = fields.Boolean(
        string='Is Porter Carrier',
        compute='_compute_is_porter_carrier',
        store=True
    )

    porter_service_type = fields.Selection(
        related='carrier_id.porter_product_code',
        string='Porter Service Type',
        readonly=True,
        store=True  # إضافة store للبحث
    )

    @api.depends('carrier_id', 'carrier_id.delivery_type')
    def _compute_is_porter_carrier(self):
        for order in self:
            order.is_porter_carrier = order.carrier_id and order.carrier_id.delivery_type == 'porter'

    @api.depends('picking_ids.porter_shipment_id')
    def _compute_porter_shipments(self):
        for order in self:
            shipments = order.picking_ids.mapped('porter_shipment_id')
            order.porter_shipment_ids = shipments
            order.porter_shipment_count = len(shipments)

    @api.depends('picking_ids.porter_shipment_id', 'picking_ids.porter_shipment_id.name',
                 'picking_ids.porter_shipment_id.state')
    def _compute_porter_info(self):
        for order in self:
            shipments = order.picking_ids.mapped('porter_shipment_id')

            # AWB Numbers
            awb_numbers = shipments.mapped('name')
            order.porter_awb_numbers = ', '.join(awb_numbers) if awb_numbers else False

            # Tracking URLs
            tracking_urls = shipments.mapped('tracking_url')
            order.porter_tracking_urls = '\n'.join([url for url in tracking_urls if url]) if tracking_urls else False

            # Pickup Numbers
            pickup_numbers = []
            for shipment in shipments:
                if hasattr(shipment, 'pickup_number') and shipment.pickup_number:
                    pickup_numbers.append(shipment.pickup_number)
            order.porter_pickup_numbers = ', '.join(pickup_numbers) if pickup_numbers else False

            # Overall Status
            if not shipments:
                order.porter_shipment_state = 'none'
            else:
                states = shipments.mapped('state')
                unique_states = set(states)
                if len(unique_states) == 1:
                    order.porter_shipment_state = states[0]
                else:
                    order.porter_shipment_state = 'mixed'

    def action_view_porter_shipments(self):
        """View related Porter shipments"""
        self.ensure_one()

        shipments = self.picking_ids.mapped('porter_shipment_id')
        action = self.env["ir.actions.actions"]._for_xml_id("porter_express_integration.action_porter_shipment")

        if len(shipments) > 1:
            action['domain'] = [('id', 'in', shipments.ids)]
        elif len(shipments) == 1:
            form_view = [(self.env.ref('porter_express_integration.view_porter_shipment_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = shipments.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def action_open_porter_tracking(self):
        """Open Porter tracking page"""
        self.ensure_one()

        if not self.porter_tracking_urls:
            raise UserError(_('No Porter tracking URL available.'))

        # If multiple URLs, open the first one
        url = self.porter_tracking_urls.split('\n')[0]

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': '_blank',
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # يمكن إضافة حقل للتحقق
    has_porter_sku = fields.Boolean(
        string='Has Porter SKU',
        compute='_compute_has_porter_sku',
        store=True
    )

    @api.depends('default_code')
    def _compute_has_porter_sku(self):
        for product in self:
            product.has_porter_sku = bool(product.default_code)
