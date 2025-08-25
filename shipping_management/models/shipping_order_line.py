# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShippingProductTemplate(models.Model):
    """Saved product templates for quick reuse"""
    _name = 'shipping.product.template'
    _description = 'Shipping Product Template'
    _order = 'use_count desc, product_name'

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        index=True
    )

    product_name = fields.Char(
        string='Product Name',
        required=True
    )

    category_id = fields.Many2one(
        'product.category',
        string='Main Category',
        required=True
    )

    subcategory_id = fields.Many2one(
        'product.category',
        string='Subcategory'
    )

    brand = fields.Char(
        string='Brand'
    )

    model_number = fields.Char(
        string='Model/Reference'
    )

    default_price = fields.Float(
        string='Default Price'
    )

    weight = fields.Float(
        string='Weight (kg)'
    )

    description = fields.Text(
        string='Description'
    )

    use_count = fields.Integer(
        string='Times Used',
        default=0
    )

    last_used = fields.Datetime(
        string='Last Used'
    )

    def name_get(self):
        result = []
        for template in self:
            name = template.product_name
            if template.brand:
                name = f"{template.brand} - {name}"
            result.append((template.id, name))
        return result


class ShippingOrderLine(models.Model):
    _name = 'shipping.order.line'
    _description = 'Shipping Order Line'
    _order = 'order_id, sequence'

    order_id = fields.Many2one(
        'shipping.order',
        string='Shipping Order',
        required=True,
        ondelete='cascade',
        index=True
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    # ===== Product Information =====
    product_name = fields.Char(
        string='Product Name',
        required=True
    )

    category_id = fields.Many2one(
        'product.category',
        string='Main Category',
        required=True
    )

    subcategory_id = fields.Many2one(
        'product.category',
        string='Subcategory',
        domain="[('parent_id', '=', category_id)]"
    )

    brand = fields.Char(
        string='Brand'
    )

    model_number = fields.Char(
        string='Model/Reference Number'
    )

    # ===== Quantity & Pricing =====
    quantity = fields.Integer(
        string='Quantity',
        required=True,
        default=1
    )

    unit_price = fields.Float(
        string='Unit Price',
        required=True
    )

    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True
    )

    # ===== Physical Attributes =====
    weight = fields.Float(
        string='Weight (kg)',
        help='Total weight for all quantity'
    )

    length = fields.Float(
        string='Length (cm)'
    )

    width = fields.Float(
        string='Width (cm)'
    )

    height = fields.Float(
        string='Height (cm)'
    )

    # ===== Additional Information =====
    description = fields.Text(
        string='Description'
    )

    is_fragile = fields.Boolean(
        string='Fragile Item'
    )

    requires_battery = fields.Boolean(
        string='Contains Battery'
    )

    # ===== Saved Product Template =====
    save_as_template = fields.Boolean(
        string='Save for Future Use'
    )

    product_template_id = fields.Many2one(
        'shipping.product.template',
        string='Product Template',
        help='Select from saved products'
    )

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.onchange('category_id')
    def _onchange_category_id(self):
        """Clear subcategory when main category changes"""
        self.subcategory_id = False

        # Set default weight based on category
        category_weights = {
            'Electronics': 0.5,
            'Clothing': 0.2,
            'Books': 0.3,
            'Food': 1.0,
            'Furniture': 10.0,
        }

        if self.category_id:
            self.weight = category_weights.get(self.category_id.name, 0.5)

    @api.onchange('product_template_id')
    def _onchange_product_template(self):
        """Load product details from template"""
        if self.product_template_id:
            template = self.product_template_id
            self.product_name = template.product_name
            self.category_id = template.category_id
            self.subcategory_id = template.subcategory_id
            self.brand = template.brand
            self.model_number = template.model_number
            self.unit_price = template.default_price
            self.weight = template.weight
            self.description = template.description

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))

    @api.constrains('unit_price')
    def _check_unit_price(self):
        for line in self:
            if line.unit_price < 0:
                raise ValidationError(_('Unit price cannot be negative.'))

    @api.model
    def create(self, vals):
        result = super(ShippingOrderLine, self).create(vals)

        # Save as template if requested
        if result.save_as_template:
            result._create_product_template()

        return result

    def _create_product_template(self):
        """Create a product template for future use"""
        for line in self:
            existing = self.env['shipping.product.template'].search([
                ('product_name', '=', line.product_name),
                ('customer_id', '=', line.order_id.customer_id.id)
            ], limit=1)

            if not existing:
                self.env['shipping.product.template'].create({
                    'customer_id': line.order_id.customer_id.id,
                    'product_name': line.product_name,
                    'category_id': line.category_id.id,
                    'subcategory_id': line.subcategory_id.id if line.subcategory_id else False,
                    'brand': line.brand,
                    'model_number': line.model_number,
                    'default_price': line.unit_price,
                    'weight': line.weight,
                    'description': line.description,
                })