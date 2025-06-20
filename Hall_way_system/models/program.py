from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Program(models.Model):
    _name = 'hallway.program'
    _description = 'Educational Program'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'create_date desc'

    # Common Fields
    program_type = fields.Selection([
        ('qualification', 'Qualification'),
        ('training', 'Training')
    ], string='Program Type', required=True, tracking=True)

    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    # Computed display name
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    # Qualification Fields
    program_name = fields.Char(string='Qualification Name', tracking=True)
    awarding_body = fields.Text(string='Awarding Body')
    title_of_qualification = fields.Char(string='Title of Qualification')
    has_subtitle = fields.Boolean(string='Has Subtitle', default=False)
    subtitle = fields.Char(string='Subtitle')

    # Training Fields
    training_name = fields.Char(string='Training Name', tracking=True)

    # Relations
    level_ids = fields.One2many('program.level', 'program_id', string='Levels')

    # Computed Fields
    levels_count = fields.Integer(string='Number of Levels', compute='_compute_levels_info', store=True)
    total_price = fields.Monetary(string='Total Price', compute='_compute_levels_info', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    @api.depends('program_type', 'program_name', 'training_name')
    def _compute_display_name(self):
        for record in self:
            if record.program_type == 'qualification':
                record.display_name = record.program_name or _('New Qualification')
            else:
                record.display_name = record.training_name or _('New Training')

    @api.depends('level_ids', 'level_ids.price')
    def _compute_levels_info(self):
        for record in self:
            record.levels_count = len(record.level_ids)
            record.total_price = sum(record.level_ids.mapped('price'))

    @api.constrains('program_type', 'program_name', 'training_name')
    def _check_required_fields(self):
        for record in self:
            if record.program_type == 'qualification' and not record.program_name:
                raise ValidationError(_('Program Name is required for Qualification type.'))
            elif record.program_type == 'training' and not record.training_name:
                raise ValidationError(_('Training Name is required for Training type.'))

    @api.onchange('has_subtitle')
    def _onchange_has_subtitle(self):
        if not self.has_subtitle:
            self.subtitle = False

    @api.onchange('program_type')
    def _onchange_program_type(self):
        if self.program_type == 'training':
            # Clear qualification fields
            self.program_name = False
            self.awarding_body = False
            self.title_of_qualification = False
            self.has_subtitle = False
            self.subtitle = False
            self.level_ids = [(5, 0, 0)]  # Clear all levels
        else:
            # Clear training fields
            self.training_name = False

    def copy(self, default=None):
        default = dict(default or {})
        if self.program_type == 'qualification':
            default['program_name'] = _("%s (copy)", self.program_name)
        else:
            default['training_name'] = _("%s (copy)", self.training_name)
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