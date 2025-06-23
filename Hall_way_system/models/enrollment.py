from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class Enrollment(models.Model):
    _name = 'hallway.enrollment'
    _description = 'Student Enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'enrollment_number'
    _order = 'enrollment_date desc, id desc'

    # Basic Information
    enrollment_number = fields.Char(string='Enrollment Number', required=True, copy=False, readonly=True, default='New')
    student_id = fields.Many2one('hallway.student', string='Student', required=True,
                                 ondelete='restrict', tracking=True)
    application_id = fields.Many2one('student.application', string='Application',
                                     domain="[('student_id', '=', student_id), ('status', '=', 'confirm')]")

    # Program Information
    application_program_id = fields.Many2one('application.program', string='Program Selection',
                                             required=True, ondelete='restrict')
    program_id = fields.Many2one('hallway.program', string='Program',
                                 compute='_compute_program_info', store=True)

    # For Qualification
    level_ids = fields.Many2many('program.level', string='Enrolled Levels',
                                 compute='_compute_program_info', store=True)

    # Dates
    enrollment_date = fields.Date(string='Enrollment Date', required=True,
                                  default=fields.Date.today, tracking=True)
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    expected_end_date = fields.Date(string='Expected End Date', compute='_compute_expected_end_date',
                                    store=True)
    actual_end_date = fields.Date(string='Actual End Date', readonly=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    # Financial Information
    total_amount = fields.Monetary(string='Total Amount', required=True, tracking=True)

    # Discount fields
    discount_type = fields.Selection([
        ('none', 'No Discount'),
        ('percentage', 'Percentage'),
        ('amount', 'Fixed Amount')
    ], string='Discount Type', default='none', tracking=True)
    discount_percentage = fields.Float(string='Discount (%)',
                                       digits='Discount',
                                       tracking=True)
    discount_amount = fields.Monetary(string='Discount Amount',
                                      tracking=True)
    discount_reason = fields.Text(string='Discount Reason')

    # Computed fields
    subtotal_amount = fields.Monetary(string='Subtotal',
                                      compute='_compute_amounts',
                                      store=True)
    total_discount = fields.Monetary(string='Total Discount',
                                     compute='_compute_amounts',
                                     store=True)
    final_amount = fields.Monetary(string='Final Amount',
                                   compute='_compute_amounts',
                                   store=True)

    payment_method = fields.Selection([
        ('cash', 'Cash - Full Payment'),
        ('installment', 'Installment Plan')
    ], string='Payment Method', required=True, default='cash')

    installment_count = fields.Integer(string='Number of Installments', default=1)
    amount_paid = fields.Monetary(string='Amount Paid', compute='_compute_payment_info', store=True)
    amount_remaining = fields.Monetary(string='Amount Remaining', compute='_compute_payment_info', store=True)
    payment_percentage = fields.Float(string='Payment %', compute='_compute_payment_info', store=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id, required=True)

    # Relations
    payment_plan_id = fields.Many2one('enrollment.payment.plan', string='Payment Plan',
                                      ondelete='restrict', copy=False)
    installment_ids = fields.One2many('enrollment.installment', 'enrollment_id', string='Installments')
    payment_ids = fields.One2many('enrollment.payment', 'enrollment_id', string='Payments')

    # Invoice Integration
    invoice_ids = fields.One2many('account.move', 'enrollment_id', string='Invoices',
                                  domain=[('move_type', '=', 'out_invoice')])
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 compute='_compute_partner_id', store=True)

    # Additional Info
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True)

    # Computed display fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    has_overdue = fields.Boolean(string='Has Overdue', compute='_compute_has_overdue', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('enrollment_number', 'New') == 'New':
                vals['enrollment_number'] = self.env['ir.sequence'].next_by_code('hallway.enrollment') or 'New'
        return super().create(vals_list)

    @api.depends('student_id')
    def _compute_partner_id(self):
        """Get or create partner from student"""
        for record in self:
            if record.student_id:
                # البحث عن partner موجود
                partner = self.env['res.partner'].search([
                    '|',
                    ('email', '=', record.student_id.email_id),
                    ('mobile', '=', record.student_id.mobile_no_1)
                ], limit=1)

                if not partner and (record.student_id.email_id or record.student_id.mobile_no_1):
                    # إنشاء partner جديد من بيانات الطالب
                    partner_vals = {
                        'name': record.student_id.full_name,
                        'phone': record.student_id.mobile_no_1,
                        'mobile': record.student_id.mobile_no_2,
                        'is_company': False,
                        'customer_rank': 1,
                    }
                    if record.student_id.email_id:
                        partner_vals['email'] = record.student_id.email_id

                    partner = self.env['res.partner'].create(partner_vals)

                record.partner_id = partner
            else:
                record.partner_id = False

    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    @api.depends('application_program_id')
    def _compute_program_info(self):
        for record in self:
            if record.application_program_id:
                record.program_id = record.application_program_id.program_id
                record.level_ids = record.application_program_id.level_ids
            else:
                record.program_id = False
                record.level_ids = [(5, 0, 0)]  # Clear all

    @api.depends('student_id', 'enrollment_number', 'program_id')
    def _compute_display_name(self):
        for record in self:
            if record.student_id and record.program_id:
                record.display_name = f"{record.enrollment_number} - {record.student_id.full_name} - {record.program_id.display_name}"
            else:
                record.display_name = record.enrollment_number or 'New'

    @api.depends('start_date', 'level_ids')
    def _compute_expected_end_date(self):
        for record in self:
            if not record.start_date:
                record.expected_end_date = False
                continue

            if record.level_ids:
                # للمؤهلات: 3 شهور لكل مستوى
                months = len(record.level_ids) * 3
                record.expected_end_date = record.start_date + relativedelta(months=months)
            else:
                record.expected_end_date = False

    @api.depends('total_amount', 'discount_type', 'discount_percentage', 'discount_amount')
    def _compute_amounts(self):
        for record in self:
            record.subtotal_amount = record.total_amount

            if record.discount_type == 'percentage':
                record.total_discount = (record.total_amount * record.discount_percentage) / 100.0
            elif record.discount_type == 'amount':
                record.total_discount = record.discount_amount
            else:
                record.total_discount = 0.0

            record.final_amount = record.subtotal_amount - record.total_discount

    @api.depends('invoice_ids.amount_residual', 'invoice_ids.state', 'final_amount')
    def _compute_payment_info(self):
        for record in self:
            # حساب المدفوعات من الفواتير المؤكدة
            paid_invoices = record.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            record.amount_paid = sum(paid_invoices.mapped('amount_total')) - sum(
                paid_invoices.mapped('amount_residual'))
            record.amount_remaining = record.final_amount - record.amount_paid
            record.payment_percentage = (record.amount_paid / record.final_amount * 100) if record.final_amount else 0

    @api.onchange('application_program_id')
    def _onchange_application_program_id(self):
        if self.application_program_id:
            self.total_amount = self.application_program_id.total_price

    @api.onchange('discount_type')
    def _onchange_discount_type(self):
        if self.discount_type == 'none':
            self.discount_percentage = 0.0
            self.discount_amount = 0.0
        elif self.discount_type == 'percentage':
            self.discount_amount = 0.0
        elif self.discount_type == 'amount':
            self.discount_percentage = 0.0

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        if self.payment_method == 'cash':
            self.installment_count = 1
        elif self.payment_method == 'installment' and self.installment_count <= 1:
            self.installment_count = 2

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        for record in self:
            if record.discount_type == 'percentage':
                if record.discount_percentage < 0 or record.discount_percentage > 100:
                    raise ValidationError(_('Discount percentage must be between 0 and 100.'))

    @api.constrains('discount_amount')
    def _check_discount_amount(self):
        for record in self:
            if record.discount_type == 'amount':
                if record.discount_amount < 0:
                    raise ValidationError(_('Discount amount cannot be negative.'))
                if record.discount_amount > record.total_amount:
                    raise ValidationError(_('Discount amount cannot exceed total amount.'))

    @api.constrains('installment_count')
    def _check_installment_count(self):
        for record in self:
            if record.payment_method == 'installment' and record.installment_count < 2:
                raise ValidationError(_('Installment plan must have at least 2 installments.'))

    @api.constrains('start_date', 'enrollment_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.enrollment_date:
                if record.start_date < record.enrollment_date:
                    raise ValidationError(_('Start date cannot be before enrollment date.'))

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft enrollments can be confirmed.'))

            # Validate required fields
            if not record.level_ids:
                raise UserError(_('Please select at least one level.'))

            record.state = 'confirmed'

            # Create payment plan if installment method
            if record.payment_method == 'installment' and not record.payment_plan_id:
                record._create_payment_plan()

    def _create_payment_plan(self):
        """Create payment plan"""
        self.ensure_one()

        # Create payment plan
        plan_vals = {
            'enrollment_id': self.id,
            'total_amount': self.final_amount,  # Use final amount after discount
            'installment_count': self.installment_count,
            'payment_frequency': 'monthly',  # Default
        }

        payment_plan = self.env['enrollment.payment.plan'].create(plan_vals)
        self.payment_plan_id = payment_plan
        payment_plan.action_activate()

    def action_create_invoices(self):
        """Create invoices based on payment method"""
        self.ensure_one()

        if self.invoice_count > 0:
            raise UserError(_('Invoices already created for this enrollment.'))

        if self.payment_method == 'cash':
            # إنشاء فاتورة واحدة للدفع الكاش
            self._create_single_invoice()
        else:  # installment
            # إنشاء فواتير متعددة للأقساط
            self._create_installment_invoices()

        # فتح قائمة الفواتير
        return self.action_view_invoices()

    def _create_single_invoice(self):
        """Create single invoice for cash payment"""
        # التحقق من وجود منتج للخدمة التعليمية
        education_product = self._get_education_product()

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'enrollment_id': self.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [],
        }

        # إضافة سطر الفاتورة - سطر لكل مستوى
        for level in self.level_ids:
            line_vals = {
                'product_id': education_product.id,
                'name': f"{self.program_id.display_name} - {level.name}",
                'quantity': 1,
                'price_unit': level.total_price,
            }
            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))

        # Add discount line if applicable
        if self.total_discount > 0:
            discount_product = self._get_discount_product()
            discount_line = {
                'product_id': discount_product.id,
                'name': f"Discount - {self.discount_reason or 'Special Discount'}",
                'quantity': 1,
                'price_unit': -self.total_discount,  # Negative amount for discount
            }
            invoice_vals['invoice_line_ids'].append((0, 0, discount_line))

        invoice = self.env['account.move'].create(invoice_vals)
        return invoice

    def _create_installment_invoices(self):
        """Create multiple invoices for installments"""
        if not self.payment_plan_id:
            raise UserError(_('Please create payment plan first.'))

        if not self.installment_ids:
            raise UserError(_('No installments found. Please check payment plan.'))

        education_product = self._get_education_product()

        for installment in self.installment_ids:
            # إنشاء فاتورة لكل قسط
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.partner_id.id,
                'enrollment_id': self.id,
                'installment_id': installment.id,
                'invoice_date': installment.due_date,
                'invoice_date_due': installment.due_date,
                'invoice_line_ids': [(0, 0, {
                    'product_id': education_product.id,
                    'name': f"{self.program_id.display_name} - Installment {installment.sequence}",
                    'quantity': 1,
                    'price_unit': installment.amount,
                })],
            }

            invoice = self.env['account.move'].create(invoice_vals)

            # ربط الفاتورة بالقسط
            installment.invoice_id = invoice

    def _get_education_product(self):
        """Get or create education service product"""
        product = self.env['product.product'].search([
            ('default_code', '=', 'EDUCATION_SERVICE')
        ], limit=1)

        if not product:
            product = self.env['product.product'].create({
                'name': 'Education Service',
                'default_code': 'EDUCATION_SERVICE',
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
                'list_price': 0.0,
                'taxes_id': [(5, 0, 0)],  # Remove default taxes
            })

        return product

    def _get_discount_product(self):
        """Get or create discount product"""
        product = self.env['product.product'].search([
            ('default_code', '=', 'EDUCATION_DISCOUNT')
        ], limit=1)

        if not product:
            product = self.env['product.product'].create({
                'name': 'Education Discount',
                'default_code': 'EDUCATION_DISCOUNT',
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
                'list_price': 0.0,
                'taxes_id': [(5, 0, 0)],  # Remove default taxes
            })

        return product

    def action_activate(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Only confirmed enrollments can be activated.'))
            record.state = 'active'

    def action_suspend(self):
        for record in self:
            if record.state != 'active':
                raise UserError(_('Only active enrollments can be suspended.'))
            record.state = 'suspended'

    def action_resume(self):
        for record in self:
            if record.state != 'suspended':
                raise UserError(_('Only suspended enrollments can be resumed.'))
            record.state = 'active'

    def action_complete(self):
        for record in self:
            if record.state not in ['active', 'suspended']:
                raise UserError(_('Only active or suspended enrollments can be completed.'))

            # Check if all payments are made
            if record.amount_remaining > 0:
                raise UserError(_('Cannot complete enrollment with pending payments. Remaining amount: %s %s') %
                                (record.amount_remaining, record.currency_id.symbol))

            record.state = 'completed'
            record.actual_end_date = fields.Date.today()

    def action_cancel(self):
        for record in self:
            if record.state in ['completed', 'cancelled']:
                raise UserError(_('Cannot cancel completed or already cancelled enrollments.'))
            record.state = 'cancelled'

    def action_view_invoices(self):
        """View related invoices"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('enrollment_id', '=', self.id)],
            'context': {
                'default_enrollment_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_move_type': 'out_invoice',
            }
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'enrollment.payment',
            'view_mode': 'list,form',
            'domain': [('enrollment_id', '=', self.id)],
            'context': {'default_enrollment_id': self.id}
        }

    def action_view_installments(self):
        self.ensure_one()
        return {
            'name': _('Installments'),
            'type': 'ir.actions.act_window',
            'res_model': 'enrollment.installment',
            'view_mode': 'list,form',
            'domain': [('enrollment_id', '=', self.id)],
            'context': {'default_enrollment_id': self.id}
        }

    @api.depends('installment_ids.state', 'installment_ids.due_date')
    def _compute_has_overdue(self):
        today = fields.Date.today()
        for record in self:
            overdue_installments = record.installment_ids.filtered(
                lambda i: i.state == 'pending' and i.due_date < today
            )
            record.has_overdue = bool(overdue_installments)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ربط الفاتورة بالـ Enrollment
    enrollment_id = fields.Many2one('hallway.enrollment', string='Enrollment',
                                    readonly=True, ondelete='restrict')
    installment_id = fields.Many2one('enrollment.installment', string='Installment',
                                     readonly=True, ondelete='restrict')

    @api.depends('amount_residual', 'move_type', 'state', 'payment_state')
    def _compute_payment_state(self):
        """Override to update installment status when invoice is paid"""
        res = super()._compute_payment_state()

        for move in self:
            if move.installment_id and move.payment_state == 'paid':
                # تحديث حالة القسط عند دفع الفاتورة
                move.installment_id.write({
                    'state': 'paid',
                    'payment_date': fields.Date.today(),
                })

        return res