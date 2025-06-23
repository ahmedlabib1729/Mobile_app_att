from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProgramUnit(models.Model):
    _name = 'program.unit'
    _description = 'Program Unit'
    _order = 'level_id, sequence, code'
    _rec_name = 'display_name'

    code = fields.Char(string='Unit Code', required=True, index=True)
    name = fields.Char(string='Unit Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

    level_id = fields.Many2one('program.level', string='Level', required=True, ondelete='cascade')
    program_id = fields.Many2one('hallway.program', string='Program',
                                 related='level_id.program_id', store=True, readonly=True)

    number_of_sessions = fields.Integer(string='Number of Sessions', required=True, default=1)
    credit_hours = fields.Float(string='Credit Hours', required=True, digits=(6, 2))

    # New price field
    price = fields.Monetary(string='Price', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='program_id.currency_id', store=True)

    description = fields.Text(string='Description')

    # Display
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The unit code must be unique!'),
    ]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}" if record.code and record.name else record.code or record.name or 'New'

    @api.constrains('number_of_sessions')
    def _check_number_of_sessions(self):
        for record in self:
            if record.number_of_sessions <= 0:
                raise ValidationError(_('Number of sessions must be greater than zero.'))

    @api.constrains('credit_hours')
    def _check_credit_hours(self):
        for record in self:
            if record.credit_hours < 0:
                raise ValidationError(_('Credit hours cannot be negative.'))

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price < 0:
                raise ValidationError(_('Price cannot be negative.'))

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if record.code:
                # Remove spaces and check format
                clean_code = record.code.strip()
                if not clean_code:
                    raise ValidationError(_('Unit code cannot be empty.'))
                if len(clean_code) < 2:
                    raise ValidationError(_('Unit code must be at least 2 characters long.'))
                # Update code to cleaned version
                if record.code != clean_code.upper():
                    record.code = clean_code.upper()

    def copy(self, default=None):
        default = dict(default or {})
        # Generate new unique code
        original_code = self.code
        counter = 1
        while True:
            new_code = f"{original_code}-COPY{counter}"
            if not self.search([('code', '=', new_code)]):
                default['code'] = new_code
                break
            counter += 1
        default['name'] = _("%s (copy)", self.name)
        return super().copy(default)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto uppercase code
            if 'code' in vals and vals['code']:
                vals['code'] = vals['code'].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        # Auto uppercase code
        if 'code' in vals and vals['code']:
            vals['code'] = vals['code'].strip().upper()
        return super().write(vals)