from odoo import models, fields, api, _


class Subject(models.Model):
    _name = 'hallway.subject'
    _description = 'Educational Subject'
    _order = 'department_id, sequence, name'

    name = fields.Char(string='Subject Name', required=True, translate=True)
    name_ar = fields.Char(string='اسم المادة', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')

    # Department
    department_id = fields.Many2one('hallway.department', string='Department', required=True, ondelete='cascade')

    # Levels
    has_levels = fields.Boolean(string='Has Levels', default=True)
    level_ids = fields.One2many('hallway.subject.level', 'subject_id', string='Levels')
    level_count = fields.Integer(string='Level Count', compute='_compute_level_count')

    # Courses
    course_ids = fields.One2many('hallway.course', 'subject_id', string='Courses')
    course_count = fields.Integer(string='Course Count', compute='_compute_course_count')

    # Additional Info
    duration_per_level = fields.Integer(string='Duration per Level (Hours)', default=30)
    max_students_per_class = fields.Integer(string='Max Students per Class', default=20)

    # Company
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, company_id)', 'Subject code must be unique per company!'),
    ]

    @api.depends('level_ids')
    def _compute_level_count(self):
        for record in self:
            record.level_count = len(record.level_ids)

    @api.depends('course_ids')
    def _compute_course_count(self):
        for record in self:
            record.course_count = len(record.course_ids)

    def action_view_levels(self):
        """View all levels for this subject"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Levels',
            'res_model': 'hallway.subject.level',
            'view_mode': 'list,form',
            'domain': [('subject_id', '=', self.id)],
            'context': {'default_subject_id': self.id}
        }

    def action_view_courses(self):
        """View all courses for this subject"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Courses',
            'res_model': 'hallway.course',
            'view_mode': 'list,form',
            'domain': [('subject_id', '=', self.id)],
            'context': {'default_subject_id': self.id}
        }