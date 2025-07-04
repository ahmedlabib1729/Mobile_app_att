from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import re

_logger = logging.getLogger(__name__)


class StudentApplication(models.Model):
    _name = 'student.application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Student Application Form'
    _order = 'name desc'

    application_type = fields.Selection([
        ('qualification', 'Qualification / مؤهل'),
        ('training', 'Training / تدريب')
    ], string='Application Type / نوع الطلب',
        required=True,
        default='qualification',
        tracking=True,
        help='Select whether this application is for a qualification program or language training')

    name = fields.Char(string='Sequence', required=True, copy=False, readonly=True, default='New')
    first_name = fields.Char(string='First Name', required=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', required=True)
    full_name = fields.Char(string='Full Name', compute='_compute_full_name', store=True)

    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender', required=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True)
    application_date = fields.Date(string='Application Date', required=True, default=fields.Date.today)
    mobile_no_1 = fields.Char(string='Mobile No. 1', required=True)
    mobile_no_2 = fields.Char(string='Mobile No. 2')
    email_id = fields.Char(string='Email ID')
    passport_no = fields.Char(string='Passport No.')
    emirates_id = fields.Char(string='Emirates ID')
    address = fields.Text(string='Address')

    emirate = fields.Selection([
        ('Dubai', 'Dubai - دبى'),
        ('AbuDhabi', 'Abu Dhabi -  أبوظبي '),
        ('Sharjah', 'Sharjah - الشارقة'),
        ('Ajman', 'Ajman - عجمان'),
        ('UmmAlQuwain', 'Umm Al Quwain - أم القوين'),
        ('RasAlKhaimah', 'Ras Al Khaimah - رأس الخيمة'),
        ('Fujairah', 'Fujairah -  الفجيرة')
    ], string='Emirate')

    nationality_id = fields.Many2one(
        comodel_name='res.country',
        string='Nationality',
        ondelete='set null',
    )
    last_graduation = fields.Char(string='Last Graduation')
    schedule_day_ids = fields.Many2many('week.days', string='Schedule Days')
    start_date = fields.Date(string='Start Date')
    image_1920 = fields.Image(string="Applicant Photo", max_width=1920, max_height=1920)

    # Document attachments
    id_card_image = fields.Binary(string="ID Card Image / صورة الهوية", attachment=True)
    id_card_filename = fields.Char(string="ID Card Filename")

    passport_image = fields.Binary(string="Passport Image / صورة جواز السفر", attachment=True)
    passport_filename = fields.Char(string="Passport Filename")

    last_certificate_image = fields.Binary(string="Last Certificate / آخر شهادة", attachment=True)
    last_certificate_filename = fields.Char(string="Certificate Filename")

    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='cascade')

    schedule = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
    ], string='Schedule / الجدول')

    # Program Selection
    program_selection_ids = fields.One2many('application.program', 'application_id', string='Selected Programs')
    has_program_selection = fields.Boolean(string='Has Program Selection', compute='_compute_has_program_selection')

    # Vocational Qualification Levels
    levl1 = fields.Boolean(string="LEVEL 1 المستوى", default=False)
    levl2 = fields.Boolean(string="LEVEL 2 المستوى", default=False)
    levl3 = fields.Boolean(string="LEVEL 3 المستوى", default=False)
    levl4 = fields.Boolean(string="LEVEL 4 المستوى", default=False)
    levl5 = fields.Boolean(string="LEVEL 5 المستوى", default=False)
    extend_level = fields.Boolean(string="Extend Level", default=False)
    levl6 = fields.Boolean(string="LEVEL 6 المستوى", default=False)
    levl7 = fields.Boolean(string="LEVEL 7 المستوى", default=False)
    other = fields.Boolean(string="OTHER أخرى ", default=False)

    # Business Courses
    accounting_and_finance = fields.Boolean(string="Accounting and Finance - المحاسبة المالية", default=False)
    business_mangement = fields.Boolean(string="Business Mangment - إدارة أعمال", default=False)
    commercial_law = fields.Boolean(string="Commercial Law -  القانون التجارى", default=False)
    enterpreneurship_and_small = fields.Boolean(
        string="Enterpreneurship And Small B.M - الريادة و إدارة المشروعات الصغيرة  ", default=False)
    humen = fields.Boolean(string="Human Resource Management - إدارة الموارد البشرية ", default=False)
    market = fields.Boolean(string="Marketing Management - إدارة التسويق ", default=False)
    others = fields.Boolean(string="Others - أخرى", default=False)

    # Arabic Language Levels
    beginnera = fields.Boolean(string="Beginner Arabic - مبتدأ عربي", default=False)
    Pre_Intermediatea = fields.Boolean(string="Pre-Intermediate Arabic - قبل المتوسط عربي", default=False)
    Intermediatea = fields.Boolean(string="Intermediate Arabic - متوسط عربي", default=False)
    Advanceda = fields.Boolean(string="Advanced Arabic - متقدم عربي", default=False)
    Proficienta = fields.Boolean(string="Proficient Arabic - محترف عربي", default=False)

    # English Language Levels
    beginnere = fields.Boolean(string="Beginner English - مبتدأ إنجليزي", default=False)
    Pre_Intermediatee = fields.Boolean(string="Pre-Intermediate English - قبل المتوسط إنجليزي", default=False)
    Intermediatee = fields.Boolean(string="Intermediate English - متوسط إنجليزي", default=False)
    Advancede = fields.Boolean(string="Advanced English - متقدم إنجليزي", default=False)
    Proficiente = fields.Boolean(string="Proficient English - محترف إنجليزي", default=False)

    # English Course For Kids
    Early = fields.Boolean(string="Early - المراحل الأولى", default=False)
    Starters = fields.Boolean(string="Starters - المبتدئون", default=False)
    Movers = fields.Boolean(string="Movers - المستويات المتوسطة", default=False)
    Flyers = fields.Boolean(string="Flyers - المستويات المتقدمة", default=False)
    Otherk = fields.Boolean(string="Other - أخرى", default=False)

    other_Course = fields.Text(string='OTHER COURSES - دورات أخرى')
    Declaration = fields.Text(
        string='Declaration - إفصاح',
        default="غاية معهد هال واى للإدارة هو ضمان عمل نزيه و على نحو ملائم ى إتخاذ القرار حول قبول الطالب و تسجيلة و تحديد مستواة "
    )
    existing_student_id = fields.Many2one(
        'hallway.student',
        string='Select Existing Student',
        domain=[('active', '=', True)]
    )

    student_id = fields.Many2one('hallway.student', string='Student', readonly=True)
    student_exists = fields.Boolean(string='Student Exists', compute='_compute_student_exists', store=True)

    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed')
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    enrollment_ids = fields.One2many('hallway.enrollment', 'application_id',
                                     string='Enrollments')
    enrollment_count = fields.Integer(string='Enrollment Count',
                                      compute='_compute_enrollment_count')
    has_enrollment = fields.Boolean(string='Has Enrollment',
                                    compute='_compute_enrollment_count')

    @api.depends('first_name', 'middle_name', 'last_name')
    def _compute_full_name(self):
        for record in self:
            name_parts = filter(None, [record.first_name, record.middle_name, record.last_name])
            record.full_name = ' '.join(name_parts)

    @api.depends('program_selection_ids')
    def _compute_has_program_selection(self):
        for record in self:
            record.has_program_selection = bool(record.program_selection_ids)

    @api.depends('enrollment_ids')
    def _compute_enrollment_count(self):
        for record in self:
            record.enrollment_count = len(record.enrollment_ids)
            record.has_enrollment = bool(record.enrollment_ids)

    def action_view_enrollments(self):
        """Open enrollments related to this application"""
        self.ensure_one()

        if self.enrollment_count == 1:
            # فتح الـ enrollment مباشرة إذا كان واحد فقط
            return {
                'type': 'ir.actions.act_window',
                'name': _('Enrollment'),
                'res_model': 'hallway.enrollment',
                'res_id': self.enrollment_ids.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            # فتح قائمة بالـ enrollments إذا كان أكثر من واحد
            return {
                'type': 'ir.actions.act_window',
                'name': _('Enrollments'),
                'res_model': 'hallway.enrollment',
                'view_mode': 'list,form',
                'domain': [('application_id', '=', self.id)],
                'context': {
                    'default_application_id': self.id,
                    'default_student_id': self.student_id.id,
                }
            }

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
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('student.application') or 'New'
        return super().create(vals_list)

    @api.depends('passport_no', 'emirates_id')
    def _compute_student_exists(self):
        for record in self:
            domain = []
            if record.passport_no:
                domain = [('passport_no', '=', record.passport_no)]
            elif record.emirates_id:
                domain = [('emirates_id', '=', record.emirates_id)]

            if domain:
                record.student_exists = bool(self.env['hallway.student'].search(domain, limit=1))
            else:
                record.student_exists = False

    @api.onchange('existing_student_id')
    def _onchange_existing_student_id(self):
        if self.existing_student_id:
            self.first_name = self.existing_student_id.first_name
            self.middle_name = self.existing_student_id.middle_name
            self.last_name = self.existing_student_id.last_name
            self.gender = self.existing_student_id.gender
            self.date_of_birth = self.existing_student_id.date_of_birth
            self.mobile_no_1 = self.existing_student_id.mobile_no_1
            self.mobile_no_2 = self.existing_student_id.mobile_no_2
            self.email_id = self.existing_student_id.email_id
            self.passport_no = self.existing_student_id.passport_no
            self.emirates_id = self.existing_student_id.emirates_id
            self.address = self.existing_student_id.address
            self.emirate = self.existing_student_id.emirate
            self.nationality_id = self.existing_student_id.nationality_id
            self.image_1920 = self.existing_student_id.image_1920
            # Transfer documents
            self.id_card_image = self.existing_student_id.id_card_image
            self.id_card_filename = self.existing_student_id.id_card_filename
            self.passport_image = self.existing_student_id.passport_image
            self.passport_filename = self.existing_student_id.passport_filename
            self.last_certificate_image = self.existing_student_id.last_certificate_image
            self.last_certificate_filename = self.existing_student_id.last_certificate_filename

    def action_confirm(self):
        for record in self:
            if record.status != 'draft':
                raise UserError(_('Only draft applications can be confirmed.'))

            # Check if student exists
            existing_student = self._find_existing_student()

            if existing_student:
                record.student_id = existing_student
                record.status = 'confirm'
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Existing Student Found'),
                    'res_model': 'hallway.student',
                    'res_id': existing_student.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                record.status = 'confirm'

    def action_create_student(self):
        for record in self:
            if record.status != 'confirm':
                raise UserError(_('Only confirmed applications can create students.'))

            if record.student_id:
                raise UserError(_('Student already exists for this application.'))

            # Create new student
            student_vals = {
                'first_name': record.first_name,
                'middle_name': record.middle_name,
                'last_name': record.last_name,
                'gender': record.gender,
                'date_of_birth': record.date_of_birth,
                'mobile_no_1': record.mobile_no_1,
                'mobile_no_2': record.mobile_no_2,
                'email_id': record.email_id,
                'passport_no': record.passport_no,
                'emirates_id': record.emirates_id,
                'address': record.address,
                'emirate': record.emirate,
                'nationality_id': record.nationality_id.id,
                'image_1920': record.image_1920,
                'company_id': record.company_id.id,
                # Transfer document attachments
                'id_card_image': record.id_card_image,
                'id_card_filename': record.id_card_filename,
                'passport_image': record.passport_image,
                'passport_filename': record.passport_filename,
                'last_certificate_image': record.last_certificate_image,
                'last_certificate_filename': record.last_certificate_filename,
            }

            new_student = self.env['hallway.student'].create(student_vals)
            record.student_id = new_student

            return {
                'type': 'ir.actions.act_window',
                'name': _('Student Created'),
                'res_model': 'hallway.student',
                'res_id': new_student.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_link_to_student(self):
        for record in self:
            existing_student = self._find_existing_student()
            if existing_student:
                record.student_id = existing_student
            else:
                raise UserError(_('No existing student found with the same Passport or Emirates ID.'))

    def _find_existing_student(self):
        self.ensure_one()
        domain = ['|',
                  ('passport_no', '=', self.passport_no),
                  ('emirates_id', '=', self.emirates_id)]
        return self.env['hallway.student'].search(domain, limit=1)

    def action_view_student(self):
        self.ensure_one()
        if not self.student_id:
            raise UserError(_('No student linked to this application.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Student'),
            'res_model': 'hallway.student',
            'res_id': self.student_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_select_programs(self):
        """Open wizard to select programs"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Programs'),
            'res_model': 'application.program.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_application_id': self.id,
            }
        }

    def action_create_enrollment_wizard(self):
        """Open wizard to create enrollment"""
        self.ensure_one()

        # التحقق من الحالة
        if self.status != 'confirm':
            raise UserError(_('Please confirm the application first.'))

        if not self.student_id:
            raise UserError(_('No student linked to this application. Please create or link a student first.'))

        # تحذير إذا كان هناك enrollment موجود
        if self.has_enrollment:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _(
                        'This application already has %s enrollment(s). Are you sure you want to create another one?') % self.enrollment_count,
                    'type': 'warning',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.act_window',
                        'name': _('Create Enrollment'),
                        'res_model': 'create.enrollment.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_application_id': self.id,
                            'default_student_id': self.student_id.id,
                        }
                    }
                }
            }

        # فتح الـ wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Enrollment'),
            'res_model': 'create.enrollment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_application_id': self.id,
                'default_student_id': self.student_id.id,
            }
        }