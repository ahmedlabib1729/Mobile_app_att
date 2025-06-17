from odoo import models, fields, api, _
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
    start_date = fields.Date(string='Strat Date')
    image_1920 = fields.Image(string="Applicant Image", max_width=1920, max_height=1920)  # إضافة حقل الصورة
    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='cascade')


    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('invoiced', 'Invoiced')
    ], string='Status', default='draft', required=True, copy=False, tracking=True)





    schedule = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),

    ], string='Schedule / الجدول')

    levl1 = fields.Boolean(string="LEVEL 1 المستوى", default=False)
    levl2 = fields.Boolean(string="LEVEL 2 المستوى", default=False)
    levl3 = fields.Boolean(string="LEVEL 3 المستوى", default=False)
    levl4 = fields.Boolean(string="LEVEL 4 المستوى", default=False)
    levl5 = fields.Boolean(string="LEVEL 5 المستوى", default=False)
    levl6 = fields.Boolean(string="LEVEL 6 المستوى", default=False)
    levl7 = fields.Boolean(string="LEVEL 7 المستوى", default=False)
    other = fields.Boolean(string="OTHER أخرى ", default=False)

    accounting_and_finance = fields.Boolean(string="Accounting and Finance - المحاسبة المالية", default=False)
    business_mangement = fields.Boolean(string="Business Mangment - إدارة أعمال", default=False)
    commercial_law = fields.Boolean(string="Commercial Law -  القانون التجارى", default=False)
    enterpreneurship_and_small = fields.Boolean(string="Enterpreneurship And Small B.M - الريادة و إدارة المشروعات الصغيرة  ", default=False)
    humen = fields.Boolean(string="Human Resource Management - إدارة الموارد البشرية ", default=False)
    market = fields.Boolean(string="Marketing Management - إدارة التسويق ", default=False)
    others = fields.Boolean(string="Others - أخرى", default=False)

    beginnera = fields.Boolean(string="Beginner - مبتدأ", default=False)
    beginnere = fields.Boolean(string="Beginner - مبتدأ", default=False)

    Pre_Intermediatea = fields.Boolean(string="Pre-Intermediate - قبل المتوسط", default=False)
    Pre_Intermediatee = fields.Boolean(string="Pre-Intermediate - قبل المتوسط", default=False)

    Intermediatea = fields.Boolean(string="Intermediate - متوسط ", default=False)
    Intermediatee = fields.Boolean(string="Intermediate - متوسط ", default=False)

    Advanceda = fields.Boolean(string="Advanced - متقدم ", default=False)
    Advancede = fields.Boolean(string="Advanced - متقدم ", default=False)

    Proficienta = fields.Boolean(string="Proficient - محترف ", default=False)
    Proficiente = fields.Boolean(string="Proficient - محترف ", default=False)

    Early = fields.Boolean(string="Early - المراحل الأولى  ", default=False)
    Starters = fields.Boolean(string="Starters - المبتدئون ", default=False)
    Movers = fields.Boolean(string="Movers - المستويات المتوسطة  ", default=False)
    Flyers = fields.Boolean(string="Flyers - المستويات المتقدمة  ", default=False)
    Otherk = fields.Boolean(string="Other - أخرى   ", default=False)
    other_Course = fields.Text(string='OTHER COURSES - دورات أخرى')
    Declaration  = fields.Text(string='Declaration -  إفصاح')









    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('student.application') or 'New'
        return super(StudentApplication, self).create(vals)



    def action_confirm(self):
        """Set status to Confirmed"""
        self.write({'status': 'confirm'})

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
                _logger.info(f"✅ Contact Created on Confirmation: {partner.name} (ID: {partner.id})")
            except Exception as e:
                _logger.error(f"❌ Error Creating Contact on Confirmation: {str(e)}")

        self.message_post(body="The application has been confirmed and a related contact has been created.",
                          subtype_xmlid="mail.mt_comment")  # تسجيل تعليق في Chatter
        self.write({'status': 'confirm'})

    def reset_to_draft(self):
        """Set status to Draft"""
        self.write({'status': 'draft'})





