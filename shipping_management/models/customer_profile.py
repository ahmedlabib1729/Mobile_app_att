# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CustomerProfile(models.Model):
    _name = 'customer.profile'
    _description = 'Customer Profile Analysis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'customer_id'

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True,
        tracking=True
    )

    # ===== Customer Classification =====
    customer_type = fields.Selection([
        ('vip', 'VIP Customer'),
        ('active', 'Active Customer'),
        ('normal', 'Normal Customer'),
        ('cold', 'Cold Customer'),
        ('new', 'New Customer')
    ], string='Customer Type', default='new', tracking=True)

    # ===== Order Statistics =====
    total_orders = fields.Integer(
        string='Total Orders',
        default=0
    )

    delivered_orders = fields.Integer(
        string='Delivered Orders',
        default=0
    )

    cancelled_orders = fields.Integer(
        string='Cancelled Orders',
        default=0
    )

    returned_orders = fields.Integer(
        string='Returned Orders',
        default=0
    )

    # ===== Financial Statistics =====
    total_revenue = fields.Float(
        string='Total Revenue (EGP)',
        default=0.0,
        tracking=True
    )

    avg_order_value = fields.Float(
        string='Average Order Value',
        default=0.0
    )

    total_products_shipped = fields.Integer(
        string='Total Products Shipped',
        default=0
    )

    # ===== Time-based Analysis =====
    first_order_date = fields.Datetime(
        string='First Order Date'
    )

    last_order_date = fields.Datetime(
        string='Last Order Date',
        tracking=True
    )

    days_since_last_order = fields.Integer(
        string='Days Since Last Order',
        compute='_compute_days_since_last_order'
    )

    customer_lifetime_days = fields.Integer(
        string='Customer Lifetime (Days)',
        default=0
    )

    # ===== Simple Text Fields Instead of Relations =====
    top_brand = fields.Char(
        string='Top Brand'
    )

    preferred_shipping_type = fields.Selection([
        ('normal', 'Normal'),
        ('express', 'Express'),
        ('same_day', 'Same Day')
    ], string='Preferred Shipping Type')

    preferred_payment_method = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('cod', 'Cash on Delivery'),
        ('credit', 'Credit Account')
    ], string='Preferred Payment Method')

    most_common_city = fields.Char(
        string='Most Common City'
    )

    # ===== Loyalty & Engagement =====
    loyalty_points = fields.Integer(
        string='Loyalty Points',
        default=0,
        tracking=True
    )

    loyalty_tier = fields.Selection([
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum')
    ], string='Loyalty Tier', default='bronze')

    referral_count = fields.Integer(
        string='Referrals Made',
        default=0
    )

    # ===== Predictive Analytics =====
    churn_risk = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk')
    ], string='Churn Risk', default='low')

    predicted_next_order_date = fields.Date(
        string='Predicted Next Order'
    )

    predicted_next_order_value = fields.Float(
        string='Predicted Order Value',
        default=0.0
    )

    # ===== Customer Lifetime Value =====
    clv = fields.Float(
        string='Customer Lifetime Value',
        default=0.0,
        help='Predicted total value of customer over their lifetime'
    )

    # ===== Marketing =====
    email_subscribed = fields.Boolean(
        string='Email Subscribed',
        default=True
    )

    sms_subscribed = fields.Boolean(
        string='SMS Subscribed',
        default=True
    )

    campaign_response_rate = fields.Float(
        string='Campaign Response Rate (%)',
        default=0.0
    )

    @api.depends('last_order_date')
    def _compute_days_since_last_order(self):
        for profile in self:
            if profile.last_order_date:
                delta = datetime.now() - profile.last_order_date
                profile.days_since_last_order = delta.days
            else:
                profile.days_since_last_order = 0

    def update_statistics(self):
        """Update customer statistics from orders"""
        for profile in self:
            orders = self.env['shipping.order'].search([
                ('customer_id', '=', profile.customer_id.id)
            ])

            profile.total_orders = len(orders)
            profile.delivered_orders = len(orders.filtered(lambda o: o.state == 'delivered'))
            profile.cancelled_orders = len(orders.filtered(lambda o: o.state == 'cancelled'))
            profile.returned_orders = len(orders.filtered(lambda o: o.state == 'returned'))

            # Financial stats
            delivered = orders.filtered(lambda o: o.state in ['delivered', 'in_transit', 'out_for_delivery'])
            profile.total_revenue = sum(delivered.mapped('total_amount'))
            profile.avg_order_value = profile.total_revenue / len(delivered) if delivered else 0

            # Products count
            profile.total_products_shipped = sum(orders.mapped('products_count'))

            # Dates
            if orders:
                profile.first_order_date = min(orders.mapped('order_date'))
                profile.last_order_date = max(orders.mapped('order_date'))

                if profile.first_order_date and profile.last_order_date:
                    delta = profile.last_order_date - profile.first_order_date
                    profile.customer_lifetime_days = delta.days

            # Update customer type
            if profile.total_orders == 0:
                profile.customer_type = 'new'
            elif profile.total_orders >= 10 and profile.total_revenue >= 20000:
                profile.customer_type = 'vip'
            elif profile.total_orders >= 2 and profile.days_since_last_order <= 30:
                profile.customer_type = 'active'
            elif profile.days_since_last_order > 60:
                profile.customer_type = 'cold'
            else:
                profile.customer_type = 'normal'

    # ===== Action Methods =====
    def action_view_orders(self):
        """View customer orders"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Orders'),
            'res_model': 'shipping.order',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.customer_id.id)],
            'context': {'default_customer_id': self.customer_id.id}
        }

    def action_send_marketing_email(self):
        """Send targeted marketing email"""
        return True

    @api.model
    def create(self, vals):
        """Override create to ensure clean data"""
        result = super(CustomerProfile, self).create(vals)
        result.update_statistics()
        return result