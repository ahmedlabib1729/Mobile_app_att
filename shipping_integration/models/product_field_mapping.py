# shipping_integration/models/product_field_mapping.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductFieldMapping(models.Model):
    _name = 'shipping.product.field.mapping'
    _description = 'Product Field Mapping for Shipping Providers'
    _order = 'sequence, id'

    provider_id = fields.Many2one('shipping.provider', string='Provider', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    # Mapping configuration
    placeholder_name = fields.Char(
        string='Placeholder Name',
        required=True,
        help='Placeholder in template (e.g., sku, quantity, weight)'
    )

    source_type = fields.Selection([
        ('field', 'Odoo Field'),
        ('fixed', 'Fixed Value'),
        ('python', 'Python Expression')
    ], string='Source Type', default='field', required=True)

    # Field source
    odoo_field_path = fields.Char(
        string='Odoo Field Path',
        help='Path to field (e.g., product_id.default_code, product_uom_qty)'
    )

    # Fixed value
    fixed_value = fields.Char(string='Fixed Value')

    # Python expression
    python_expression = fields.Text(
        string='Python Expression',
        help='Python expression. Available variables: line, product, order'
    )

    # Data type and transformation
    data_type = fields.Selection([
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean')
    ], string='Data Type', default='string')

    transformation = fields.Selection([
        ('none', 'None'),
        ('uppercase', 'UPPERCASE'),
        ('lowercase', 'lowercase'),
        ('round', 'Round Number')
    ], string='Transformation', default='none')

    # Default value
    default_value = fields.Char(string='Default Value')
    is_required = fields.Boolean(string='Required', default=False)

    @api.constrains('placeholder_name', 'provider_id')
    def _check_unique_placeholder(self):
        for record in self:
            domain = [
                ('placeholder_name', '=', record.placeholder_name),
                ('provider_id', '=', record.provider_id.id),
                ('id', '!=', record.id)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(f'Placeholder "{record.placeholder_name}" already exists for this provider!')

    def get_value_from_line(self, order_line):
        """Get value from order line based on mapping configuration"""
        self.ensure_one()

        value = None

        try:
            if self.source_type == 'fixed':
                value = self.fixed_value

            elif self.source_type == 'field':
                if self.odoo_field_path:
                    # Navigate through the field path
                    obj = order_line
                    for field in self.odoo_field_path.split('.'):
                        if hasattr(obj, field):
                            obj = getattr(obj, field)
                        else:
                            obj = None
                            break
                    value = obj

            elif self.source_type == 'python':
                if self.python_expression:
                    try:
                        # Safe evaluation context
                        eval_context = {
                            'line': order_line,
                            'product': order_line.product_id,
                            'order': order_line.order_id,
                            'round': round,
                            'int': int,
                            'float': float,
                            'str': str
                        }
                        value = eval(self.python_expression, eval_context)
                    except Exception as e:
                        _logger.error(f"Error evaluating expression: {e}")
                        value = None

            # Apply default if no value
            if value is None or value == '':
                value = self.default_value

            # Type conversion - تحويل إلى النوع الصحيح
            if value is not None:
                try:
                    if self.data_type == 'integer':
                        # تحويل إلى integer
                        if isinstance(value, str):
                            value = int(float(value))
                        else:
                            value = int(value)
                    elif self.data_type == 'float':
                        # تحويل إلى float
                        value = float(value)
                    elif self.data_type == 'boolean':
                        # تحويل إلى boolean
                        value = bool(value)
                    elif self.data_type == 'string':
                        # تحويل إلى string
                        value = str(value)
                except Exception as e:
                    _logger.error(f"Error converting value {value} to {self.data_type}: {e}")
                    # استخدام القيمة الافتراضية في حالة فشل التحويل
                    if self.default_value:
                        try:
                            if self.data_type == 'integer':
                                value = int(self.default_value)
                            elif self.data_type == 'float':
                                value = float(self.default_value)
                            elif self.data_type == 'boolean':
                                value = bool(self.default_value)
                            else:
                                value = str(self.default_value)
                        except:
                            value = self.default_value

            # Apply transformation
            if value and self.transformation != 'none':
                if self.transformation == 'uppercase' and isinstance(value, str):
                    value = value.upper()
                elif self.transformation == 'lowercase' and isinstance(value, str):
                    value = value.lower()
                elif self.transformation == 'round' and isinstance(value, (int, float)):
                    value = round(value)

        except Exception as e:
            _logger.error(f"Error getting value for placeholder {self.placeholder_name}: {str(e)}")
            value = self.default_value

        return value