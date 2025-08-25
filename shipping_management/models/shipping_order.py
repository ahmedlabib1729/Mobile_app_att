# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ShippingOrder(models.Model):
    _name = 'shipping.order'
    _description = 'Shipping Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'order_number'

    # ===== Basic Information =====
    order_number = fields.Char(
        string='Order Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        domain=[('is_company', '=', False)]
    )

    customer_type = fields.Selection(
        related='customer_id.customer_type',
        string='Customer Type',
        store=True
    )

    order_date = fields.Datetime(
        string='Order Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )

    # ===== Sender Information =====
    sender_name = fields.Char(
        string='Sender Name',
        required=True,
        tracking=True
    )

    sender_phone = fields.Char(
        string='Sender Phone',
        required=True,
        tracking=True
    )

    sender_email = fields.Char(
        string='Sender Email',
        tracking=True
    )

    sender_governorate = fields.Many2one(
        'res.country.state',
        string='Sender Governorate',
        domain="[('country_id.code', '=', 'EG')]",
        required=True
    )

    sender_city = fields.Char(
        string='Sender City',
        required=True
    )

    sender_address = fields.Text(
        string='Sender Address',
        required=True
    )

    # ===== Receiver Information =====
    receiver_name = fields.Char(
        string='Receiver Name',
        required=True,
        tracking=True
    )

    receiver_phone = fields.Char(
        string='Receiver Phone',
        required=True,
        tracking=True
    )

    receiver_email = fields.Char(
        string='Receiver Email',
        tracking=True
    )

    receiver_governorate = fields.Many2one(
        'res.country.state',
        string='Receiver Governorate',
        domain="[('country_id.code', '=', 'EG')]",
        required=True
    )

    receiver_city = fields.Char(
        string='Receiver City',
        required=True
    )

    receiver_address = fields.Text(
        string='Receiver Address',
        required=True
    )

    same_as_sender = fields.Boolean(
        string='Same as Sender',
        help='Check if receiver address is same as sender (for returns)'
    )

    # ===== Shipping Details =====
    shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        required=True,
        tracking=True
    )

    shipping_type = fields.Selection([
        ('normal', 'Normal (3-5 days) - 50 EGP'),
        ('express', 'Express (1-2 days) - 75 EGP'),
        ('same_day', 'Same Day - 150 EGP')
    ], string='Shipping Type', required=True, default='normal', tracking=True)

    tracking_number = fields.Char(
        string='Tracking Number',
        readonly=True,
        copy=False,
        tracking=True
    )

    external_tracking_number = fields.Char(
        string='External Tracking Number',
        help='Tracking number from shipping company',
        tracking=True
    )

    # ===== Products =====
    order_line_ids = fields.One2many(
        'shipping.order.line',
        'order_id',
        string='Products'
    )

    # ===== Additional Services =====
    special_packaging = fields.Boolean(
        string='Special Packaging (+20 EGP)'
    )

    insurance = fields.Boolean(
        string='Insurance (+2% of value)'
    )

    open_package = fields.Boolean(
        string='Open Package on Delivery (+15 EGP)'
    )

    # ===== Financial Information =====
    products_value = fields.Float(
        string='Products Value',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )

    shipping_cost = fields.Float(
        string='Shipping Cost',
        compute='_compute_amounts',
        store=True
    )

    additional_services_cost = fields.Float(
        string='Additional Services Cost',
        compute='_compute_amounts',
        store=True
    )

    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )

    cod_amount = fields.Float(
        string='COD Amount',
        help='Cash on Delivery Amount'
    )

    payment_method = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('cod', 'Cash on Delivery'),
        ('cod_receiver', 'Receiver Pays'),
        ('credit', 'Credit Account')
    ], string='Payment Method', required=True, default='prepaid', tracking=True)

    # ===== Status =====
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('picked', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, index=True)

    delivery_date = fields.Datetime(
        string='Delivery Date',
        tracking=True
    )

    expected_delivery_date = fields.Date(
        string='Expected Delivery Date',
        compute='_compute_expected_delivery',
        store=True
    )

    # ===== Notes =====
    internal_notes = fields.Text(
        string='Internal Notes'
    )

    delivery_notes = fields.Text(
        string='Delivery Notes'
    )

    # ===== Computed Fields for Analysis =====
    total_weight = fields.Float(
        string='Total Weight (kg)',
        compute='_compute_total_weight',
        store=True
    )

    products_count = fields.Integer(
        string='Products Count',
        compute='_compute_products_count',
        store=True
    )

    @api.depends('order_line_ids.subtotal')
    def _compute_amounts(self):
        for order in self:
            # Products value
            order.products_value = sum(order.order_line_ids.mapped('subtotal'))

            # Shipping cost based on type
            shipping_costs = {
                'normal': 50.0,
                'express': 75.0,
                'same_day': 150.0
            }
            order.shipping_cost = shipping_costs.get(order.shipping_type, 50.0)

            # Additional services
            additional = 0.0
            if order.special_packaging:
                additional += 20.0
            if order.insurance:
                additional += order.products_value * 0.02
            if order.open_package:
                additional += 15.0

            order.additional_services_cost = additional
            order.total_amount = order.products_value + order.shipping_cost + additional

    @api.depends('order_line_ids.weight')
    def _compute_total_weight(self):
        for order in self:
            order.total_weight = sum(order.order_line_ids.mapped('weight'))

    @api.depends('order_line_ids')
    def _compute_products_count(self):
        for order in self:
            order.products_count = len(order.order_line_ids)

    @api.depends('order_date', 'shipping_type')
    def _compute_expected_delivery(self):
        for order in self:
            if order.order_date:
                days = {'normal': 4, 'express': 2, 'same_day': 0}
                delta = days.get(order.shipping_type, 4)
                order.expected_delivery_date = order.order_date.date() + timedelta(days=delta)
            else:
                order.expected_delivery_date = False

    @api.onchange('same_as_sender')
    def _onchange_same_as_sender(self):
        if self.same_as_sender:
            self.receiver_name = self.sender_name
            self.receiver_phone = self.sender_phone
            self.receiver_email = self.sender_email
            self.receiver_governorate = self.sender_governorate
            self.receiver_city = self.sender_city
            self.receiver_address = self.sender_address

    @api.model
    def create(self, vals):
        if vals.get('order_number', _('New')) == _('New'):
            vals['order_number'] = self.env['ir.sequence'].next_by_code('shipping.order') or _('New')

        result = super(ShippingOrder, self).create(vals)

        # Update customer profile
        result._update_customer_profile()

        # Create product analysis records
        result._create_product_analysis()

        return result

    def write(self, vals):
        result = super(ShippingOrder, self).write(vals)

        if 'state' in vals and vals['state'] == 'delivered':
            self.delivery_date = fields.Datetime.now()
            self._update_customer_metrics()

        return result

    def _update_customer_profile(self):
        """Update customer profile with new order data"""
        for order in self:
            if order.customer_id:
                profile = self.env['customer.profile'].search([
                    ('customer_id', '=', order.customer_id.id)
                ], limit=1)

                if not profile:
                    profile = self.env['customer.profile'].create({
                        'customer_id': order.customer_id.id
                    })

                profile._compute_statistics()

    def _create_product_analysis(self):
        """Create product analysis records for ordered products"""
        for order in self:
            for line in order.order_line_ids:
                self.env['product.analysis'].create({
                    'product_name': line.product_name,
                    'category_id': line.category_id.id,
                    'subcategory_id': line.subcategory_id.id,
                    'brand': line.brand,
                    'quantity': line.quantity,
                    'order_id': order.id,
                    'customer_id': order.customer_id.id,
                    'shipping_date': order.order_date,
                    'governorate_id': order.receiver_governorate.id,
                })

    def _update_customer_metrics(self):
        """Update customer metrics when order is delivered"""
        for order in self:
            if order.customer_id:
                order.customer_id._compute_customer_statistics()

    # ===== Action Methods =====
    def action_view_customer_profile(self):
        """View customer profile"""
        self.ensure_one()
        profile = self.env['customer.profile'].search([
            ('customer_id', '=', self.customer_id.id)
        ], limit=1)

        if not profile:
            profile = self.env['customer.profile'].create({
                'customer_id': self.customer_id.id
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Profile'),
            'res_model': 'customer.profile',
            'view_mode': 'form',
            'res_id': profile.id,
            'target': 'current'
        }

    def action_view_product_analysis(self):
        """View product analysis for this order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Analysis'),
            'res_model': 'product.analysis',
            'view_mode': 'list,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id}
        }

    def action_confirm(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_('Only draft orders can be confirmed.'))

            # Validate order lines
            if not order.order_line_ids:
                raise ValidationError(_('Please add at least one product.'))

            # Send to shipping company API
            order._send_to_shipping_company()

            order.state = 'confirmed'

            # Send confirmation email
            order._send_confirmation_email()

    def action_cancel(self):
        for order in self:
            if order.state in ['delivered', 'returned']:
                raise UserError(_('Cannot cancel delivered or returned orders.'))
            order.state = 'cancelled'

    def action_set_delivered(self):
        for order in self:
            order.state = 'delivered'
            order.delivery_date = fields.Datetime.now()

    def action_return(self):
        for order in self:
            if order.state != 'delivered':
                raise UserError(_('Only delivered orders can be returned.'))
            order.state = 'returned'

    def _send_to_shipping_company(self):
        """Mark order as sent to shipping company"""
        for order in self:
            # Generate a dummy tracking number for now
            order.tracking_number = f"TRK-{order.order_number}"
            _logger.info(f"Order {order.order_number} sent to {order.shipping_company_id.name}")

    def _send_confirmation_email(self):
        """Send confirmation email to customer"""
        for order in self:
            template = self.env.ref('shipping_management.email_template_order_confirmation', False)
            if template:
                template.send_mail(order.id, force_send=True)

    def action_print_label(self):
        """Print shipping label"""
        return self.env.ref('shipping_management.action_report_shipping_label').report_action(self)

    def action_track_shipment(self):
        """Open tracking URL or show tracking info"""
        for order in self:
            if order.tracking_number:
                # For now, just show a message
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Tracking Number'),
                        'message': f'Tracking Number: {order.tracking_number}',
                        'type': 'info',
                        'sticky': False,
                    }
                }

    @api.model
    def get_dashboard_data(self):
        """Get data for dashboard"""
        today = fields.Date.today()

        # Today's orders
        today_orders = self.search_count([
            ('order_date', '>=', today),
            ('order_date', '<', today + timedelta(days=1))
        ])

        # This week's orders
        week_start = today - timedelta(days=today.weekday())
        week_orders = self.search_count([
            ('order_date', '>=', week_start),
            ('order_date', '<', today + timedelta(days=1))
        ])

        # This month's revenue
        month_start = today.replace(day=1)
        month_orders = self.search([
            ('order_date', '>=', month_start),
            ('state', 'in', ['confirmed', 'picked', 'in_transit', 'out_for_delivery', 'delivered'])
        ])
        month_revenue = sum(month_orders.mapped('total_amount'))

        return {
            'today_orders': today_orders,
            'week_orders': week_orders,
            'month_revenue': month_revenue,
        }