from odoo import models, fields, api, _


class SubjectLevel(models.Model):
    _name = 'hallway.subject.level'
    _description = 'Subject Level'
    _order = 'subject_id, name'

    name = fields.Char(string='Level Name', required=True, translate=True)
    name_ar = fields.Char(string='اسم المستوى', required=True)
    active = fields.Boolean(string='Active', default=True)

    # Subject
    subject_id = fields.Many2one('hallway.subject', string='Subject', required=True, ondelete='cascade')
    department_id = fields.Many2one(related='subject_id.department_id', string='Department', store=True)

    description = fields.Text(string='Description')
    objectives = fields.Text(string='Learning Objectives')

    # Materials
    materials_included = fields.Text(string='Materials Included')

    # Courses
    course_ids = fields.One2many('hallway.course', 'level_id', string='Courses')
    course_count = fields.Integer(string='Course Count', compute='_compute_course_count')

    # Company
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

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