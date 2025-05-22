from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_mobile_app_access = fields.Boolean(
        string="السماح بالوصول من التطبيق المحمول",
        config_parameter='hr_mobile_app.allow_mobile_app_access',
        default=False,
        help="تمكين الموظفين من استخدام التطبيق المحمول للوصول إلى Odoo"
    )
