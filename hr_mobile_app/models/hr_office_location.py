# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrOfficeLocation(models.Model):
    _name = 'hr.office.location'
    _description = 'Company Office Locations'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'sequence, name'

    # الحقول الأساسية
    name = fields.Char(
        string='Location Name',
        required=True,
        tracking=True,
        help="Clear name for the location (e.g.: Main Office, Maadi Branch)"
    )

    code = fields.Char(
        string='Location Code',
        help="Short code for the location (e.g.: HQ, BR1)"
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help="Deactivate instead of delete"
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display order"
    )

    # إحداثيات الموقع
    latitude = fields.Float(
        string='Latitude',
        digits=(10, 6),
        required=True,
        tracking=True,
        help="Latitude for the location"
    )

    longitude = fields.Float(
        string='Longitude',
        digits=(10, 6),
        required=True,
        tracking=True,
        help="Longitude for the location"
    )

    # إعدادات النطاق
    allowed_radius = fields.Integer(
        string='Allowed Radius (m)',
        default=100,
        required=True,
        tracking=True,
        help="Allowed distance from location for attendance check-in in meters"
    )

    # معلومات العنوان
    street = fields.Char(
        string='Street',
        help="Street address"
    )

    street2 = fields.Char(
        string='Street 2',
        help="Additional address"
    )

    city = fields.Char(
        string='City',
        help="City"
    )

    state_id = fields.Many2one(
        'res.country.state',
        string='State',
        help="State or province"
    )

    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env.ref('base.eg'),  # Egypt as default
        help="Country"
    )

    zip = fields.Char(
        string='Zip Code',
        help="Postal code"
    )

    # معلومات إضافية
    description = fields.Text(
        string='Description',
        help="Detailed description of the location"
    )

    location_type = fields.Selection([
        ('main', 'Main Office'),
        ('branch', 'Branch'),
        ('warehouse', 'Warehouse'),
        ('site', 'Work Site'),
        ('client', 'Client Location'),
        ('other', 'Other')
    ], string='Location Type', default='branch', tracking=True)

    # العلاقات
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Company this location belongs to"
    )

    department_ids = fields.One2many(
        'hr.department',
        'office_location_id',
        string='Departments',
        help="Departments working from this location"
    )

    employee_ids = fields.One2many(
        'hr.employee',
        'office_location_id',
        string='Employees',
        help="Employees assigned to this location"
    )

    # حقول محسوبة
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_employee_count',
        store=True
    )

    department_count = fields.Integer(
        string='Department Count',
        compute='_compute_department_count',
        store=True
    )

    # خريطة Google
    google_maps_url = fields.Char(
        string='Google Maps URL',
        compute='_compute_google_maps_url',
        help="Link to view location on Google Maps"
    )

    # إعدادات إضافية
    allow_flexible_radius = fields.Boolean(
        string='Allow Flexible Radius',
        default=False,
        help="Allow attendance check-in from wider range at certain times"
    )

    flexible_radius = fields.Integer(
        string='Flexible Radius (m)',
        default=200,
        help="Wider range allowed in special cases"
    )

    require_wifi = fields.Boolean(
        string='Require WiFi',
        default=False,
        help="Require connection to office WiFi for attendance check-in"
    )

    wifi_name = fields.Char(
        string='WiFi Network Name',
        help="WiFi network name required for connection"
    )

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for location in self:
            location.employee_count = len(location.employee_ids)

    @api.depends('department_ids')
    def _compute_department_count(self):
        for location in self:
            location.department_count = len(location.department_ids)

    @api.depends('latitude', 'longitude')
    def _compute_google_maps_url(self):
        for location in self:
            if location.latitude and location.longitude:
                location.google_maps_url = f"https://www.google.com/maps?q={location.latitude},{location.longitude}"
            else:
                location.google_maps_url = False

    @api.constrains('latitude')
    def _check_latitude(self):
        for location in self:
            if location.latitude < -90 or location.latitude > 90:
                raise ValidationError(_('Latitude must be between -90 and 90'))

    @api.constrains('longitude')
    def _check_longitude(self):
        for location in self:
            if location.longitude < -180 or location.longitude > 180:
                raise ValidationError(_('Longitude must be between -180 and 180'))

    @api.constrains('allowed_radius', 'flexible_radius')
    def _check_radius(self):
        for location in self:
            if location.allowed_radius <= 0:
                raise ValidationError(_('Allowed radius must be greater than zero'))
            if location.flexible_radius <= 0:
                raise ValidationError(_('Flexible radius must be greater than zero'))
            if location.flexible_radius < location.allowed_radius:
                raise ValidationError(_('Flexible radius must be greater than or equal to allowed radius'))

    def action_view_employees(self):
        """View employees assigned to this location"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employees at %s') % self.name,
            'res_model': 'hr.employee',
            'view_mode': 'list,form',
            'domain': [('office_location_id', '=', self.id)],
            'context': {'default_office_location_id': self.id}
        }

    def action_view_departments(self):
        """View departments at this location"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Departments at %s') % self.name,
            'res_model': 'hr.department',
            'view_mode': 'list,form',
            'domain': [('office_location_id', '=', self.id)],
            'context': {'default_office_location_id': self.id}
        }

    def action_open_map(self):
        """Open location on Google Maps"""
        self.ensure_one()
        if self.google_maps_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.google_maps_url,
                'target': 'new',
            }

    @api.model
    def get_nearest_location(self, latitude, longitude):
        """Get nearest office location from given coordinates"""
        locations = self.search([('active', '=', True)])

        if not locations:
            return False

        nearest_location = None
        min_distance = float('inf')

        for location in locations:
            # Calculate distance using function from hr.attendance
            attendance_model = self.env['hr.attendance']
            distance = attendance_model._calculate_distance(
                latitude, longitude,
                location.latitude, location.longitude
            )

            if distance < min_distance:
                min_distance = distance
                nearest_location = location

        return {
            'location': nearest_location,
            'distance': min_distance
        }

    def name_get(self):
        """Customize name display"""
        result = []
        for location in self:
            if location.code:
                name = f"[{location.code}] {location.name}"
            else:
                name = location.name
            result.append((location.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Search by name or code"""
        if args is None:
            args = []

        if name:
            args = ['|', ('name', operator, name), ('code', operator, name)] + args

        return self.search(args, limit=limit).name_get()


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    office_location_id = fields.Many2one(
        'hr.office.location',
        string='Office Location',
        help="Geographical location for this department"
    )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    office_location_id = fields.Many2one(
        'hr.office.location',
        string='Office Location',
        help="Geographical location assigned to this employee",
        tracking=True
    )

    allow_remote_attendance = fields.Boolean(
        string='Allow Remote Attendance',
        default=False,
        help="Allow this employee to check-in from anywhere",
        tracking=True
    )

    temporary_location_ids = fields.One2many(
        'hr.employee.temp.location',
        'employee_id',
        string='Temporary Locations',
        help="Temporary locations allowed for employee attendance"
    )

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Update office location when department changes"""
        if self.department_id and self.department_id.office_location_id:
            self.office_location_id = self.department_id.office_location_id


class HrEmployeeTempLocation(models.Model):
    _name = 'hr.employee.temp.location'
    _description = 'Employee Temporary Locations'
    _rec_name = 'reason'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade'
    )

    date_from = fields.Date(
        string='From Date',
        required=True,
        default=fields.Date.today
    )

    date_to = fields.Date(
        string='To Date',
        required=True
    )

    latitude = fields.Float(
        string='Latitude',
        digits=(10, 6),
        required=True
    )

    longitude = fields.Float(
        string='Longitude',
        digits=(10, 6),
        required=True
    )

    allowed_radius = fields.Integer(
        string='Allowed Radius (m)',
        default=100,
        required=True
    )

    reason = fields.Text(
        string='Reason',
        required=True,
        help="Reason for allowing attendance from this location"
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(_('From date must be before to date'))