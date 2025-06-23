from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class HallwayStudent(models.Model):
    _name = 'hallway.student'
    _description = 'Hallway Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'full_name'
    _order = 'create_date desc'

    # Student Information
    student_code = fields.Char(string='Student Code', required=True, copy=False, readonly=True, default='New')
    first_name = fields.Char(string='First Name', required=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', required=True)
    full_name = fields.Char(string='Full Name', compute='_compute_full_name', store=True)

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female')
    ], string='Gender', required=True)

    date_of_birth = fields.Date(string='Date of Birth', required=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)

    # Contact Information
    mobile_no_1 = fields.Char(string='Mobile No. 1', required=True)
    mobile_no_2 = fields.Char(string='Mobile No. 2')
    email_id = fields.Char(string='Email ID')

    # Identification
    passport_no = fields.Char(string='Passport No.', required=True)
    emirates_id = fields.Char(string='Emirates ID', required=True)

    # Address
    address = fields.Text(string='Address')
    emirate = fields.Selection([
        ('Dubai', 'Dubai - دبى'),
        ('AbuDhabi', 'Abu Dhabi - أبوظبي'),
        ('Sharjah', 'Sharjah - الشارقة'),
        ('Ajman', 'Ajman - عجمان'),
        ('UmmAlQuwain', 'Umm Al Quwain - أم القوين'),
        ('RasAlKhaimah', 'Ras Al Khaimah - رأس الخيمة'),
        ('Fujairah', 'Fujairah - الفجيرة')
    ], string='Emirate')

    nationality_id = fields.Many2one('res.country', string='Nationality', required=True)

    # Other Information
    image_1920 = fields.Image(string="Student Photo", max_width=1920, max_height=1920)

    # Document attachments
    id_card_image = fields.Binary(string="ID Card Image / صورة الهوية", attachment=True)
    id_card_filename = fields.Char(string="ID Card Filename")

    passport_image = fields.Binary(string="Passport Image / صورة جواز السفر", attachment=True)
    passport_filename = fields.Char(string="Passport Filename")

    last_certificate_image = fields.Binary(string="Last Certificate / آخر شهادة", attachment=True)
    last_certificate_filename = fields.Char(string="Certificate Filename")

    active = fields.Boolean(string='Active', default=True)

    # Relations
    application_ids = fields.One2many('student.application', 'student_id', string='Applications')
    application_count = fields.Integer(string='Application Count', compute='_compute_application_count')

    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    @api.constrains('emirates_id')
    def _check_emirates_id(self):
        """
        Validate Emirates ID format.
        Emirates ID format: 784-YYYY-NNNNNNN-C
        Where:
        - 784 is the country code for UAE
        - YYYY is the year of birth
        - NNNNNNN is a 7-digit serial number
        - C is a check digit
        """
        for record in self:
            if record.emirates_id:
                # Remove spaces and hyphens for validation
                emirates_id_clean = record.emirates_id.replace('-', '').replace(' ', '')

                # Check if it's exactly 15 digits
                if not emirates_id_clean.isdigit() or len(emirates_id_clean) != 15:
                    raise ValidationError(_(
                        "Emirates ID must be exactly 15 digits in format: 784-YYYY-NNNNNNN-C\n"
                        "Example: 784-1990-1234567-8"
                    ))

                # Check if it starts with 784
                if not emirates_id_clean.startswith('784'):
                    raise ValidationError(_(
                        "Emirates ID must start with 784 (UAE country code)"
                    ))

                # Validate year part (position 3-7)
                year_part = emirates_id_clean[3:7]
                try:
                    year = int(year_part)
                    if year < 1900 or year > 2100:
                        raise ValidationError(_(
                            "The year part of Emirates ID seems invalid. It should be between 1900 and 2100."
                        ))
                except ValueError:
                    raise ValidationError(_("Invalid year format in Emirates ID"))

                # Optional: Format the Emirates ID for display
                formatted_id = f"{emirates_id_clean[:3]}-{emirates_id_clean[3:7]}-{emirates_id_clean[7:14]}-{emirates_id_clean[14]}"
                if record.emirates_id != formatted_id:
                    record.emirates_id = formatted_id

    @api.constrains('passport_no')
    def _check_passport_no(self):
        """
        Validate passport number format.
        Passport numbers vary by country but generally:
        - 6-9 alphanumeric characters
        - May contain letters and numbers
        - No special characters except sometimes hyphens
        """
        for record in self:
            if record.passport_no:
                # Remove spaces and convert to uppercase
                passport_clean = record.passport_no.strip().upper()

                # Check length (most passports are 6-9 characters)
                if len(passport_clean) < 6 or len(passport_clean) > 12:
                    raise ValidationError(_(
                        "Passport number must be between 6 and 12 characters long."
                    ))

                # Check for valid characters (letters, numbers, and optionally hyphens)
                if not re.match(r'^[A-Z0-9\-]+$', passport_clean):
                    raise ValidationError(_(
                        "Passport number can only contain letters, numbers, and hyphens."
                    ))

                # Check that it contains at least one letter and one number
                has_letter = any(c.isalpha() for c in passport_clean)
                has_digit = any(c.isdigit() for c in passport_clean)

                if not (has_letter and has_digit):
                    raise ValidationError(_(
                        "Passport number must contain both letters and numbers."
                    ))

                # Update the passport number to uppercase
                if record.passport_no != passport_clean:
                    record.passport_no = passport_clean

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('student_code', 'New') == 'New':
                vals['student_code'] = self.env['ir.sequence'].next_by_code('hallway.student') or 'New'
        return super().create(vals_list)

    @api.depends('first_name', 'middle_name', 'last_name')
    def _compute_full_name(self):
        for record in self:
            name_parts = filter(None, [record.first_name, record.middle_name, record.last_name])
            record.full_name = ' '.join(name_parts)

    @api.depends('date_of_birth')
    def _compute_age(self):
        from datetime import date
        for record in self:
            if record.date_of_birth:
                today = date.today()
                record.age = today.year - record.date_of_birth.year - (
                        (today.month, today.day) < (record.date_of_birth.month, record.date_of_birth.day))
            else:
                record.age = 0

    def _compute_application_count(self):
        for record in self:
            record.application_count = self.env['student.application'].search_count([('student_id', '=', record.id)])

    def action_view_applications(self):
        return {
            'name': 'Student Applications',
            'type': 'ir.actions.act_window',
            'res_model': 'student.application',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id}
        }