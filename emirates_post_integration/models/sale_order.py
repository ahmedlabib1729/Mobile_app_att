from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    emirates_post_shipment_ids = fields.One2many(
        'emirates.post.shipment',
        compute='_compute_emirates_post_shipments',
        string='Emirates Post Shipments',
        compute_sudo=True
    )

    emirates_post_shipment_count = fields.Integer(
        compute='_compute_emirates_post_shipments',
        string='Emirates Post Shipment Count',
        store=True
    )

    emirates_post_awb_numbers = fields.Text(
        string='Emirates Post AWB Numbers',
        compute='_compute_emirates_post_info',
        store=True
    )

    emirates_post_tracking_urls = fields.Text(
        string='Emirates Post Tracking URLs',
        compute='_compute_emirates_post_info',
        store=True
    )

    emirates_post_shipment_state = fields.Selection([
        ('none', 'No Shipment'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('mixed', 'Mixed Status')
    ], string='Emirates Post Status', compute='_compute_emirates_post_info', store=True)

    is_emirates_post_carrier = fields.Boolean(
        string='Is Emirates Post Carrier',
        compute='_compute_is_emirates_post_carrier',
        store=True
    )

    @api.depends('carrier_id', 'carrier_id.delivery_type')
    def _compute_is_emirates_post_carrier(self):
        for order in self:
            order.is_emirates_post_carrier = order.carrier_id and order.carrier_id.delivery_type == 'emirates_post'

    @api.depends('picking_ids.emirates_post_shipment_id')
    def _compute_emirates_post_shipments(self):
        for order in self:
            shipments = order.picking_ids.mapped('emirates_post_shipment_id')
            order.emirates_post_shipment_ids = shipments
            order.emirates_post_shipment_count = len(shipments)

    @api.depends('picking_ids.emirates_post_shipment_id', 'picking_ids.emirates_post_shipment_id.name',
                 'picking_ids.emirates_post_shipment_id.state')
    def _compute_emirates_post_info(self):
        for order in self:
            shipments = order.picking_ids.mapped('emirates_post_shipment_id')

            # AWB Numbers
            awb_numbers = shipments.mapped('name')
            order.emirates_post_awb_numbers = ', '.join(awb_numbers) if awb_numbers else False

            # Tracking URLs
            tracking_urls = shipments.mapped('tracking_url')
            order.emirates_post_tracking_urls = '\n'.join([url for url in tracking_urls if url]) if tracking_urls else False

            # Overall Status
            if not shipments:
                order.emirates_post_shipment_state = 'none'
            else:
                states = shipments.mapped('state')
                unique_states = set(states)
                if len(unique_states) == 1:
                    order.emirates_post_shipment_state = states[0]
                else:
                    order.emirates_post_shipment_state = 'mixed'

    def action_view_emirates_post_shipments(self):
        """View related Emirates Post shipments"""
        self.ensure_one()

        shipments = self.picking_ids.mapped('emirates_post_shipment_id')
        action = self.env["ir.actions.actions"]._for_xml_id("emirates_post_integration.action_emirates_post_shipment")

        if len(shipments) > 1:
            action['domain'] = [('id', 'in', shipments.ids)]
        elif len(shipments) == 1:
            form_view = [(self.env.ref('emirates_post_integration.view_emirates_post_shipment_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = shipments.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def action_open_emirates_post_tracking(self):
        """Open Emirates Post tracking page"""
        self.ensure_one()

        if not self.emirates_post_tracking_urls:
            raise UserError(_('No Emirates Post tracking URL available.'))

        # If multiple URLs, open the first one
        url = self.emirates_post_tracking_urls.split('\n')[0]

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': '_blank',
        }
