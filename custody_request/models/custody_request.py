from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CustodyRequest(models.Model):
    _name = 'custody.request'
    _description = 'Custody Request'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Recipient',
        required=True,
        tracking=True,
        help='Person receiving the custody'
    )

    amount = fields.Float(
        string='Amount',
        required=True,
        tracking=True,
        help='Custody amount'
    )

    date = fields.Date(
        string='Receipt Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date when the amount was received'
    )

    reason = fields.Text(
        string='Reason',
        required=True,
        tracking=True,
        help='Reason for custody request'
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        tracking=True,
        help='Department for this custody request'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_approval', 'In Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, readonly=True)

    current_approval_step = fields.Integer(
        string='Current Approval Step',
        default=0,
        readonly=True,
        help='Current position in approval workflow'
    )

    approval_line_ids = fields.One2many(
        'custody.approval.line',
        'request_id',
        string='Approval History',
        readonly=True
    )

    approval_count = fields.Integer(
        string='Approval Count',
        compute='_compute_approval_count'
    )

    can_approve = fields.Boolean(
        string='Can Approve',
        compute='_compute_can_approve',
        help='Whether current user can approve this request'
    )

    next_approvers = fields.Char(
        string='Next Approvers',
        compute='_compute_next_approvers',
        help='Users who need to approve next'
    )

    @api.depends('approval_line_ids')
    def _compute_approval_count(self):
        for record in self:
            record.approval_count = len(record.approval_line_ids)

    @api.depends('state', 'current_approval_step', 'company_id', 'department_id')
    def _compute_can_approve(self):
        for record in self:
            record.can_approve = False
            if record.state == 'in_approval':
                # Get all configs for this department, ordered by sequence
                configs = self.env['custody.approval.config'].search([
                    ('company_id', '=', record.company_id.id),
                    ('department_id', '=', record.department_id.id)
                ], order='sequence')

                # Find the next config after current step
                next_config = False
                for config in configs:
                    if config.sequence > record.current_approval_step:
                        next_config = config
                        break

                if next_config and self.env.user in next_config.user_ids:
                    record.can_approve = True

    @api.depends('state', 'current_approval_step', 'company_id', 'department_id')
    def _compute_next_approvers(self):
        for record in self:
            if record.state in ['in_approval', 'submitted']:
                # Get all configs for this department, ordered by sequence
                configs = self.env['custody.approval.config'].search([
                    ('company_id', '=', record.company_id.id),
                    ('department_id', '=', record.department_id.id)
                ], order='sequence')

                # Find the next config after current step
                next_config = False
                for config in configs:
                    if config.sequence > record.current_approval_step:
                        next_config = config
                        break

                if next_config:
                    record.next_approvers = ', '.join(next_config.user_ids.mapped('name'))
                else:
                    record.next_approvers = 'No more approvals needed'
            else:
                record.next_approvers = ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Get company from vals or use current company
                company_id = vals.get('company_id', self.env.company.id)
                # Generate sequence based on company
                IrSequence = self.env['ir.sequence'].with_context(force_company=company_id)
                vals['name'] = IrSequence.next_by_code('custody.request') or 'New'
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError('Amount must be greater than zero!')

    def action_submit(self):
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError('Only draft requests can be submitted!')

        # Check if approval configs exist for this company and department
        configs = self.env['custody.approval.config'].search([
            ('company_id', '=', self.company_id.id),
            ('department_id', '=', self.department_id.id)
        ], order='sequence')

        if not configs:
            raise ValidationError(f'No approval configuration found for department {self.department_id.name}!')

        self.write({
            'state': 'in_approval',
            'current_approval_step': 0
        })

        # Create approval history
        self._create_approval_history()

        # Send notification to first approvers
        self._notify_approvers()

    def action_approve(self):
        self.ensure_one()
        if not self.can_approve:
            raise ValidationError('You are not authorized to approve at this stage!')

        # Get configs for THIS department ONLY
        configs = self.env['custody.approval.config'].search([
            ('company_id', '=', self.company_id.id),
            ('department_id', '=', self.department_id.id)
        ], order='sequence')

        # Find current config
        current_config = False
        for config in configs:
            if config.sequence > self.current_approval_step:
                current_config = config
                break

        if not current_config:
            raise ValidationError('No approval configuration found!')

        # Update approval line
        approval_line = self.approval_line_ids.filtered(
            lambda l: l.sequence == current_config.sequence and l.status == 'pending'
        )
        if approval_line:
            approval_line.write({
                'status': 'approved',
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now()
            })

        # Update current step
        self.current_approval_step = current_config.sequence

        # Check if there are more steps FOR THIS DEPARTMENT
        next_config = False
        for config in configs:
            if config.sequence > current_config.sequence:
                next_config = config
                break

        if next_config:
            # More approvals needed
            self._notify_approvers()
            self.message_post(
                body=f"Approved by {self.env.user.name}. Next approval: {next_config.name}"
            )
        else:
            # All approvals done
            self.state = 'approved'
            self.message_post(
                body=f"Request fully approved. Last approval by {self.env.user.name}"
            )

    def action_reject(self):
        self.ensure_one()
        if not self.can_approve:
            raise ValidationError('You are not authorized to reject at this stage!')

        # Get configs for THIS department ONLY
        configs = self.env['custody.approval.config'].search([
            ('company_id', '=', self.company_id.id),
            ('department_id', '=', self.department_id.id)
        ], order='sequence')

        # Find current config
        current_config = False
        for config in configs:
            if config.sequence > self.current_approval_step:
                current_config = config
                break

        if current_config:
            # Update approval line
            approval_line = self.approval_line_ids.filtered(
                lambda l: l.sequence == current_config.sequence and l.status == 'pending'
            )
            if approval_line:
                approval_line.write({
                    'status': 'rejected',
                    'approved_by': self.env.user.id,
                    'approval_date': fields.Datetime.now()
                })

        self.state = 'rejected'
        self.message_post(
            body=f"Request rejected by {self.env.user.name}"
        )

    def action_cancel(self):
        self.ensure_one()
        if self.state in ['approved', 'rejected']:
            raise ValidationError('Cannot cancel approved or rejected requests!')
        self.state = 'cancelled'

    def action_reset_to_draft(self):
        self.ensure_one()
        if self.state not in ['cancelled', 'rejected']:
            raise ValidationError('Only cancelled or rejected requests can be reset!')

        # Clear approval history
        self.approval_line_ids.unlink()

        self.write({
            'state': 'draft',
            'current_approval_step': 0
        })

    def action_view_approval_history(self):
        """Open approval history in a popup"""
        self.ensure_one()
        return {
            'name': 'Approval History',
            'type': 'ir.actions.act_window',
            'res_model': 'custody.approval.line',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {'create': False, 'edit': False, 'delete': False},
            'target': 'new',
        }

    def _create_approval_history(self):
        """Create approval lines based on department configuration"""
        if not self.department_id:
            raise ValidationError('Department is required!')

        # Get configs for the selected department ONLY
        configs = self.env['custody.approval.config'].search([
            ('company_id', '=', self.company_id.id),
            ('department_id', '=', self.department_id.id)
        ], order='sequence')

        # Log for debugging
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"\n=== Creating approval history ===")
        _logger.info(f"Request department: {self.department_id.name} (ID: {self.department_id.id})")
        _logger.info(f"Company: {self.company_id.name} (ID: {self.company_id.id})")
        _logger.info(f"Found {len(configs)} approval stages")

        if not configs:
            raise ValidationError(f'No approval configuration found for department: {self.department_id.name}')

        for config in configs:
            _logger.info(f"Creating line for config: {config.name}")
            _logger.info(f"  - Config Dept: {config.department_id.name} (ID: {config.department_id.id})")
            _logger.info(f"  - Config Users: {config.user_ids.mapped('name')}")

            vals = {
                'request_id': self.id,
                'sequence': config.sequence,
                'stage_name': config.name,
                'required_users': ', '.join(config.user_ids.mapped('name')),
                'status': 'pending'
            }
            self.env['custody.approval.line'].create(vals)
            _logger.info(f"Created approval line: Seq {config.sequence} - {config.name}")

    def _notify_approvers(self):
        """Send notification to next approvers based on department"""
        # Get configs for the selected department ONLY
        configs = self.env['custody.approval.config'].search([
            ('company_id', '=', self.company_id.id),
            ('department_id', '=', self.department_id.id)
        ], order='sequence')

        # Find next config
        next_config = False
        for config in configs:
            if config.sequence > self.current_approval_step:
                next_config = config
                break

        if next_config:
            # Send notification to approvers
            for user in next_config.user_ids:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=f'Custody Request Approval Required - {self.partner_id.name} ({self.department_id.name})'
                )


class CustodyApprovalLine(models.Model):
    _name = 'custody.approval.line'
    _description = 'Custody Approval Line'
    _order = 'sequence'

    request_id = fields.Many2one(
        'custody.request',
        string='Request',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(
        string='Sequence',
        required=True
    )

    stage_name = fields.Char(
        string='Stage',
        required=True
    )

    required_users = fields.Char(
        string='Required Approvers'
    )

    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='pending', required=True)

    approved_by = fields.Many2one(
        'res.users',
        string='Approved/Rejected By'
    )

    approval_date = fields.Datetime(
        string='Approval Date'
    )

    comments = fields.Text(
        string='Comments'
    )