# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class HrMobileAppSettings(models.TransientModel):
    _name = 'hr.mobile.app.settings'
    _description = 'Employee Mobile App Settings'

    name = fields.Char(default='Mobile App Settings')
    allow_mobile_app_access = fields.Boolean(
        string="Enable App Access",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.allow_mobile_app_access',
                                                                              'False').lower() == 'true',
        help="Enable employees to use the mobile app"
    )
    mobile_service_username = fields.Char(
        string="Service Username",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.service_username',
                                                                              'mobile_app_service'),
        help="Shared username for server connection"
    )
    mobile_service_password = fields.Char(
        string="Service Password",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.service_password', ''),
        help="Shared user password (should be changed regularly)"
    )
    api_base_url = fields.Char(
        string="API Server URL",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.api_base_url', ''),
        help="Base URL for Odoo server (example: https://your-odoo-server.com)"
    )
    api_database = fields.Char(
        string="Database Name",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.api_database',
                                                                              self.env.cr.dbname),
        help="Odoo database name to connect to"
    )

    def execute(self):
        """Save settings"""
        # Validate input
        if self.mobile_service_password and len(self.mobile_service_password) < 3:
            raise ValidationError(_('Password must be at least 8 characters long'))

        # Save settings to system parameters
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('hr_mobile_app.allow_mobile_app_access', str(self.allow_mobile_app_access))
        params.set_param('hr_mobile_app.service_username', self.mobile_service_username or 'mobile_app_service')

        if self.mobile_service_password:
            params.set_param('hr_mobile_app.service_password', self.mobile_service_password)

        params.set_param('hr_mobile_app.api_base_url', self.api_base_url or '')
        params.set_param('hr_mobile_app.api_database', self.api_database or self.env.cr.dbname)

        # Update shared user if data has changed
        if self.mobile_service_username or self.mobile_service_password:
            service_user = self.env['res.users'].sudo().search([('login', '=', 'mobile_app_service')], limit=1)

            if service_user:
                # Update existing user data
                update_vals = {}

                if self.mobile_service_username:
                    update_vals['login'] = self.mobile_service_username
                    update_vals['name'] = f"Mobile App Service ({self.mobile_service_username})"

                if self.mobile_service_password:
                    update_vals['password'] = self.mobile_service_password

                if update_vals:
                    service_user.write(update_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Saved'),
                'message': _('Mobile app settings saved successfully.'),
                'sticky': False,
                'type': 'success',
            }
        }