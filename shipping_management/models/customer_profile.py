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
    ], string='Customer Type', compute='_compute_customer_type', store=True, tracking=True)

    # ===== Order Statistics =====
    total_orders = fields.Integer(
        string='Total Orders',
        compute='_compute_statistics',
        store=True
    )

    delivered_orders = fields.Integer(
        string='Delivered Orders',
        compute='_compute_statistics',
        store=True
    )

    cancelled_orders = fields.Integer(
        string='Cancelled Orders',
        compute='_compute_statistics',
        store=True
    )

    returned_orders = fields.Integer(
        string='Returned Orders',
        compute='_compute_statistics',
        store=True
    )

    # ===== Financial Statistics =====
    total_revenue = fields.Float(
        string='Total Revenue (EGP)',
        compute='_compute_statistics',
        store=True,
        tracking=True
    )

    avg_order_value = fields.Float(
        string='Average Order Value',
        compute='_compute_statistics',
        store=True
    )

    total_products_shipped = fields.Integer(
        string='Total Products Shipped',
        compute='_compute_statistics',
        store=True
    )

    # ===== Time-based Analysis =====
    first_order_date = fields.Datetime(
        string='First Order Date',
        compute='_compute_statistics',
        store=True
    )

    last_order_date = fields.Datetime(
        string='Last Order Date',
        compute='_compute_statistics',
        store=True,
        tracking=True
    )

    days_since_last_order = fields.Integer(
        string='Days Since Last Order',
        compute='_compute_days_since_last_order'
    )

    customer_lifetime_days = fields.Integer(
        string='Customer Lifetime (Days)',
        compute='_compute_statistics',
        store=True
    )

    # ===== Product Preferences =====
    favorite_product_ids = fields.Many2many(
        'shipping.product.template',
        'customer_favorite_products_rel',
        'profile_id',
        'product_id',
        string='Favorite Products',
        compute='_compute_favorite_products',
        store=True
    )

    preferred_category_ids = fields.Many2many(
        'product.category',
        'customer_preferred_categories_rel',
        'profile_id',
        'category_id',
        string='Preferred Categories',
        compute='_compute_favorite_products',
        store=True
    )

    top_brand = fields.Char(
        string='Top Brand',
        compute='_compute_favorite_products',
        store=True
    )

    # ===== Shipping Preferences =====
    preferred_shipping_type = fields.Selection([
        ('normal', 'Normal'),
        ('express', 'Express'),
        ('same_day', 'Same Day')
    ], string='Preferred Shipping Type', compute='_compute_shipping_preferences', store=True)

    preferred_shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Preferred Shipping Company',
        compute='_compute_shipping_preferences',
        store=True
    )

    preferred_payment_method = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('cod', 'Cash on Delivery'),
        ('credit', 'Credit Account')
    ], string='Preferred Payment Method', compute='_compute_shipping_preferences', store=True)

    # ===== Geographic Analysis =====
    most_common_governorate = fields.Many2one(
        'res.country.state',
        string='Most Common Governorate',
        compute='_compute_geographic_data',
        store=True
    )

    most_common_city = fields.Char(
        string='Most Common City',
        compute='_compute_geographic_data',
        store=True
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
    ], string='Loyalty Tier', compute='_compute_loyalty_tier', store=True)

    referral_count = fields.Integer(
        string='Referrals Made',
        default=0
    )

    # ===== Predictive Analytics =====
    churn_risk = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk')
    ], string='Churn Risk', compute='_compute_churn_risk', store=True)

    predicted_next_order_date = fields.Date(
        string='Predicted Next Order',
        compute='_compute_predictions'
    )

    predicted_next_order_value = fields.Float(
        string='Predicted Order Value',
        compute='_compute_predictions'
    )

    # ===== Customer Lifetime Value =====
    clv = fields.Float(
        string='Customer Lifetime Value',
        compute='_compute_clv',
        store=True,
        help='Predicted total value of customer over their lifetime'
    )

    # ===== Marketing =====
    email_subscribed = fields.Boolean(
        string='Email Subscribed',
        related='customer_id.email_subscribed',
        store=True
    )

    sms_subscribed = fields.Boolean(
        string='SMS Subscribed',
        related='customer_id.sms_subscribed',
        store=True
    )

    last_marketing_campaign_id = fields.Many2one(
        'mail.mass_mailing',
        string='Last Campaign'
    )

    campaign_response_rate = fields.Float(
        string='Campaign Response Rate (%)'
    )

    @api.depends('customer_id')
    def _compute_statistics(self):
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
            else:
                profile.first_order_date = False
                profile.last_order_date = False
                profile.customer_lifetime_days = 0

    @api.depends('last_order_date')
    def _compute_days_since_last_order(self):
        for profile in self:
            if profile.last_order_date:
                delta = datetime.now() - profile.last_order_date
                profile.days_since_last_order = delta.days
            else:
                profile.days_since_last_order = 0

    @api.depends('total_orders', 'total_revenue', 'days_since_last_order')
    def _compute_customer_type(self):
        for profile in self:
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

    @api.depends('customer_id')
    def _compute_favorite_products(self):
        for profile in self:
            if not profile.customer_id:
                profile.favorite_product_ids = [(5, 0, 0)]
                profile.preferred_category_ids = [(5, 0, 0)]
                profile.top_brand = False
                continue

            # Get all order lines for this customer
            order_lines = self.env['shipping.order.line'].search([
                ('order_id.customer_id', '=', profile.customer_id.id),
                ('order_id.state', 'in', ['delivered', 'in_transit'])
            ])

            if order_lines:
                # Find top products
                product_count = {}
                category_count = {}
                brand_count = {}

                for line in order_lines:
                    # Count products
                    key = (line.product_name, line.brand)
                    product_count[key] = product_count.get(key, 0) + line.quantity

                    # Count categories
                    if line.category_id:
                        category_count[line.category_id.id] = category_count.get(line.category_id.id, 0) + 1

                    # Count brands
                    if line.brand:
                        brand_count[line.brand] = brand_count.get(line.brand, 0) + 1

                # Get top 5 products
                top_products = sorted(product_count.items(), key=lambda x: x[1], reverse=True)[:5]

                # Create product templates for favorites
                templates = []
                for (name, brand), count in top_products:
                    template = self.env['shipping.product.template'].search([
                        ('customer_id', '=', profile.customer_id.id),
                        ('product_name', '=', name)
                    ], limit=1)

                    if template:
                        templates.append(template.id)

                profile.favorite_product_ids = [(6, 0, templates)]

                # Set preferred categories (top 3)
                if category_count:
                    top_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:3]
                    profile.preferred_category_ids = [(6, 0, [cat_id for cat_id, _ in top_categories])]
                else:
                    profile.preferred_category_ids = [(5, 0, 0)]

                # Set top brand
                if brand_count:
                    profile.top_brand = max(brand_count.items(), key=lambda x: x[1])[0]
                else:
                    profile.top_brand = False
            else:
                profile.favorite_product_ids = [(5, 0, 0)]
                profile.preferred_category_ids = [(5, 0, 0)]
                profile.top_brand = False

    @api.depends('customer_id')
    def _compute_shipping_preferences(self):
        for profile in self:
            if not profile.customer_id:
                profile.preferred_shipping_type = False
                profile.preferred_shipping_company_id = False
                profile.preferred_payment_method = False
                continue

            orders = self.env['shipping.order'].search([
                ('customer_id', '=', profile.customer_id.id),
                ('state', '!=', 'cancelled')
            ])

            if orders:
                # Preferred shipping type
                shipping_types = {}
                for order in orders:
                    shipping_types[order.shipping_type] = shipping_types.get(order.shipping_type, 0) + 1

                if shipping_types:
                    profile.preferred_shipping_type = max(shipping_types.items(), key=lambda x: x[1])[0]
                else:
                    profile.preferred_shipping_type = False

                # Preferred shipping company
                company_count = {}
                for order in orders:
                    if order.shipping_company_id:
                        company_count[order.shipping_company_id.id] = company_count.get(order.shipping_company_id.id,
                                                                                        0) + 1

                if company_count:
                    company_id = max(company_count.items(), key=lambda x: x[1])[0]
                    profile.preferred_shipping_company_id = company_id
                else:
                    profile.preferred_shipping_company_id = False

                # Preferred payment method
                payment_methods = {}
                for order in orders:
                    payment_methods[order.payment_method] = payment_methods.get(order.payment_method, 0) + 1

                if payment_methods:
                    profile.preferred_payment_method = max(payment_methods.items(), key=lambda x: x[1])[0]
                else:
                    profile.preferred_payment_method = False
            else:
                profile.preferred_shipping_type = False
                profile.preferred_shipping_company_id = False
                profile.preferred_payment_method = False

    @api.depends('customer_id')
    def _compute_geographic_data(self):
        for profile in self:
            if not profile.customer_id:
                profile.most_common_governorate = False
                profile.most_common_city = False
                continue

            orders = self.env['shipping.order'].search([
                ('customer_id', '=', profile.customer_id.id)
            ])

            if orders:
                # Most common governorate
                governorate_count = {}
                city_count = {}

                for order in orders:
                    if order.receiver_governorate:
                        governorate_count[order.receiver_governorate.id] = \
                            governorate_count.get(order.receiver_governorate.id, 0) + 1

                    if order.receiver_city:
                        city_count[order.receiver_city] = city_count.get(order.receiver_city, 0) + 1

                if governorate_count:
                    gov_id = max(governorate_count.items(), key=lambda x: x[1])[0]
                    profile.most_common_governorate = gov_id
                else:
                    profile.most_common_governorate = False

                if city_count:
                    profile.most_common_city = max(city_count.items(), key=lambda x: x[1])[0]
                else:
                    profile.most_common_city = False
            else:
                profile.most_common_governorate = False
                profile.most_common_city = False

    @api.depends('loyalty_points')
    def _compute_loyalty_tier(self):
        for profile in self:
            if profile.loyalty_points >= 5000:
                profile.loyalty_tier = 'platinum'
            elif profile.loyalty_points >= 2000:
                profile.loyalty_tier = 'gold'
            elif profile.loyalty_points >= 500:
                profile.loyalty_tier = 'silver'
            else:
                profile.loyalty_tier = 'bronze'

    @api.depends('days_since_last_order', 'total_orders', 'customer_lifetime_days')
    def _compute_churn_risk(self):
        for profile in self:
            if profile.total_orders == 0:
                profile.churn_risk = 'low'  # New customer
            elif profile.days_since_last_order > 90:
                profile.churn_risk = 'high'
            elif profile.days_since_last_order > 60:
                profile.churn_risk = 'medium'
            else:
                profile.churn_risk = 'low'

    def _compute_predictions(self):
        for profile in self:
            if profile.total_orders >= 3:
                # Simple prediction based on average order frequency
                if profile.customer_lifetime_days and profile.total_orders > 1:
                    avg_days_between_orders = profile.customer_lifetime_days / (profile.total_orders - 1)

                    if profile.last_order_date:
                        next_date = profile.last_order_date + timedelta(days=avg_days_between_orders)
                        profile.predicted_next_order_date = next_date.date()

                    profile.predicted_next_order_value = profile.avg_order_value
                else:
                    profile.predicted_next_order_date = fields.Date.today() + timedelta(days=30)
                    profile.predicted_next_order_value = profile.avg_order_value
            else:
                profile.predicted_next_order_date = False
                profile.predicted_next_order_value = 0

    @api.depends('total_revenue', 'total_orders', 'customer_lifetime_days')
    def _compute_clv(self):
        for profile in self:
            if profile.total_orders > 0:
                # Simple CLV calculation
                # CLV = Average Order Value × Purchase Frequency × Customer Lifespan

                if profile.customer_lifetime_days > 0:
                    # Purchase frequency (orders per year)
                    years = max(profile.customer_lifetime_days / 365, 0.1)
                    frequency = profile.total_orders / years

                    # Estimate remaining lifetime (2 years for active customers)
                    if profile.customer_type in ['vip', 'active']:
                        estimated_lifetime_years = 2
                    else:
                        estimated_lifetime_years = 1

                    profile.clv = profile.avg_order_value * frequency * estimated_lifetime_years
                else:
                    # New customer - estimate based on average
                    profile.clv = profile.avg_order_value * 6  # Assume 6 orders per year
            else:
                profile.clv = 0

    # ===== Action Methods =====
    def action_add_loyalty_points(self, points):
        """Add loyalty points to customer"""
        for profile in self:
            profile.loyalty_points += points

            # Check for tier upgrade
            old_tier = profile.loyalty_tier
            profile._compute_loyalty_tier()

            if old_tier != profile.loyalty_tier:
                # Send notification about tier upgrade
                profile._send_tier_upgrade_notification()

    def action_send_marketing_email(self):
        """Send targeted marketing email"""
        for profile in self:
            template = False

            if profile.customer_type == 'cold':
                template = self.env.ref('shipping_management.email_template_reactivation', False)
            elif profile.customer_type == 'vip':
                template = self.env.ref('shipping_management.email_template_vip_offer', False)

            if template:
                template.send_mail(profile.id, force_send=True)

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

    def _send_tier_upgrade_notification(self):
        """Send notification when customer tier is upgraded"""
        for profile in self:
            # Send email notification
            _logger.info(f"Customer {profile.customer_id.name} upgraded to {profile.loyalty_tier}")

    @api.model
    def cron_update_customer_profiles(self):
        """Cron job to update all customer profiles"""
        profiles = self.search([])
        profiles._compute_statistics()
        profiles._compute_predictions()
        profiles._compute_churn_risk()

        # Send reactivation campaigns to high churn risk customers
        high_risk = profiles.filtered(lambda p: p.churn_risk == 'high')
        high_risk.action_send_marketing_email()