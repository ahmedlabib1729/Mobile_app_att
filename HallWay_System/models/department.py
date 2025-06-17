from odoo import models, fields, api, _


class Department(models.Model):
    _name = 'hallway.department'
    _description = 'Educational Department'
    _order = 'name'

    name = fields.Char(string='Department Name', required=True, translate=True)
    name_ar = fields.Char(string='اسم القسم', required=True)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')

    # Relations
    subject_ids = fields.One2many('hallway.subject', 'department_id', string='Subjects')
    subject_count = fields.Integer(string='Subject Count', compute='_compute_subject_count')

    # Pricing
    price = fields.Float(string='Department Price', required=True, default=0.0,
                         help='Default price for all courses in this department')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Company
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    @api.depends('subject_ids')
    def _compute_subject_count(self):
        for record in self:
            record.subject_count = len(record.subject_ids)

    def action_view_subjects(self):
        """View all subjects in this department"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subjects',
            'res_model': 'hallway.subject',
            'view_mode': 'list,form',
            'domain': [('department_id', '=', self.id)],
            'context': {'default_department_id': self.id}
        }