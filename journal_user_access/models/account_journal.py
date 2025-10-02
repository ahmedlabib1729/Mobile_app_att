from odoo import models, fields, api, _
from odoo.exceptions import AccessError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    allowed_user_ids = fields.Many2many(
        'res.users',
        'journal_users_rel',
        'journal_id',
        'user_id',
        string='Allowed Users',
        domain=[('share', '=', False)],
        help='Leave empty to allow all users'
    )

    restrict_access = fields.Boolean(
        string='Restrict Access',
        default=False,
        help='When enabled, only selected users can view this journal'
    )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Allow reading journals for selection purposes (dropdowns, etc)
        but apply restrictions when actually using them"""

        # في حالة القراءة للـ dropdowns والـ many2one، نسمح بالوصول
        # بس لما يحاول يستخدم الـ journal فعلياً، الـ rules هتطبق
        if self.env.context.get('journal_selection_mode'):
            return super(AccountJournal, self.sudo()).search_read(
                domain=domain, fields=fields, offset=offset, limit=limit, order=order
            )

        return super().search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

    def check_access_rule(self, operation):
        """Override to add detailed access check with better error message"""
        # نسمح للـ superuser دايماً
        if self.env.su:
            return super().check_access_rule(operation)

        # في حالة القراءة البسيطة للـ selection، نسمح
        if operation == 'read' and self.env.context.get('journal_selection_mode'):
            return

        super().check_access_rule(operation)

        # فقط للعمليات read/write على البيانات الفعلية
        if operation in ('read', 'write'):
            for journal in self:
                if journal.restrict_access:
                    # مدير الحسابات يمر مباشرة
                    if self.env.user.has_group('account.group_account_manager'):
                        continue

                    # تحقق من المستخدم المسموح
                    if self.env.user not in journal.allowed_user_ids:
                        raise AccessError(
                            _("⚠️ Access Denied\n\n"
                              "You don't have permission to access journal: %(name)s\n\n"
                              "📝 Details:\n"
                              "• Journal: %(name)s\n"
                              "• Type: %(type)s\n"
                              "• Company: %(company)s\n\n"
                              "💡 Solution:\n"
                              "Please contact your system administrator or accounting manager\n"
                              "to request access to this journal.") % {
                                'name': journal.name,
                                'type': dict(journal._fields['type'].selection).get(journal.type, journal.type),
                                'company': journal.company_id.name
                            }
                        )


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _search_default_journal(self, journal_types):
        """Override to allow searching journals with context"""
        return super(
            AccountMove,
            self.with_context(journal_selection_mode=True)
        )._search_default_journal(journal_types)

    @api.model
    def default_get(self, fields_list):
        """Override to allow reading journals for default values"""
        # نستخدم sudo() بس لقراءة الـ journals في الـ defaults
        res = super(AccountMove, self.sudo()).default_get(fields_list)
        return res

    def _get_default_journal(self):
        """Override to show available journals only"""
        journals = self.env['account.journal'].search([
            '|',
            ('restrict_access', '=', False),
            ('allowed_user_ids', 'in', self.env.user.id)
        ])

        if journals:
            return journals[0]

        # Fallback to sudo if no journals available
        return self.env['account.journal'].sudo().search([], limit=1)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def default_get(self, fields_list):
        """Override to allow reading journals for payment defaults"""
        return super(
            AccountPayment,
            self.with_context(journal_selection_mode=True)
        ).default_get(fields_list)

    @api.model
    def _get_available_journals(self):
        """Override to show all journals in payment dropdown,
        but restrict actual usage based on rules"""
        # نسمح برؤية كل الـ journals في الـ dropdown
        domain = [('type', 'in', ('bank', 'cash'))]

        # لو مش مدير، نطبق القيود
        if not self.env.user.has_group('account.group_account_manager'):
            domain = [
                ('type', 'in', ('bank', 'cash')),
                '|',
                ('restrict_access', '=', False),
                ('allowed_user_ids', 'in', self.env.user.id)
            ]

        return self.env['account.journal'].sudo().search(domain)

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Check if user has access to selected journal"""
        res = super()._onchange_journal_id()

        if self.journal_id and self.journal_id.restrict_access:
            if not self.env.user.has_group('account.group_account_manager'):
                if self.env.user not in self.journal_id.allowed_user_ids:
                    return {
                        'warning': {
                            'title': 'Access Denied',
                            'message': f'You don\'t have permission to use journal: {self.journal_id.name}'
                        }
                    }
        return res