from odoo import models, fields, api, _


class Attendance(models.Model):
    _name = 'hallway.attendance'
    _description = 'Student Attendance'
    _order = 'session_id, student_id'
    _rec_name = 'display_name'

    # Session and Student
    session_id = fields.Many2one('hallway.course.session', string='Session', required=True, ondelete='cascade')
    student_id = fields.Many2one('hallway.student', string='Student', required=True, ondelete='cascade')
    enrollment_id = fields.Many2one('hallway.enrollment', string='Enrollment', required=True, ondelete='cascade')

    # Related fields
    course_id = fields.Many2one(related='session_id.course_id', string='Course', store=True)
    session_date = fields.Date(related='session_id.date', string='Date', store=True)

    # Attendance
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused')
    ], string='Status', required=True, default='absent')

    # Time tracking
    check_in_time = fields.Float(string='Check-in Time')
    check_out_time = fields.Float(string='Check-out Time')

    # Notes
    notes = fields.Text(string='Notes')
    excuse_reason = fields.Text(string='Excuse Reason')

    # Display name
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    # Company
    company_id = fields.Many2one(
        related='course_id.company_id', string="Company", store=True
    )

    _sql_constraints = [
        ('unique_attendance', 'UNIQUE(session_id, student_id)',
         'Attendance record already exists for this student in this session!'),
    ]

    @api.depends('student_id', 'session_id')
    def _compute_display_name(self):
        for record in self:
            if record.student_id and record.session_id:
                record.display_name = f"{record.student_id.full_name} - {record.session_id.name}"
            else:
                record.display_name = "Attendance Record"

    def action_mark_present(self):
        """Mark student as present"""
        self.status = 'present'

    def action_mark_absent(self):
        """Mark student as absent"""
        self.status = 'absent'

    def action_mark_late(self):
        """Mark student as late"""
        self.status = 'late'

    def action_mark_excused(self):
        """Mark student as excused"""
        self.status = 'excused'