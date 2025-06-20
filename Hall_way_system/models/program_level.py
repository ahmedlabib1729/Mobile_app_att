from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProgramLevel(models.Model):
    _name = 'program.level'
    _description = 'Program Level'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Level Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    program_id = fields.Many2one('hallway.program', string='Program', required=True, ondelete='cascade')

    # Pricing
    price = fields.Monetary(string='Price', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='program_id.currency_id', store=True)

    # Relations
    unit_ids = fields.One2many('program.unit', 'level_id', string='Units')

    # Computed Fields
    units_count = fields.Integer(string='Number of Units', compute='_compute_units_info', store=True)
    total_sessions = fields.Integer(string='Total Sessions', compute='_compute_units_info', store=True)
    total_credit_hours = fields.Float(string='Total Credit Hours', compute='_compute_units_info', store=True)

    # For display
    display_info = fields.Char(string='Info', compute='_compute_display_info')
    color = fields.Integer(string='Color Index', default=0)

    active = fields.Boolean(string='Active', default=True)

    @api.depends('unit_ids', 'unit_ids.number_of_sessions', 'unit_ids.credit_hours')
    def _compute_units_info(self):
        for record in self:
            record.units_count = len(record.unit_ids)
            record.total_sessions = sum(record.unit_ids.mapped('number_of_sessions'))
            record.total_credit_hours = sum(record.unit_ids.mapped('credit_hours'))

    @api.depends('units_count', 'price', 'currency_id')
    def _compute_display_info(self):
        for record in self:
            currency_symbol = record.currency_id.symbol or ''
            record.display_info = f"{record.units_count} Units - {currency_symbol}{record.price:,.2f}"

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price < 0:
                raise ValidationError(_('Price cannot be negative.'))

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _("%s (copy)", self.name)
        # Copy with units
        new_level = super().copy(default)
        for unit in self.unit_ids:
            unit.copy({'level_id': new_level.id})
        return new_level

    @api.model
    def create(self, vals):
        # Set sequence based on existing levels
        if 'sequence' not in vals and 'program_id' in vals:
            last_level = self.search([('program_id', '=', vals['program_id'])],
                                     order='sequence desc', limit=1)
            vals['sequence'] = last_level.sequence + 10 if last_level else 10

        # Set color automatically
        if 'color' not in vals:
            # Use different colors for different levels (1-10)
            existing_count = self.search_count([('program_id', '=', vals.get('program_id', False))])
            vals['color'] = (existing_count % 10) + 1

        return super().create(vals)

    def action_view_units(self):
        self.ensure_one()
        return {
            'name': _('Units for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'program.unit',
            'view_mode': 'list,form',
            'domain': [('level_id', '=', self.id)],
            'context': {
                'default_level_id': self.id,
                'default_program_id': self.program_id.id,
            }
        }