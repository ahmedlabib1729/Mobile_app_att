from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Student(models.Model):
    _inherit = 'hallway.student'

    # Portal User
    user_id = fields.Many2one('res.users', string='Portal User', readonly=True)
    has_portal_access = fields.Boolean(string='Has Portal Access', compute='_compute_has_portal_access')

    @api.depends('user_id')
    def _compute_has_portal_access(self):
        for record in self:
            record.has_portal_access = bool(record.user_id)

    def action_create_portal_user(self):
        """Create portal user for student"""
        self.ensure_one()

        if self.user_id:
            raise UserError(_('This student already has a portal user!'))

        if not self.email_id:
            raise UserError(_('Please set an email for the student before creating portal access.'))

        # Check if user with this email exists
        existing_user = self.env['res.users'].sudo().search([('login', '=', self.email_id)], limit=1)
        if existing_user:
            raise UserError(_('A user with this email already exists!'))

        # Create portal user
        portal_group = self.env.ref('base.group_portal')
        user_vals = {
            'name': self.full_name,
            'login': self.email_id,
            'email': self.email_id,
            'partner_id': self.partner_id.id,
            'groups_id': [(6, 0, [portal_group.id])],
            'password': 'Welcome123!',  # Default password - should be changed
        }

        user = self.env['res.users'].sudo().create(user_vals)
        self.user_id = user

        # Send welcome email with credentials
        template = self.env.ref('HallWay_System.email_template_portal_welcome', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Portal access created successfully! Default password: Welcome123!'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_disable_portal_access(self):
        """Disable portal access"""
        self.ensure_one()
        if self.user_id:
            self.user_id.active = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Portal access disabled successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_enable_portal_access(self):
        """Enable portal access"""
        self.ensure_one()
        if self.user_id:
            self.user_id.active = True
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Portal access enabled successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }