from odoo import models, fields, api, _


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
    active = fields.Boolean(string='Active', default=True)

    # Relations
    application_ids = fields.One2many('student.application', 'student_id', string='Applications')
    application_count = fields.Integer(string='Application Count', compute='_compute_application_count')

    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

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