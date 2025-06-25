# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class HrAnnouncement(models.Model):
    _name = 'hr.announcement'
    _description = 'Employee Announcements'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'is_pinned desc, priority desc, create_date desc'

    # Main fields
    name = fields.Char(
        string='Announcement Title',
        required=True,
        tracking=True,
        help="A clear and concise title for the announcement"
    )

    content = fields.Html(
        string='Announcement Content',
        required=True,
        sanitize_style=True,
        help="Detailed content of the announcement"
    )

    summary = fields.Text(
        string='Summary',
        help="A short summary to be shown in the announcement list"
    )

    # Category and type
    announcement_type = fields.Selection([
        ('general', 'General'),
        ('department', 'By Department'),
        ('job', 'By Job'),
        ('personal', 'Personal'),
        ('urgent', 'Urgent'),
    ], string='Announcement Type', default='general', required=True, tracking=True)

    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Very Urgent'),
    ], string='Priority', default='normal', tracking=True)

    # Dates
    start_date = fields.Datetime(
        string='Start Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
        help="Date and time when the announcement starts being shown"
    )

    end_date = fields.Datetime(
        string='End Date',
        tracking=True,
        help="Date and time when the announcement ends (optional)"
    )

    # Targeting
    department_ids = fields.Many2many(
        'hr.department',
        string='Target Departments',
        help="Leave empty to target all departments"
    )

    job_ids = fields.Many2many(
        'hr.job',
        string='Target Jobs',
        help="Leave empty to target all jobs"
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Specific Employees',
        help="Select specific employees to receive the announcement"
    )

    # Display options
    is_pinned = fields.Boolean(
        string='Pin Announcement',
        default=False,
        tracking=True,
        help="Pinned announcements are shown at the top of the list"
    )

    show_in_mobile = fields.Boolean(
        string='Show in Mobile App',
        default=True,
        help="Display this announcement in the mobile app"
    )

    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
        help="Add attached files or images"
    )

    # Publishing info
    author_id = fields.Many2one(
        'res.users',
        string='Author',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('scheduled', 'Scheduled'),
        ('expired', 'Expired'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)

    # Stats
    read_count = fields.Integer(
        string='Read Count',
        compute='_compute_read_count',
        store=True
    )

    read_employee_ids = fields.Many2many(
        'hr.employee',
        'hr_announcement_read_rel',
        'announcement_id',
        'employee_id',
        string='Employees who read the announcement'
    )

    # Computed fields
    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_is_expired',
        store=True
    )

    target_employee_count = fields.Integer(
        string='Targeted Employees Count',
        compute='_compute_target_employee_count',
        store=True
    )

    read_percentage = fields.Float(
        string='Read Percentage',
        compute='_compute_read_percentage',
        store=True
    )

    @api.depends('read_employee_ids')
    def _compute_read_count(self):
        for record in self:
            record.read_count = len(record.read_employee_ids)

    @api.depends('end_date')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            if record.end_date:
                record.is_expired = record.end_date < now
            else:
                record.is_expired = False

    @api.depends('announcement_type', 'department_ids', 'job_ids', 'employee_ids')
    def _compute_target_employee_count(self):
        for record in self:
            if record.announcement_type == 'personal':
                record.target_employee_count = len(record.employee_ids)
            elif record.announcement_type == 'department':
                employees = self.env['hr.employee'].search([
                    ('department_id', 'in', record.department_ids.ids)
                ])
                record.target_employee_count = len(employees)
            elif record.announcement_type == 'job':
                employees = self.env['hr.employee'].search([
                    ('job_id', 'in', record.job_ids.ids)
                ])
                record.target_employee_count = len(employees)
            else:  # general or urgent
                record.target_employee_count = self.env['hr.employee'].search_count([])

    @api.depends('read_count', 'target_employee_count')
    def _compute_read_percentage(self):
        for record in self:
            if record.target_employee_count > 0:
                record.read_percentage = (record.read_count / record.target_employee_count) * 100
            else:
                record.read_percentage = 0

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date > record.end_date:
                raise ValidationError(_('Start date must be before the end date.'))

    def action_publish(self):
        """Publish announcement"""
        self.ensure_one()
        if not self.content:
            raise ValidationError(_('You must add content to the announcement before publishing.'))

        now = fields.Datetime.now()
        if self.start_date > now:
            self.state = 'scheduled'
        else:
            self.state = 'published'

        # Send notification to targeted employees
        self._send_notification_to_employees()

    def action_draft(self):
        """Return to Draft"""
        self.state = 'draft'

    def action_archive(self):
        """Archive announcement"""
        self.state = 'archived'

    def action_mark_as_read(self, employee_id=None):
        """Mark announcement as read"""
        if not employee_id:
            employee = self.env.user.employee_id
        else:
            employee = self.env['hr.employee'].browse(employee_id)

        if employee and employee not in self.read_employee_ids:
            self.read_employee_ids = [(4, employee.id)]
            _logger.info(f"Employee {employee.name} has read announcement {self.name}")

    def _send_notification_to_employees(self):
        """Send notification to targeted employees"""
        employees = self._get_target_employees()
        # Here you can add logic to send notifications
        # such as email or internal notifications
        _logger.info(f"Notification for announcement {self.name} sent to {len(employees)} employees")

    def _get_target_employees(self):
        """Get list of targeted employees"""
        if self.announcement_type == 'personal':
            return self.employee_ids
        elif self.announcement_type == 'department':
            return self.env['hr.employee'].search([
                ('department_id', 'in', self.department_ids.ids)
            ])
        elif self.announcement_type == 'job':
            return self.env['hr.employee'].search([
                ('job_id', 'in', self.job_ids.ids)
            ])
        else:  # general or urgent
            return self.env['hr.employee'].search([])

    @api.model
    def check_scheduled_announcements(self):
        """Cron job to check scheduled announcements"""
        now = fields.Datetime.now()

        # Publish scheduled announcements
        scheduled = self.search([
            ('state', '=', 'scheduled'),
            ('start_date', '<=', now)
        ])
        scheduled.write({'state': 'published'})

        # Expire finished announcements
        expired = self.search([
            ('state', '=', 'published'),
            ('end_date', '<', now),
            ('end_date', '!=', False)
        ])
        expired.write({'state': 'expired'})

    def get_announcement_preview(self):
        """Show announcement preview"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web#id={self.id}&model=hr.announcement&view_type=form',
            'target': 'new',
        }


class HrAnnouncementRead(models.Model):
    _name = 'hr.announcement.read'
    _description = 'Announcement Read Log'
    _rec_name = 'announcement_id'

    announcement_id = fields.Many2one(
        'hr.announcement',
        string='Announcement',
        required=True,
        ondelete='cascade'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade'
    )

    read_date = fields.Datetime(
        string='Read Date',
        default=fields.Datetime.now,
        required=True
    )

    _sql_constraints = [
        ('unique_read', 'UNIQUE(announcement_id, employee_id)',
         'The employee has already read this announcement!')
    ]