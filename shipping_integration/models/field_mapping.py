# shipping_integration/models/field_mapping.py
from odoo import models, fields, api


class ShippingFieldMapping(models.Model):
    _name = 'shipping.field.mapping'
    _description = 'Shipping Provider Field Mapping'
    _order = 'sequence, id'

    provider_id = fields.Many2one('shipping.provider', string='Provider', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    field_key = fields.Char(string='Field Key', required=True)
    field_name = fields.Char(string='Field Name', required=True)
    field_type = fields.Selection([
        ('string', 'Text'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        ('datetime', 'DateTime')
    ], string='Field Type', default='string')

    # Odoo field configuration
    odoo_model = fields.Selection([
        ('sale.order', 'Sale Order'),
        ('res.partner', 'Partner'),
        ('res.company', 'Company'),
        ('stock.picking', 'Delivery Order')
    ], string='Odoo Model', default='sale.order')

    odoo_field = fields.Char(string='Odoo Field Path',
                             help='Path to field in Odoo. E.g., partner_id.name or partner_shipping_id.street')

    # Provider field configuration
    provider_field_path = fields.Char(string='Provider Field Path', required=True,
                                      help='Path in provider JSON. E.g., ShipmentConsignee.ConsigneeName')

    # Additional configuration
    is_required = fields.Boolean(string='Required', default=False)
    is_active = fields.Boolean(string='Active', default=True)
    default_value = fields.Char(string='Default Value')
    transformation = fields.Selection([
        ('none', 'None'),
        ('uppercase', 'UPPERCASE'),
        ('lowercase', 'lowercase'),
        ('title', 'Title Case')
    ], string='Transformation', default='none')

    def get_value_from_order(self, order):
        """Get value from order based on field mapping"""
        if not self.odoo_field:
            return self.default_value

        # Handle context values first (from wizard)
        if self.odoo_field.startswith('context.'):
            context_key = self.odoo_field.replace('context.', '')
            return order._context.get(context_key, self.default_value)

        # Start with the order
        value = order

        # Navigate through the field path
        for field in self.odoo_field.split('.'):
            if hasattr(value, field):
                value = getattr(value, field)
            else:
                return self.default_value

        # Apply transformation
        if value and self.transformation != 'none' and isinstance(value, str):
            if self.transformation == 'uppercase':
                value = value.upper()
            elif self.transformation == 'lowercase':
                value = value.lower()
            elif self.transformation == 'title':
                value = value.title()

        # Convert based on field type
        if self.field_type == 'integer' and value:
            try:
                value = int(value)
            except:
                pass
        elif self.field_type == 'float' and value:
            try:
                value = float(value)
            except:
                pass

        return value or self.default_value