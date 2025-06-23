from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Program(models.Model):
    _name = 'hallway.program'
    _description = 'Educational Program'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'create_date desc'

    # Common Fields
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    # Computed display name
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    # Qualification Fields
    program_name = fields.Char(string='Qualification Name', tracking=True)

    # Changed from Text to Selection
    awarding_body = fields.Selection([
        ('qualifi', 'Qualifi'),
        ('pearson', 'Pearson'),
        ('othm', 'OTHM'),

    ], string='Awarding Body', tracking=True)

    # Field for when 'other' is selected
    awarding_body_other = fields.Char(string='Other Awarding Body')

    title_of_qualification = fields.Char(string='Title of Qualification')
    has_subtitle = fields.Boolean(string='Has Subtitle', default=False)
    subtitle = fields.Char(string='Subtitle')

    # Relations
    level_ids = fields.One2many('program.level', 'program_id', string='Levels')

    # Computed Fields
    levels_count = fields.Integer(string='Number of Levels', compute='_compute_levels_info', store=True)
    total_price = fields.Monetary(string='Total Price', compute='_compute_levels_info', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    @api.depends('program_name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.program_name or _('New Qualification')

    @api.depends('level_ids', 'level_ids.total_price')
    def _compute_levels_info(self):
        for record in self:
            record.levels_count = len(record.level_ids)
            # Now total price comes from sum of level total prices
            record.total_price = sum(record.level_ids.mapped('total_price'))

    @api.constrains('program_name')
    def _check_required_fields(self):
        for record in self:
            if not record.program_name:
                raise ValidationError(_('Program Name is required.'))

    @api.constrains('awarding_body', 'awarding_body_other')
    def _check_awarding_body_other(self):
        for record in self:
            if record.awarding_body == 'other' and not record.awarding_body_other:
                raise ValidationError(_('Please specify the other awarding body.'))

    @api.onchange('has_subtitle')
    def _onchange_has_subtitle(self):
        if not self.has_subtitle:
            self.subtitle = False

    @api.onchange('awarding_body')
    def _onchange_awarding_body(self):
        if self.awarding_body != 'other':
            self.awarding_body_other = False

    def copy(self, default=None):
        default = dict(default or {})
        default['program_name'] = _("%s (copy)", self.program_name)
        return super().copy(default)

    @api.model
    def create(self, vals):
        # Additional validation or defaults can be added here
        return super().create(vals)

    def unlink(self):
        for record in self:
            if record.level_ids:
                raise ValidationError(_('Cannot delete a program that has levels. Please delete the levels first.'))
        return super().unlink()