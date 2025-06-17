from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StudentApplication(models.Model):
    _name = 'student.application'
    _description = 'Student Application Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(string='Sequence', required=True, copy=False, readonly=True, default='New')
    first_name = fields.Char(string='First Name', required=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', required=True)
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

    nationality = fields.Char(string='Nationality')
    last_graduation = fields.Char(string='Last Graduation')
    schedule_day_ids = fields.Many2many('week.days', string='Schedule Days')
    start_date = fields.Date(string='Start Date')
    image_1920 = fields.Image(string="Applicant Image", max_width=1920, max_height=1920)
    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='cascade')

    # Relation to student
    student_id = fields.Many2one('hallway.student', string='Student', readonly=True)
    student_exists = fields.Boolean(string='Student Exists', compute='_compute_student_exists', store=True)

    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('linked', 'Linked to Student'),
        ('student_created', 'Student Created')
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    schedule = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
    ], string='Schedule / الجدول')

    # Vocational Qualification Levels
    levl1 = fields.Boolean(string="LEVEL 1 المستوى", default=False)
    levl2 = fields.Boolean(string="LEVEL 2 المستوى", default=False)
    levl3 = fields.Boolean(string="LEVEL 3 المستوى", default=False)
    levl4 = fields.Boolean(string="LEVEL 4 المستوى", default=False)
    levl5 = fields.Boolean(string="LEVEL 5 المستوى", default=False)
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
    Declaration = fields.Text(string='Declaration - إفصاح')

    @api.depends('passport_no', 'emirates_id')
    def _compute_student_exists(self):
        for record in self:
            if record.passport_no or record.emirates_id:
                existing_student = self.env['hallway.student'].search_by_passport_or_emirates_id(
                    passport_no=record.passport_no,
                    emirates_id=record.emirates_id
                )
                record.student_exists = bool(existing_student)
            else:
                record.student_exists = False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('student.application') or 'New'
        return super(StudentApplication, self).create(vals)

    def action_confirm(self):
        """Set status to Confirmed and check for existing student"""
        if not self.passport_no and not self.emirates_id:
            raise UserError(_('Please enter either Passport Number or Emirates ID before confirming!'))

        # Check for existing student
        existing_student = self.env['hallway.student'].search_by_passport_or_emirates_id(
            passport_no=self.passport_no,
            emirates_id=self.emirates_id
        )

        if existing_student:
            # Link to existing student
            self.student_id = existing_student.id
            self.status = 'linked'

            # Update student info if needed
            update_vals = {}
            if self.passport_no and not existing_student.passport_no:
                update_vals['passport_no'] = self.passport_no
            if self.emirates_id and not existing_student.emirates_id:
                update_vals['emirates_id'] = self.emirates_id
            if self.image_1920 and not existing_student.image_1920:
                update_vals['image_1920'] = self.image_1920

            if update_vals:
                existing_student.write(update_vals)

            self.message_post(
                body=f"Application linked to existing student: {existing_student.full_name} (ID: {existing_student.student_id})",
                subtype_xmlid="mail.mt_comment"
            )
        else:
            # No existing student, just confirm
            self.status = 'confirm'
            self.message_post(
                body="Application confirmed. You can now create a new student.",
                subtype_xmlid="mail.mt_comment"
            )

        # Create or update partner
        if not self.partner_id:
            full_name = f"{self.first_name or ''} {self.middle_name or ''} {self.last_name or ''}".strip()
            partner_vals = {
                'name': full_name,
                'phone': self.mobile_no_1,
                'email': self.email_id,
                'street': self.address,
                'city': self.emirate,
                'image_1920': self.image_1920,
            }
            try:
                partner = self.env['res.partner'].create(partner_vals)
                self.partner_id = partner.id
            except Exception as e:
                _logger.error(f"Error Creating Contact: {str(e)}")

    def reset_to_draft(self):
        """Set status to Draft"""
        self.write({'status': 'draft'})

    def action_create_student(self):
        """Create a student from this application"""
        if self.student_id:
            raise UserError(_('Student already linked to this application!'))

        if self.status not in ['confirm', 'linked']:
            raise UserError(_('Please confirm the application before creating a student!'))

        # Double check no existing student
        existing_student = self.env['hallway.student'].search_by_passport_or_emirates_id(
            passport_no=self.passport_no,
            emirates_id=self.emirates_id
        )

        if existing_student:
            raise UserError(_(
                f'A student already exists with this passport/ID!\n'
                f'Student: {existing_student.full_name} (ID: {existing_student.student_id})'
            ))

        student_vals = {
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth,
            'nationality': self.nationality,
            'passport_no': self.passport_no,
            'emirates_id': self.emirates_id,
            'mobile_no_1': self.mobile_no_1,
            'mobile_no_2': self.mobile_no_2,
            'email_id': self.email_id,
            'address': self.address,
            'image_1920': self.image_1920,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'company_id': self.company_id.id,
        }

        try:
            student = self.env['hallway.student'].create(student_vals)
            self.student_id = student.id
            self.status = 'student_created'

            self.message_post(
                body=f"Student created successfully: {student.full_name} (ID: {student.student_id})",
                subtype_xmlid="mail.mt_comment"
            )

            # Return action to show the created student
            return {
                'type': 'ir.actions.act_window',
                'name': 'Student',
                'res_model': 'hallway.student',
                'res_id': student.id,
                'view_mode': 'form',
                'target': 'current',
            }

        except Exception as e:
            _logger.error(f"Error Creating Student: {str(e)}")
            raise UserError(_(f'Error creating student: {str(e)}'))

    def action_view_student(self):
        """Open the related student form"""
        if not self.student_id:
            raise UserError(_('No student linked to this application!'))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Student',
            'res_model': 'hallway.student',
            'res_id': self.student_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.constrains('passport_no', 'emirates_id')
    def _check_duplicate_student(self):
        """Check if passport or emirates ID already exist in confirmed applications"""
        for record in self:
            if record.status in ['draft']:
                continue

            domain = ['&', ('id', '!=', record.id), ('status', 'not in', ['draft'])]

            if record.passport_no:
                duplicate = self.search(domain + [('passport_no', '=', record.passport_no)], limit=1)
                if duplicate and duplicate.student_id:
                    raise UserError(_(
                        f'This passport number is already used in application {duplicate.name} '
                        f'for student {duplicate.student_id.full_name}'
                    ))

            if record.emirates_id:
                duplicate = self.search(domain + [('emirates_id', '=', record.emirates_id)], limit=1)
                if duplicate and duplicate.student_id:
                    raise UserError(_(
                        f'This Emirates ID is already used in application {duplicate.name} '
                        f'for student {duplicate.student_id.full_name}'
                    ))