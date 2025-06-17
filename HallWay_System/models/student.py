from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class Student(models.Model):
    _name = 'hallway.student'
    _description = 'Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'student_id desc'
    _sql_constraints = [
        ('passport_unique', 'UNIQUE(passport_no)', 'Passport number must be unique!'),
        ('emirates_id_unique', 'UNIQUE(emirates_id)', 'Emirates ID must be unique!'),
    ]

    # Student Information
    student_id = fields.Char(string='Student ID', required=True, copy=False, readonly=True, default='New')
    first_name = fields.Char(string='First Name', required=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', required=True)
    full_name = fields.Char(string='Full Name', compute='_compute_full_name', store=True)

    # Personal Information
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender', required=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True)
    nationality = fields.Char(string='Nationality')
    passport_no = fields.Char(string='Passport No.')
    emirates_id = fields.Char(string='Emirates ID')
    image_1920 = fields.Image(string="Student Image", max_width=1920, max_height=1920)

    # Contact Information
    mobile_no_1 = fields.Char(string='Mobile No. 1', required=True)
    mobile_no_2 = fields.Char(string='Mobile No. 2')
    email_id = fields.Char(string='Email ID', required=True)
    address = fields.Text(string='Address')

    # Relations
    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='cascade')
    application_ids = fields.One2many('student.application', 'student_id', string='Applications')
    application_count = fields.Integer(string='Application Count', compute='_compute_application_count')
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    # Status
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('graduated', 'Graduated'),
        ('suspended', 'Suspended')
    ], string='Status', default='active', required=True, tracking=True)

    @api.depends('first_name', 'middle_name', 'last_name')
    def _compute_full_name(self):
        for record in self:
            name_parts = []
            if record.first_name:
                name_parts.append(record.first_name)
            if record.middle_name:
                name_parts.append(record.middle_name)
            if record.last_name:
                name_parts.append(record.last_name)
            record.full_name = ' '.join(name_parts)

    @api.depends('application_ids')
    def _compute_application_count(self):
        for record in self:
            record.application_count = len(record.application_ids)

    @api.model
    def create(self, vals):
        if vals.get('student_id', 'New') == 'New':
            vals['student_id'] = self.env['ir.sequence'].next_by_code('hallway.student') or 'New'

        # Create related partner if not exists
        if not vals.get('partner_id'):
            full_name = f"{vals.get('first_name', '')} {vals.get('middle_name', '')} {vals.get('last_name', '')}".strip()
            partner_vals = {
                'name': full_name,
                'phone': vals.get('mobile_no_1'),
                'mobile': vals.get('mobile_no_2'),
                'email': vals.get('email_id'),
                'street': vals.get('address'),
                'image_1920': vals.get('image_1920'),
                'is_company': False,
            }
            partner = self.env['res.partner'].create(partner_vals)
            vals['partner_id'] = partner.id

        return super(Student, self).create(vals)

    def write(self, vals):
        res = super(Student, self).write(vals)

        # Update partner info if changed
        for record in self:
            if record.partner_id:
                partner_vals = {}
                if 'first_name' in vals or 'middle_name' in vals or 'last_name' in vals:
                    partner_vals['name'] = record.full_name
                if 'mobile_no_1' in vals:
                    partner_vals['phone'] = vals['mobile_no_1']
                if 'mobile_no_2' in vals:
                    partner_vals['mobile'] = vals['mobile_no_2']
                if 'email_id' in vals:
                    partner_vals['email'] = vals['email_id']
                if 'address' in vals:
                    partner_vals['street'] = vals['address']
                if 'image_1920' in vals:
                    partner_vals['image_1920'] = vals['image_1920']

                if partner_vals:
                    record.partner_id.write(partner_vals)

        return res

    @api.model
    def search_by_passport_or_emirates_id(self, passport_no=None, emirates_id=None):
        """Search for existing student by passport or emirates ID"""
        domain = []
        if passport_no:
            domain.append(('passport_no', '=', passport_no))
        if emirates_id:
            if domain:
                domain.insert(0, '|')
            domain.append(('emirates_id', '=', emirates_id))

        if domain:
            return self.search(domain, limit=1)
        return False

    def action_view_applications(self):
        """View all applications for this student"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'student.application',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id}
        }