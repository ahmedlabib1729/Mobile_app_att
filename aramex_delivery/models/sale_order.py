# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ========== Aramex Shipment Information ==========
    aramex_shipment_ids = fields.One2many(
        'aramex.shipment',
        compute='_compute_aramex_shipments',
        string='Aramex Shipments',
        compute_sudo=True
    )

    aramex_shipment_count = fields.Integer(
        compute='_compute_aramex_shipments',
        string='Aramex Shipment Count',
        store=True  # Store for better performance in searches
    )

    # ========== Direct Aramex Info ==========
    aramex_awb_numbers = fields.Text(
        string='Aramex AWB Numbers',
        compute='_compute_aramex_info',
        store=True,
        help='All AWB numbers for this order'
    )

    aramex_tracking_urls = fields.Text(
        string='Aramex Tracking URLs',
        compute='_compute_aramex_info',
        store=True,
        help='Tracking URLs for all shipments'
    )

    aramex_pickup_ids = fields.Text(
        string='Aramex Pickup IDs',
        compute='_compute_aramex_info',
        store=True,
        help='Pickup reference numbers'
    )

    aramex_shipment_state = fields.Selection([
        ('none', 'No Shipment'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
        ('mixed', 'Mixed Status')
    ], string='Aramex Status', compute='_compute_aramex_info', store=True)

    # ========== Aramex Carrier Info ==========
    is_aramex_carrier = fields.Boolean(
        string='Is Aramex Carrier',
        compute='_compute_is_aramex_carrier',
        store=True
    )

    aramex_service_type = fields.Selection(
        related='carrier_id.aramex_default_product_type',
        string='Aramex Service Type',
        readonly=True,
        store=True
    )

    aramex_product_group = fields.Selection(
        related='carrier_id.aramex_default_product_group',
        string='Aramex Product Group',
        readonly=True,
        store=True
    )

    # ========== COD Information ==========
    is_cod_payment = fields.Boolean(
        string='Is COD Payment',
        compute='_compute_cod_info',
        store=True,
        help='Indicates if this is a Cash on Delivery order'
    )

    cod_amount = fields.Monetary(
        string='COD Amount',
        compute='_compute_cod_info',
        store=True,
        help='Amount to be collected on delivery'
    )

    # ========== Compute Methods ==========
    @api.depends('carrier_id', 'carrier_id.delivery_type')
    def _compute_is_aramex_carrier(self):
        """Check if the selected carrier is Aramex"""
        for order in self:
            order.is_aramex_carrier = (
                    order.carrier_id and
                    order.carrier_id.delivery_type == 'aramex'
            )

    @api.depends('picking_ids.aramex_shipment_id')
    def _compute_aramex_shipments(self):
        """Compute Aramex shipments related to this order"""
        for order in self:
            shipments = order.picking_ids.mapped('aramex_shipment_id')
            order.aramex_shipment_ids = shipments
            order.aramex_shipment_count = len(shipments)

    @api.depends(
        'picking_ids.aramex_shipment_id',
        'picking_ids.aramex_shipment_id.awb_number',
        'picking_ids.aramex_shipment_id.state',
        'picking_ids.aramex_shipment_id.tracking_url',
        'picking_ids.aramex_shipment_id.pickup_id'
    )
    def _compute_aramex_info(self):
        """Compute aggregated Aramex information"""
        for order in self:
            shipments = order.picking_ids.mapped('aramex_shipment_id')

            # AWB Numbers
            awb_numbers = shipments.mapped('awb_number')
            awb_numbers = [awb for awb in awb_numbers if awb]  # Filter out empty values
            order.aramex_awb_numbers = ', '.join(awb_numbers) if awb_numbers else False

            # Tracking URLs
            tracking_urls = shipments.mapped('tracking_url')
            tracking_urls = [url for url in tracking_urls if url]
            order.aramex_tracking_urls = '\n'.join(tracking_urls) if tracking_urls else False

            # Pickup IDs
            pickup_ids = shipments.mapped('pickup_id')
            pickup_ids = [pid for pid in pickup_ids if pid]
            order.aramex_pickup_ids = ', '.join(pickup_ids) if pickup_ids else False

            # Overall Status
            if not shipments:
                order.aramex_shipment_state = 'none'
            else:
                states = shipments.mapped('state')
                unique_states = set(states)
                if len(unique_states) == 1:
                    order.aramex_shipment_state = states[0]
                else:
                    # Check for priority states
                    if 'cancelled' in states and len([s for s in states if s != 'cancelled']) == 0:
                        order.aramex_shipment_state = 'cancelled'
                    elif 'delivered' in states and len([s for s in states if s not in ['delivered', 'cancelled']]) == 0:
                        order.aramex_shipment_state = 'delivered'
                    else:
                        order.aramex_shipment_state = 'mixed'

    @api.depends('payment_term_id', 'amount_total')
    def _compute_cod_info(self):
        """Compute COD information"""
        for order in self:
            # Check if payment term indicates COD
            is_cod = False
            if order.payment_term_id:
                # Check payment term name for COD indicators
                payment_name = order.payment_term_id.name.lower()
                cod_keywords = ['cod', 'cash on delivery', 'الدفع عند الاستلام']
                is_cod = any(keyword in payment_name for keyword in cod_keywords)

            order.is_cod_payment = is_cod
            order.cod_amount = order.amount_total if is_cod else 0.0

    # ========== Action Methods ==========
    def action_view_aramex_shipments(self):
        """View related Aramex shipments"""
        self.ensure_one()

        shipments = self.picking_ids.mapped('aramex_shipment_id')
        action = self.env["ir.actions.actions"]._for_xml_id(
            "aramex_delivery.action_aramex_shipment"
        )

        if len(shipments) > 1:
            action['domain'] = [('id', 'in', shipments.ids)]
        elif len(shipments) == 1:
            form_view = [(self.env.ref('aramex_delivery.view_aramex_shipment_form').id, 'form')]
            action['views'] = form_view
            action['res_id'] = shipments.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def action_open_aramex_tracking(self):
        """Open Aramex tracking page(s)"""
        self.ensure_one()

        if not self.aramex_tracking_urls:
            raise UserError(_('No Aramex tracking URL available.'))

        # If single URL, open directly
        urls = self.aramex_tracking_urls.split('\n')
        if len(urls) == 1:
            return {
                'type': 'ir.actions.act_url',
                'url': urls[0],
                'target': '_blank',
            }
        else:
            # Multiple URLs - show them in a message
            message = _('Multiple shipments found. Tracking URLs:\n\n')
            for i, url in enumerate(urls, 1):
                awb = url.split('=')[-1] if '=' in url else f'Shipment {i}'
                message += f'{i}. AWB {awb}:\n{url}\n\n'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Aramex Tracking URLs'),
                    'message': message,
                    'type': 'info',
                    'sticky': True,
                }
            }

    def action_create_aramex_shipments(self):
        """Create Aramex shipments for all deliveries"""
        self.ensure_one()

        if not self.is_aramex_carrier:
            raise UserError(_('This order does not use Aramex delivery method.'))

        # Find pickings without Aramex shipment
        pickings_to_ship = self.picking_ids.filtered(
            lambda p: p.state == 'assigned' and not p.aramex_shipment_id
        )

        if not pickings_to_ship:
            raise UserError(_('No delivery orders ready for Aramex shipment.'))

        # If single picking, open wizard
        if len(pickings_to_ship) == 1:
            return pickings_to_ship.action_create_aramex_shipment()
        else:
            # Multiple pickings - create action to process them
            action = {
                'name': _('Create Aramex Shipments'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', pickings_to_ship.ids)],
                'context': {
                    'search_default_ready': 1,
                    'default_carrier_id': self.carrier_id.id,
                },
                'help': _(
                    '<p class="o_view_nocontent_smiling_face">'
                    'Select delivery orders to create Aramex shipments'
                    '</p>'
                )
            }
            return action

    def action_print_all_aramex_labels(self):
        """Print all Aramex labels for this order"""
        self.ensure_one()

        shipments = self.picking_ids.mapped('aramex_shipment_id')
        if not shipments:
            raise UserError(_('No Aramex shipments found for this order.'))

        # Check if all have labels
        without_labels = shipments.filtered(lambda s: not s.label_pdf)
        if without_labels:
            raise UserError(_(
                'The following shipments do not have labels:\n%s\n\n'
                'Please generate labels first.'
            ) % '\n'.join(without_labels.mapped('awb_number')))

        # If single shipment, print directly
        if len(shipments) == 1:
            return shipments.action_print_label()
        else:
            # Multiple labels - would need a report that combines PDFs
            # For now, show notification with AWB numbers
            awb_list = '\n'.join([
                f'• {s.awb_number} - {s.partner_id.name}'
                for s in shipments
            ])

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Multiple Labels'),
                    'message': _(
                        'Multiple shipments found:\n%s\n\n'
                        'Please print labels individually from delivery orders.'
                    ) % awb_list,
                    'type': 'warning',
                    'sticky': True,
                }
            }

    # ========== Override Methods ==========
    @api.onchange('partner_shipping_id')
    def _onchange_partner_shipping_id_aramex(self):
        """Update delivery method if Aramex is configured for the country"""
        if self.partner_shipping_id and self.partner_shipping_id.country_id:
            # Check if we have Aramex configured for this country
            aramex_carriers = self.env['delivery.carrier'].search([
                ('delivery_type', '=', 'aramex'),
                ('active', '=', True),
                ('company_id', '=', self.company_id.id)
            ])

            for carrier in aramex_carriers:
                try:
                    # Check if this carrier has config for the country
                    config = carrier.get_aramex_config(self.partner_shipping_id)
                    if config and config.country_id == self.partner_shipping_id.country_id:
                        self.carrier_id = carrier
                        break
                except:
                    pass

    def _prepare_delivery_line_vals(self, carrier, price_unit):
        """Override to add Aramex-specific information"""
        vals = super()._prepare_delivery_line_vals(carrier, price_unit)

        if carrier.delivery_type == 'aramex' and self.is_cod_payment:
            # Add COD information to delivery line name
            vals['name'] += _(' (COD: %s %s)') % (
                self.cod_amount,
                self.currency_id.symbol
            )

        return vals

    # ========== Helper Methods ==========
    def _get_aramex_shipment_warnings(self):
        """Get any warnings related to Aramex shipments"""
        self.ensure_one()
        warnings = []

        if self.is_aramex_carrier:
            # Check partner data
            partner = self.partner_shipping_id
            if not partner.country_id:
                warnings.append(_('Customer country is not set'))
            if not partner.city:
                warnings.append(_('Customer city is not set'))
            if not partner.zip and partner.country_id.code in ['SA', 'AE', 'KW']:
                warnings.append(_('Postal code recommended for %s') % partner.country_id.name)
            if not (partner.phone or partner.mobile):
                warnings.append(_('Customer phone number is not set'))

            # Check if all products have SKU
            for line in self.order_line.filtered(lambda l: l.product_id.type != 'service'):
                if not line.product_id.default_code:
                    warnings.append(
                        _('Product "%s" missing Internal Reference (SKU)') %
                        line.product_id.name
                    )

        return warnings

    @api.model
    def _cron_update_aramex_tracking(self):
        """Cron job to update Aramex tracking for recent orders"""
        # Find orders with Aramex shipments that are not yet delivered
        orders = self.search([
            ('is_aramex_carrier', '=', True),
            ('aramex_shipment_state', 'not in', ['delivered', 'cancelled', 'returned', 'none']),
            ('state', '=', 'sale'),
            ('create_date', '>', fields.Datetime.now() - timedelta(days=30))  # Last 30 days
        ])

        for order in orders:
            for shipment in order.aramex_shipment_ids:
                try:
                    shipment.update_tracking_status()
                except Exception as e:
                    _logger.error(
                        f"Failed to update tracking for order {order.name}, "
                        f"AWB {shipment.awb_number}: {str(e)}"
                    )