# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ===== Customer Classification =====
    is_shipping_customer = fields.Boolean(
        string='Shipping Customer',
        default=False
    )

    customer_type = fields.Selection([
        ('vip', 'VIP Customer'),
        ('active', 'Active Customer'),
        ('normal', 'Normal Customer'),
        ('cold', 'Cold Customer'),
        ('new', 'New Customer')
    ], string='Customer Type', default='new')

    customer_profile_id = fields.Many2one(
        'customer.profile',
        string='Customer Profile'
    )

    # ===== Shipping Statistics =====
    shipping_order_count = fields.Integer(
        string='Shipping Orders',
        compute='_compute_shipping_statistics'
    )

    total_shipping_revenue = fields.Float(
        string='Total Shipping Revenue',
        compute='_compute_shipping_statistics'
    )

    last_shipping_date = fields.Date(
        string='Last Shipping Date',
        compute='_compute_shipping_statistics'
    )

    # ===== Loyalty =====
    loyalty_points = fields.Integer(
        string='Loyalty Points',
        default=0
    )

    loyalty_tier = fields.Selection([
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum')
    ], string='Loyalty Tier', default='bronze')

    # ===== Credit & Payment =====
    credit_limit = fields.Float(
        string='Credit Limit',
        default=0.0
    )

    current_credit = fields.Float(
        string='Current Credit',
        compute='_compute_credit'
    )

    available_credit = fields.Float(
        string='Available Credit',
        compute='_compute_credit'
    )

    default_payment_method = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('cod', 'Cash on Delivery'),
        ('credit', 'Credit Account')
    ], string='Default Payment Method', default='prepaid')

    # ===== Shipping Preferences =====
    default_shipping_type = fields.Selection([
        ('normal', 'Normal'),
        ('express', 'Express'),
        ('same_day', 'Same Day')
    ], string='Default Shipping Type', default='normal')

    default_shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Default Shipping Company'
    )

    # ===== Marketing Preferences =====
    email_subscribed = fields.Boolean(
        string='Email Marketing',
        default=True
    )

    sms_subscribed = fields.Boolean(
        string='SMS Marketing',
        default=True
    )

    whatsapp_subscribed = fields.Boolean(
        string='WhatsApp Marketing',
        default=True
    )

    # ===== Saved Addresses =====
    shipping_address_ids = fields.One2many(
        'shipping.address',
        'partner_id',
        string='Saved Shipping Addresses'
    )

    # ===== Referral =====
    referral_code = fields.Char(
        string='Referral Code',
        compute='_compute_referral_code',
        store=True
    )

    referred_by_id = fields.Many2one(
        'res.partner',
        string='Referred By'
    )

    referral_count = fields.Integer(
        string='Referrals Made',
        compute='_compute_referral_count'
    )

    def _compute_shipping_statistics(self):
        for partner in self:
            orders = self.env['shipping.order'].search([
                ('customer_id', '=', partner.id)
            ])

            partner.shipping_order_count = len(orders)

            delivered = orders.filtered(lambda o: o.state in ['delivered', 'in_transit'])
            partner.total_shipping_revenue = sum(delivered.mapped('total_amount'))

            if orders:
                latest = max(orders.mapped('order_date'))
                partner.last_shipping_date = latest.date() if latest else False
            else:
                partner.last_shipping_date = False

    def _compute_credit(self):
        for partner in self:
            # Calculate current credit usage
            unpaid_orders = self.env['shipping.order'].search([
                ('customer_id', '=', partner.id),
                ('payment_method', '=', 'credit'),
                ('state', 'in', ['confirmed', 'picked', 'in_transit', 'delivered']),
            ])

            partner.current_credit = sum(unpaid_orders.mapped('total_amount'))
            partner.available_credit = partner.credit_limit - partner.current_credit

    @api.depends('name')
    def _compute_referral_code(self):
        for partner in self:
            if partner.name:
                # Generate unique referral code
                code = ''.join(filter(str.isalnum, partner.name.upper()))[:5]
                partner.referral_code = f"{code}{partner.id or 0}"
            else:
                partner.referral_code = False

    def _compute_referral_count(self):
        for partner in self:
            referred = self.search_count([
                ('referred_by_id', '=', partner.id)
            ])
            partner.referral_count = referred

    def action_view_shipping_orders(self):
        """View all shipping orders for this customer"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipping Orders'),
            'res_model': 'shipping.order',
            'view_mode': 'list,form,graph',
            'domain': [('customer_id', '=', self.id)],
            'context': {
                'default_customer_id': self.id,
                'default_sender_name': self.name,
                'default_sender_phone': self.phone or self.mobile,
                'default_sender_email': self.email,
            }
        }

    def action_create_shipping_order(self):
        """Create new shipping order for this customer"""
        self.ensure_one()

        # Set customer as shipping customer
        if not self.is_shipping_customer:
            self.is_shipping_customer = True
            # Create profile if doesn't exist
            if not self.customer_profile_id:
                profile = self.env['customer.profile'].search([
                    ('customer_id', '=', self.id)
                ], limit=1)

                if not profile:
                    profile = self.env['customer.profile'].create({
                        'customer_id': self.id
                    })

                self.customer_profile_id = profile

        return {
            'type': 'ir.actions.act_window',
            'name': _('New Shipping Order'),
            'res_model': 'shipping.order',
            'view_mode': 'form',
            'context': {
                'default_customer_id': self.id,
                'default_sender_name': self.name,
                'default_sender_phone': self.phone or self.mobile,
                'default_sender_email': self.email,
                'default_payment_method': self.default_payment_method,
                'default_shipping_type': self.default_shipping_type,
                'default_shipping_company_id': self.default_shipping_company_id.id if self.default_shipping_company_id else False,
            }
        }

    def action_view_customer_profile(self):
        """View customer profile analysis"""
        self.ensure_one()

        if not self.customer_profile_id:
            # Create profile if doesn't exist
            self.is_shipping_customer = True
            profile = self.env['customer.profile'].search([
                ('customer_id', '=', self.id)
            ], limit=1)

            if not profile:
                profile = self.env['customer.profile'].create({
                    'customer_id': self.id
                })

            self.customer_profile_id = profile

        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Profile'),
            'res_model': 'customer.profile',
            'view_mode': 'form',
            'res_id': self.customer_profile_id.id,
        }


class ShippingAddress(models.Model):
    """Saved shipping addresses for customers"""
    _name = 'shipping.address'
    _description = 'Shipping Address'
    _order = 'is_default desc, name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string='Address Label',
        required=True,
        help='e.g., Home, Office, etc.'
    )

    contact_name = fields.Char(
        string='Contact Name',
        required=True
    )

    phone = fields.Char(
        string='Phone',
        required=True
    )

    email = fields.Char(
        string='Email'
    )

    governorate_id = fields.Many2one(
        'res.country.state',
        string='Governorate',
        domain="[('country_id.code', '=', 'EG')]",
        required=True
    )

    city = fields.Char(
        string='City',
        required=True
    )

    street = fields.Text(
        string='Street Address',
        required=True
    )

    building_no = fields.Char(
        string='Building No.'
    )

    floor = fields.Char(
        string='Floor'
    )

    apartment = fields.Char(
        string='Apartment'
    )

    landmark = fields.Char(
        string='Landmark',
        help='Nearby landmark for easy location'
    )

    is_default = fields.Boolean(
        string='Default Address'
    )

    address_type = fields.Selection([
        ('sender', 'Sender Address'),
        ('receiver', 'Receiver Address'),
        ('both', 'Both')
    ], string='Address Type', default='both')

    @api.model
    def create(self, vals):
        # Ensure only one default address per partner
        if vals.get('is_default'):
            self.search([
                ('partner_id', '=', vals.get('partner_id')),
                ('is_default', '=', True)
            ]).write({'is_default': False})

        return super(ShippingAddress, self).create(vals)

    def write(self, vals):
        if vals.get('is_default'):
            # Ensure only one default address
            other_addresses = self.search([
                ('partner_id', 'in', self.mapped('partner_id').ids),
                ('id', 'not in', self.ids),
                ('is_default', '=', True)
            ])
            other_addresses.write({'is_default': False})

        return super(ShippingAddress, self).write(vals)

    def name_get(self):
        result = []
        for address in self:
            name = f"{address.name} - {address.city}, {address.governorate_id.name if address.governorate_id else ''}"
            result.append((address.id, name))
        return result