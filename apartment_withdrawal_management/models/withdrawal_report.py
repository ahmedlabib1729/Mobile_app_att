# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WithdrawalReport(models.TransientModel):
    _name = 'withdrawal.report'
    _description = 'Apartment Withdrawal Report'

    # Report Filters
    date_from = fields.Date(
        string='From Date',
        required=True,
        default=fields.Date.today().replace(day=1)  # First day of current month
    )

    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.today()
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help="Filter by specific partner"
    )

    building_id = fields.Many2one(
        'building',
        string='Building',
        help="Filter by specific building"
    )

    status = fields.Selection([
        ('all', 'All'),
        ('monitoring', 'Monitoring'),
        ('warning_sent', 'Warning Sent'),
        ('withdrawn', 'Withdrawn'),
        ('restored', 'Restored'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='all')

    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('statistics', 'Statistics Report')
    ], string='Report Type', default='summary', required=True)

    # Report Results
    report_data = fields.Binary('Report File', readonly=True)
    report_name = fields.Char('Report Name', readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError(_("From Date must be before To Date."))

    def action_generate_report(self):
        """Generate the withdrawal report"""
        self.ensure_one()

        # Build domain for search
        domain = []

        # Date filters
        if self.date_from:
            domain.append(('withdrawal_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('withdrawal_date', '<=', self.date_to))

        # Partner filter
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))

        # Building filter
        if self.building_id:
            domain.append(('building_id', '=', self.building_id.id))

        # Status filter
        if self.status != 'all':
            domain.append(('status', '=', self.status))

        # Get withdrawal monitor records
        withdrawal_records = self.env['withdrawal.monitor'].search(domain)

        if not withdrawal_records:
            raise UserError(_("No records found for the selected criteria."))

        # Generate different report types
        if self.report_type == 'summary':
            return self._generate_summary_report(withdrawal_records)
        elif self.report_type == 'detailed':
            return self._generate_detailed_report(withdrawal_records)
        elif self.report_type == 'statistics':
            return self._generate_statistics_report(withdrawal_records)

    def _generate_summary_report(self, records):
        """Generate summary report"""
        # Group by status
        summary_data = {}
        total_overdue_amount = 0

        for record in records:
            status = record.status
            if status not in summary_data:
                summary_data[status] = {
                    'count': 0,
                    'total_amount': 0,
                    'records': []
                }

            summary_data[status]['count'] += 1
            summary_data[status]['total_amount'] += record.overdue_amount
            summary_data[status]['records'].append(record)
            total_overdue_amount += record.overdue_amount

        # Return tree view with summary
        return {
            'name': _('Withdrawal Summary Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', records.ids)],
            'context': {
                'search_default_group_by_status': 1,
                'summary_data': summary_data,
                'total_overdue_amount': total_overdue_amount,
            },
            'target': 'current',
        }

    def _generate_detailed_report(self, records):
        """Generate detailed report"""
        return {
            'name': _('Withdrawal Detailed Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.monitor',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', records.ids)],
            'context': {
                'detailed_view': True,
            },
            'target': 'current',
        }

    def _generate_statistics_report(self, records):
        """Generate statistics report"""
        # Calculate statistics
        total_records = len(records)

        if total_records == 0:
            raise UserError(_("No data available for statistics."))

        stats = {
            'total_withdrawals': len(records.filtered(lambda r: r.status == 'withdrawn')),
            'total_restorations': len(records.filtered(lambda r: r.status == 'restored')),
            'total_monitoring': len(records.filtered(lambda r: r.status == 'monitoring')),
            'total_warnings': len(records.filtered(lambda r: r.status == 'warning_sent')),
            'total_overdue_amount': sum(records.mapped('overdue_amount')),
            'average_overdue_months': sum(records.mapped('overdue_months')) / total_records if total_records else 0,
        }

        # Calculate restoration rate
        withdrawn_count = stats['total_withdrawals'] + stats['total_restorations']
        stats['restoration_rate'] = (stats['total_restorations'] / withdrawn_count * 100) if withdrawn_count else 0

        # Return action to show statistics
        return {
            'name': _('Withdrawal Statistics'),
            'type': 'ir.actions.act_window',
            'res_model': 'withdrawal.report.statistics',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_statistics_data': str(stats),
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
            }
        }


class WithdrawalReportStatistics(models.TransientModel):
    _name = 'withdrawal.report.statistics'
    _description = 'Withdrawal Statistics Display'

    date_from = fields.Date('From Date', readonly=True)
    date_to = fields.Date('To Date', readonly=True)

    total_withdrawals = fields.Integer('Total Withdrawals', readonly=True)
    total_restorations = fields.Integer('Total Restorations', readonly=True)
    total_monitoring = fields.Integer('Currently Monitoring', readonly=True)
    total_warnings = fields.Integer('Warnings Sent', readonly=True)

    total_overdue_amount = fields.Float('Total Overdue Amount', readonly=True, digits='Product Price')
    average_overdue_months = fields.Float('Average Overdue Months', readonly=True, digits=(12, 1))
    restoration_rate = fields.Float('Restoration Rate (%)', readonly=True, digits=(12, 1))

    statistics_data = fields.Text('Statistics Data', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Parse statistics data from context
        stats_str = self._context.get('default_statistics_data', '{}')
        try:
            stats = eval(stats_str)  # Safe since we control the data
            res.update({
                'total_withdrawals': stats.get('total_withdrawals', 0),
                'total_restorations': stats.get('total_restorations', 0),
                'total_monitoring': stats.get('total_monitoring', 0),
                'total_warnings': stats.get('total_warnings', 0),
                'total_overdue_amount': stats.get('total_overdue_amount', 0),
                'average_overdue_months': stats.get('average_overdue_months', 0),
                'restoration_rate': stats.get('restoration_rate', 0),
            })
        except:
            pass

        return res