from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApplicationProgram(models.Model):
    _name = 'application.program'
    _description = 'Application Program Selection'
    _rec_name = 'display_name'
    _order = 'application_id, sequence'

    # Relations
    application_id = fields.Many2one('student.application', string='Application', required=True, ondelete='cascade')
    program_id = fields.Many2one('hallway.program', string='Program', required=True,
                                 domain=[('active', '=', True)])

    # Program Details (stored for historical reference)
    program_name = fields.Char(related='program_id.program_name', string='Program Name', store=True)
    awarding_body = fields.Selection(related='program_id.awarding_body', string='Awarding Body', store=True)
    title_of_qualification = fields.Char(related='program_id.title_of_qualification', string='Title of Qualification',
                                         store=True)

    # Level Selection
    level_ids = fields.Many2many('program.level', string='Selected Levels',
                                 domain="[('program_id', '=', program_id)]")

    # Computed Fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    total_price = fields.Monetary(string='Total Price', compute='_compute_total_price', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='program_id.currency_id', store=True)
    selected_units_count = fields.Integer(string='Total Units', compute='_compute_units_info', store=True)

    # For ordering
    sequence = fields.Integer(string='Sequence', default=10)

    # Status
    is_primary = fields.Boolean(string='Primary Program', default=False)

    @api.depends('program_id', 'level_ids')
    def _compute_display_name(self):
        for record in self:
            if record.program_id and record.level_ids:
                levels = ', '.join(record.level_ids.mapped('name'))
                record.display_name = f"{record.program_name} - {levels}"
            elif record.program_id:
                record.display_name = record.program_name
            else:
                record.display_name = _('New')

    @api.depends('level_ids', 'level_ids.total_price')
    def _compute_total_price(self):
        for record in self:
            # Now price comes from level's total_price which is sum of unit prices
            record.total_price = sum(record.level_ids.mapped('total_price'))

    @api.depends('level_ids', 'level_ids.unit_ids')
    def _compute_units_info(self):
        for record in self:
            units = record.level_ids.mapped('unit_ids')
            record.selected_units_count = len(units)

    @api.constrains('application_id', 'program_id')
    def _check_unique_program(self):
        for record in self:
            duplicate = self.search([
                ('application_id', '=', record.application_id.id),
                ('program_id', '=', record.program_id.id),
                ('id', '!=', record.id)
            ])
            if duplicate:
                raise ValidationError(_('This program is already selected for this application.'))

    @api.constrains('is_primary')
    def _check_single_primary(self):
        for record in self:
            if record.is_primary:
                other_primary = self.search([
                    ('application_id', '=', record.application_id.id),
                    ('is_primary', '=', True),
                    ('id', '!=', record.id)
                ])
                if other_primary:
                    raise ValidationError(_('Only one program can be marked as primary.'))

    @api.onchange('program_id')
    def _onchange_program_id(self):
        if self.program_id:
            # Clear previously selected levels
            self.level_ids = [(5, 0, 0)]
            # You can set default levels here if needed
            # For example, select all levels by default:
            # self.level_ids = [(6, 0, self.program_id.level_ids.ids)]

    def get_formatted_selection(self):
        """Return formatted string for display in application form"""
        self.ensure_one()
        result = []

        result.append(f"Program: {self.program_name}")
        if self.title_of_qualification:
            result.append(f"Qualification: {self.title_of_qualification}")

        for level in self.level_ids.sorted('sequence'):
            level_info = f"• {level.name} - {level.currency_id.symbol}{level.total_price:,.2f}"
            if level.unit_ids:
                units = ', '.join(level.unit_ids.mapped('code'))
                level_info += f" (Units: {units})"
            result.append(level_info)

        result.append(f"Total: {self.currency_id.symbol}{self.total_price:,.2f}")

        return '\n'.join(result)