# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LoyaltyTier(models.Model):
    _name = 'loyalty.tier'
    _description = 'Loyalty Tier Configuration'
    _order = 'min_points'

    name = fields.Char(
        string='Tier Name',
        required=True
    )

    min_points = fields.Integer(
        string='Minimum Points',
        required=True,
        help='Minimum points required to reach this tier'
    )

    max_points = fields.Integer(
        string='Maximum Points',
        help='Leave empty for highest tier'
    )

    discount_percentage = fields.Float(
        string='Discount %',
        default=0.0,
        help='Automatic discount percentage for this tier'
    )

    color = fields.Selection([
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond'),
    ], string='Badge Color', default='bronze')

    benefits = fields.Text(
        string='Benefits Description'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.constrains('min_points', 'max_points')
    def _check_points_range(self):
        for tier in self:
            if tier.max_points and tier.max_points <= tier.min_points:
                raise ValidationError(_('Maximum points must be greater than minimum points'))

            # Check for overlapping tiers
            overlapping = self.search([
                ('id', '!=', tier.id),
                ('active', '=', True),
                '|',
                '&', ('min_points', '<=', tier.min_points),
                '|', ('max_points', '>=', tier.min_points), ('max_points', '=', False),
                '&', ('min_points', '<=', tier.max_points if tier.max_points else 999999),
                '|', ('max_points', '>=', tier.max_points if tier.max_points else 999999), ('max_points', '=', False)
            ])

            if overlapping:
                raise ValidationError(_('This tier overlaps with another tier: %s') % overlapping[0].name)


class LoyaltyPointsRule(models.Model):
    _name = 'loyalty.points.rule'
    _description = 'Loyalty Points Rules'
    _order = 'sequence'

    name = fields.Char(
        string='Rule Name',
        required=True
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    rule_type = fields.Selection([
        ('order_amount', 'Per Order Amount'),
        ('product_category', 'Per Product Category'),
        ('shipping_type', 'Per Shipping Type'),
        ('payment_method', 'Per Payment Method'),
        ('first_order', 'First Order Bonus'),
        ('referral', 'Referral Bonus'),
    ], string='Rule Type', required=True)

    # Order Amount Rules
    points_per_currency = fields.Float(
        string='Points per EGP',
        default=1.0,
        help='Points awarded per currency unit spent'
    )

    min_order_amount = fields.Float(
        string='Minimum Order Amount'
    )

    # Category Rules
    category_id = fields.Many2one(
        'product.category',
        string='Product Category'
    )

    category_multiplier = fields.Float(
        string='Points Multiplier',
        default=1.0
    )

    # Shipping Type Rules
    shipping_type = fields.Selection([
        ('normal', 'Normal'),
        ('express', 'Express'),
        ('same_day', 'Same Day')
    ], string='Shipping Type')

    shipping_bonus_points = fields.Integer(
        string='Bonus Points'
    )

    # Payment Method Rules
    payment_method = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('cod', 'Cash on Delivery'),
        ('credit', 'Credit Account')
    ], string='Payment Method')

    payment_bonus_points = fields.Integer(
        string='Payment Bonus Points'
    )

    # Fixed Points
    fixed_points = fields.Integer(
        string='Fixed Points',
        help='Fixed points to award (for first order, referral, etc.)'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    description = fields.Text(
        string='Description'
    )


class CustomerDiscount(models.Model):
    _name = 'customer.discount'
    _description = 'Customer Special Discounts'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='cascade'
    )

    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Discount Type', required=True, default='percentage')

    discount_value = fields.Float(
        string='Discount Value',
        required=True
    )

    valid_from = fields.Date(
        string='Valid From',
        default=fields.Date.today
    )

    valid_to = fields.Date(
        string='Valid To'
    )

    min_order_amount = fields.Float(
        string='Minimum Order Amount',
        default=0.0
    )

    max_discount_amount = fields.Float(
        string='Maximum Discount Amount',
        help='Maximum discount amount for percentage discounts'
    )

    usage_limit = fields.Integer(
        string='Usage Limit',
        help='Leave empty for unlimited usage'
    )

    times_used = fields.Integer(
        string='Times Used',
        default=0,
        readonly=True
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    notes = fields.Text(
        string='Notes'
    )

    @api.constrains('valid_from', 'valid_to')
    def _check_dates(self):
        for discount in self:
            if discount.valid_to and discount.valid_from > discount.valid_to:
                raise ValidationError(_('End date must be after start date'))

    def _is_valid(self):
        """Check if discount is valid for use"""
        self.ensure_one()
        today = fields.Date.today()

        if not self.active:
            return False

        if self.valid_from and today < self.valid_from:
            return False

        if self.valid_to and today > self.valid_to:
            return False

        if self.usage_limit and self.times_used >= self.usage_limit:
            return False

        return True

    def calculate_discount(self, order_amount):
        """Calculate discount amount for given order"""
        self.ensure_one()

        if not self._is_valid():
            return 0.0

        if order_amount < self.min_order_amount:
            return 0.0

        if self.discount_type == 'percentage':
            discount = order_amount * (self.discount_value / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = min(self.discount_value, order_amount)

        return discount


class CustomerProfileInherit(models.Model):
    _inherit = 'customer.profile'

    # Replace the static loyalty_tier field with computed one
    loyalty_tier_id = fields.Many2one(
        'loyalty.tier',
        string='Loyalty Tier',
        compute='_compute_loyalty_tier_dynamic',
        store=True
    )

    loyalty_tier_name = fields.Char(
        string='Tier Name',
        related='loyalty_tier_id.name'
    )

    loyalty_tier_discount = fields.Float(
        string='Tier Discount %',
        related='loyalty_tier_id.discount_percentage'
    )

    customer_discount_ids = fields.One2many(
        'customer.discount',
        related='customer_id.customer_discount_ids',
        string='Special Discounts'
    )

    total_discount_available = fields.Float(
        string='Total Discount %',
        compute='_compute_total_discount'
    )

    points_history_ids = fields.One2many(
        'loyalty.points.history',
        'profile_id',
        string='Points History'
    )

    @api.depends('loyalty_points')
    def _compute_loyalty_tier_dynamic(self):
        for profile in self:
            tier = self.env['loyalty.tier'].search([
                ('active', '=', True),
                ('min_points', '<=', profile.loyalty_points),
                '|',
                ('max_points', '>=', profile.loyalty_points),
                ('max_points', '=', False)
            ], limit=1, order='min_points desc')

            profile.loyalty_tier_id = tier

    def _compute_total_discount(self):
        for profile in self:
            total_discount = profile.loyalty_tier_discount or 0.0

            # Add valid customer discounts
            for discount in profile.customer_discount_ids:
                if discount._is_valid() and discount.discount_type == 'percentage':
                    total_discount += discount.discount_value

            profile.total_discount_available = min(total_discount, 100.0)  # Cap at 100%

    def add_loyalty_points(self, points, reason=''):
        """Add loyalty points with history tracking"""
        self.ensure_one()

        self.env['loyalty.points.history'].create({
            'profile_id': self.id,
            'points': points,
            'transaction_type': 'earn',
            'reason': reason,
            'balance_after': self.loyalty_points + points
        })

        self.loyalty_points += points

        # Check for tier upgrade
        old_tier = self.loyalty_tier_id
        self._compute_loyalty_tier_dynamic()

        if old_tier != self.loyalty_tier_id and self.loyalty_tier_id:
            # Send notification about tier upgrade
            self._notify_tier_upgrade()

    def redeem_loyalty_points(self, points, reason=''):
        """Redeem loyalty points with history tracking"""
        self.ensure_one()

        if points > self.loyalty_points:
            raise ValidationError(_('Insufficient loyalty points'))

        self.env['loyalty.points.history'].create({
            'profile_id': self.id,
            'points': -points,
            'transaction_type': 'redeem',
            'reason': reason,
            'balance_after': self.loyalty_points - points
        })

        self.loyalty_points -= points

    def _notify_tier_upgrade(self):
        """Send notification when tier is upgraded"""
        # Implement notification logic here
        pass


class LoyaltyPointsHistory(models.Model):
    _name = 'loyalty.points.history'
    _description = 'Loyalty Points Transaction History'
    _order = 'date desc'

    profile_id = fields.Many2one(
        'customer.profile',
        string='Customer Profile',
        required=True,
        ondelete='cascade'
    )

    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        required=True
    )

    points = fields.Integer(
        string='Points',
        required=True,
        help='Positive for earned, negative for redeemed'
    )

    transaction_type = fields.Selection([
        ('earn', 'Earned'),
        ('redeem', 'Redeemed'),
        ('expire', 'Expired'),
        ('adjust', 'Manual Adjustment'),
    ], string='Type', required=True)

    reason = fields.Char(
        string='Reason'
    )

    order_id = fields.Many2one(
        'shipping.order',
        string='Related Order'
    )

    balance_after = fields.Integer(
        string='Balance After',
        required=True
    )


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    customer_discount_ids = fields.One2many(
        'customer.discount',
        'partner_id',
        string='Special Discounts'
    )

    has_special_discount = fields.Boolean(
        string='Has Special Discount',
        compute='_compute_has_special_discount'
    )

    @api.depends('customer_discount_ids.active')
    def _compute_has_special_discount(self):
        for partner in self:
            partner.has_special_discount = any(
                discount._is_valid() for discount in partner.customer_discount_ids
            )