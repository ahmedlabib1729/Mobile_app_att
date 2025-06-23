from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreateEnrollmentWizard(models.TransientModel):
    _name = 'create.enrollment.wizard'
    _description = 'Create Enrollment from Application'

    # Application info
    application_id = fields.Many2one('student.application', string='Application',
                                     readonly=True, required=True)
    student_id = fields.Many2one('hallway.student', string='Student',
                                 readonly=True, required=True)

    # Program selection
    program_id = fields.Many2one('hallway.program', string='Program',
                                 domain="[('active', '=', True)]")
    level_ids = fields.Many2many('program.level', string='Select Levels',
                                 domain="[('program_id', '=', program_id)]")

    # Common fields
    start_date = fields.Date(string='Start Date', required=True,
                             default=fields.Date.today)
    payment_method = fields.Selection([
        ('cash', 'Cash Payment'),
        ('installment', 'Installment')
    ], string='Payment Method', required=True, default='cash')

    installment_count = fields.Integer(string='Number of Installments', default=3)

    # Computed fields
    total_amount = fields.Monetary(string='Total Amount',
                                   compute='_compute_total_amount', store=True)

    # Discount fields
    discount_type = fields.Selection([
        ('none', 'No Discount'),
        ('percentage', 'Percentage'),
        ('amount', 'Fixed Amount')
    ], string='Discount Type', default='none')
    discount_percentage = fields.Float(string='Discount (%)', digits='Discount')
    discount_amount = fields.Monetary(string='Discount Amount')
    discount_reason = fields.Text(string='Discount Reason')

    # Computed discount fields
    subtotal_amount = fields.Monetary(string='Subtotal',
                                      compute='_compute_discount_amounts', store=True)
    total_discount = fields.Monetary(string='Total Discount',
                                     compute='_compute_discount_amounts', store=True)
    final_amount = fields.Monetary(string='Final Amount',
                                   compute='_compute_discount_amounts', store=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Display suggested programs
    suggested_programs = fields.Text(string='Suggested Programs',
                                     compute='_compute_suggested_programs')

    @api.depends('application_id')
    def _compute_suggested_programs(self):
        """Suggest programs based on application selections"""
        for wizard in self:
            suggestions = []

            # تحليل الاختيارات في الـ application
            app = wizard.application_id

            # Business courses mapping
            if app.accounting_and_finance:
                suggestions.append("- Accounting/Finance programs")
            if app.business_mangement:
                suggestions.append("- Business Management programs")
            if app.humen:
                suggestions.append("- Human Resources programs")
            if app.market:
                suggestions.append("- Marketing programs")

            # Levels
            levels = []
            if app.levl1: levels.append("Level 1")
            if app.levl2: levels.append("Level 2")
            if app.levl3: levels.append("Level 3")
            if app.levl4: levels.append("Level 4")
            if app.levl5: levels.append("Level 5")
            if app.levl6: levels.append("Level 6")
            if app.levl7: levels.append("Level 7")
            if levels:
                suggestions.append(f"- Suggested levels: {', '.join(levels)}")

            wizard.suggested_programs = '\n'.join(suggestions) if suggestions else 'No specific suggestions'

    @api.depends('program_id', 'level_ids')
    def _compute_total_amount(self):
        """Calculate total amount based on selection"""
        for wizard in self:
            if wizard.level_ids:
                wizard.total_amount = sum(wizard.level_ids.mapped('total_price'))
            else:
                wizard.total_amount = 0

    @api.depends('total_amount', 'discount_type', 'discount_percentage', 'discount_amount')
    def _compute_discount_amounts(self):
        """Calculate discount amounts"""
        for wizard in self:
            wizard.subtotal_amount = wizard.total_amount

            if wizard.discount_type == 'percentage':
                wizard.total_discount = (wizard.total_amount * wizard.discount_percentage) / 100.0
            elif wizard.discount_type == 'amount':
                wizard.total_discount = wizard.discount_amount
            else:
                wizard.total_discount = 0.0

            wizard.final_amount = wizard.subtotal_amount - wizard.total_discount

    @api.onchange('discount_type')
    def _onchange_discount_type(self):
        """Clear discount values when type changes"""
        if self.discount_type == 'none':
            self.discount_percentage = 0.0
            self.discount_amount = 0.0
        elif self.discount_type == 'percentage':
            self.discount_amount = 0.0
        elif self.discount_type == 'amount':
            self.discount_percentage = 0.0

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        """Set default installment count"""
        if self.payment_method == 'cash':
            self.installment_count = 1
        elif self.payment_method == 'installment' and self.installment_count <= 1:
            self.installment_count = 3

    @api.onchange('program_id')
    def _onchange_program_id(self):
        """Auto-select levels based on application"""
        if not self.program_id:
            self.level_ids = [(5, 0, 0)]
            return

        # Auto-select matching levels
        app = self.application_id
        selected_levels = self.env['program.level']

        level_mapping = {
            'levl1': '1',
            'levl2': '2',
            'levl3': '3',
            'levl4': '4',
            'levl5': '5',
            'levl6': '6',
            'levl7': '7',
        }

        for field, level_num in level_mapping.items():
            if getattr(app, field, False):
                # البحث عن المستوى المطابق
                matching_levels = self.program_id.level_ids.filtered(
                    lambda l: level_num in l.name or f'Level {level_num}' in l.name
                )
                selected_levels |= matching_levels

        self.level_ids = selected_levels

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        for wizard in self:
            if wizard.discount_type == 'percentage':
                if wizard.discount_percentage < 0 or wizard.discount_percentage > 100:
                    raise UserError(_('Discount percentage must be between 0 and 100.'))

    @api.constrains('discount_amount')
    def _check_discount_amount(self):
        for wizard in self:
            if wizard.discount_type == 'amount':
                if wizard.discount_amount < 0:
                    raise UserError(_('Discount amount cannot be negative.'))
                if wizard.discount_amount > wizard.total_amount:
                    raise UserError(_('Discount amount cannot exceed total amount.'))

    def action_create_enrollment(self):
        """Create enrollment based on wizard data"""
        self.ensure_one()

        # Validation
        if not self.program_id:
            raise UserError(_('Please select a program.'))
        if not self.level_ids:
            raise UserError(_('Please select at least one level.'))

        # Check if application.program already exists
        existing_app_program = self.env['application.program'].search([
            ('application_id', '=', self.application_id.id),
            ('program_id', '=', self.program_id.id)
        ], limit=1)

        if existing_app_program:
            # Update existing record
            existing_app_program.level_ids = [(6, 0, self.level_ids.ids)]
            app_program = existing_app_program
        else:
            # Create new application.program record
            app_program = self.env['application.program'].create({
                'application_id': self.application_id.id,
                'program_id': self.program_id.id,
                'level_ids': [(6, 0, self.level_ids.ids)],
                'is_primary': True,
            })

        # Create enrollment
        enrollment_vals = {
            'student_id': self.student_id.id,
            'application_id': self.application_id.id,
            'application_program_id': app_program.id,
            'enrollment_date': fields.Date.today(),
            'start_date': self.start_date,
            'total_amount': self.total_amount,
            'discount_type': self.discount_type,
            'discount_percentage': self.discount_percentage,
            'discount_amount': self.discount_amount,
            'discount_reason': self.discount_reason,
            'payment_method': self.payment_method,
            'installment_count': self.installment_count if self.payment_method == 'installment' else 1,
            'state': 'draft',
        }

        enrollment = self.env['hallway.enrollment'].create(enrollment_vals)

        # Return action to open the created enrollment
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enrollment Created'),
            'res_model': 'hallway.enrollment',
            'res_id': enrollment.id,
            'view_mode': 'form',
            'target': 'current',
        }