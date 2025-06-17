from odoo import models, fields, api, _


class SubjectLevel(models.Model):
    _name = 'hallway.subject.level'
    _description = 'Subject Level'
    _order = 'subject_id, sequence, name'

    name = fields.Char(string='Level Name', required=True, translate=True)
    name_ar = fields.Char(string='اسم المستوى', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    # Subject
    subject_id = fields.Many2one('hallway.subject', string='Subject', required=True, ondelete='cascade')
    department_id = fields.Many2one(related='subject_id.department_id', string='Department', store=True)

    # Level Details
    level_type = fields.Selection([
        ('beginner', 'Beginner / مبتدئ'),
        ('pre_intermediate', 'Pre-Intermediate / ما قبل المتوسط'),
        ('intermediate', 'Intermediate / متوسط'),
        ('advanced', 'Advanced / متقدم'),
        ('proficient', 'Proficient / محترف'),
        ('other', 'Other / أخرى')
    ], string='Level Type', default='beginner')

    description = fields.Text(string='Description')
    objectives = fields.Text(string='Learning Objectives')
    prerequisites = fields.Text(string='Prerequisites')

    # Duration
    duration_hours = fields.Integer(string='Duration (Hours)', default=30)
    duration_weeks = fields.Integer(string='Duration (Weeks)', default=4)
    sessions_per_week = fields.Integer(string='Sessions per Week', default=3)

    # Materials
    book_name = fields.Char(string='Book Name')
    materials_included = fields.Text(string='Materials Included')

    # Courses
    course_ids = fields.One2many('hallway.course', 'level_id', string='Courses')
    course_count = fields.Integer(string='Course Count', compute='_compute_course_count')

    # Company
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, subject_id)', 'Level code must be unique per subject!'),
    ]

    @api.depends('course_ids')
    def _compute_course_count(self):
        for record in self:
            record.course_count = len(record.course_ids)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.subject_id.name} - {record.name}"
            result.append((record.id, name))
        return result

    def action_view_courses(self):
        """View all courses for this level"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Courses',
            'res_model': 'hallway.course',
            'view_mode': 'list,form',
            'domain': [('level_id', '=', self.id)],
            'context': {
                'default_level_id': self.id,
                'default_subject_id': self.subject_id.id
            }
        }