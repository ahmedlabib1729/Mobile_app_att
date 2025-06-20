from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StudentApplication(models.Model):
    _name = 'student.application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Student Application Form'

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

    nationality_id = fields.Many2one(
        comodel_name='res.country',
        string='Nationality',
        ondelete='set null',
    )
    last_graduation = fields.Char(string='Last Graduation')
    schedule_day_ids = fields.Many2many('week.days', string='Schedule Days')
    start_date = fields.Date(string='Start Date')
    image_1920 = fields.Image(string="Applicant Image", max_width=1920, max_height=1920)
    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='cascade')

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
    Declaration = fields.Text(string='Declaration - إفصاح')

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
        ('confirm', 'Confirmed'),
        ('linked', 'Linked to Student'),
        ('student_created', 'Student Created')
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

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

    def action_confirm(self):
        for record in self:
            if record.status != 'draft':
                raise UserError(_('Only draft applications can be confirmed.'))

            # Check if student exists
            existing_student = self._find_existing_student()

            if existing_student:
                record.student_id = existing_student
                record.status = 'linked'
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
            if record.status not in ['confirm', 'draft']:
                raise UserError(_('Cannot create student from this status.'))

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
            }

            new_student = self.env['hallway.student'].create(student_vals)
            record.student_id = new_student
            record.status = 'student_created'

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
                record.status = 'linked'
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