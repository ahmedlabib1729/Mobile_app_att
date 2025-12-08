/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { Component, useState, onWillStart } = owl;

export class BalanceSheetReport extends Component {
    static template = "accounting_reports.BalanceSheet";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            // Report Data
            reportData: { sections: {}, summary: {} },

            // Expanded states
            expandedSections: {
                current_assets: true,
                non_current_assets: true,
                current_liabilities: true,
                non_current_liabilities: true,
                equity: true,
            },

            // Filters
            asOfDate: this.getTodayDate(),
            postedOnly: true,
            comparison: false,
            comparisonDate: this.getLastYearEnd(),

            // UI
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadReportData();
        });
    }

    // ==================== DATE HELPERS ====================

    getTodayDate() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    }

    getLastYearEnd() {
        const now = new Date();
        return `${now.getFullYear() - 1}-12-31`;
    }

    // ==================== DATA LOADING ====================

    async loadReportData() {
        this.state.isLoading = true;
        try {
            const data = await this.orm.call(
                'report.balance.sheet',
                'get_report_data',
                [],
                {
                    as_of_date: this.state.asOfDate,
                    posted_only: this.state.postedOnly,
                    comparison: this.state.comparison,
                    comparison_date: this.state.comparison ? this.state.comparisonDate : false,
                }
            );

            this.state.reportData = data;
        } catch (error) {
            console.error("Error loading report data:", error);
        }
        this.state.isLoading = false;
    }

    // ==================== FORMATTING ====================

    formatNumber(num) {
        return (num || 0).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    formatChange(num) {
        if (num > 0) return '+' + this.formatNumber(num);
        return this.formatNumber(num);
    }

    formatChangePercent(num) {
        const formatted = (num || 0).toFixed(1) + '%';
        if (num > 0) return '+' + formatted;
        return formatted;
    }

    // ==================== EXPAND/COLLAPSE ====================

    toggleSection(sectionKey) {
        this.state.expandedSections[sectionKey] = !this.state.expandedSections[sectionKey];
    }

    isSectionExpanded(sectionKey) {
        return this.state.expandedSections[sectionKey] || false;
    }

    expandAll() {
        this.state.expandedSections = {
            current_assets: true,
            non_current_assets: true,
            current_liabilities: true,
            non_current_liabilities: true,
            equity: true,
        };
    }

    collapseAll() {
        this.state.expandedSections = {
            current_assets: false,
            non_current_assets: false,
            current_liabilities: false,
            non_current_liabilities: false,
            equity: false,
        };
    }

    // ==================== FILTER HANDLERS ====================

    async onChangeAsOfDate(ev) {
        this.state.asOfDate = ev.target.value;
        await this.loadReportData();
    }

    async onChangeComparisonDate(ev) {
        this.state.comparisonDate = ev.target.value;
        if (this.state.comparison) {
            await this.loadReportData();
        }
    }

    async onChangePostedOnly(ev) {
        this.state.postedOnly = ev.target.checked;
        await this.loadReportData();
    }

    async onChangeComparison(ev) {
        this.state.comparison = ev.target.checked;
        await this.loadReportData();
    }

    async setQuickDate(period) {
        const now = new Date();
        const year = now.getFullYear();

        switch(period) {
            case 'today':
                this.state.asOfDate = this.getTodayDate();
                break;
            case 'month_end':
                const lastDayMonth = new Date(year, now.getMonth() + 1, 0);
                this.state.asOfDate = `${year}-${String(now.getMonth() + 1).padStart(2, '0')}-${lastDayMonth.getDate()}`;
                break;
            case 'quarter_end':
                const quarter = Math.floor(now.getMonth() / 3);
                const quarterEndMonth = (quarter + 1) * 3;
                const lastDayQuarter = new Date(year, quarterEndMonth, 0);
                this.state.asOfDate = `${year}-${String(quarterEndMonth).padStart(2, '0')}-${lastDayQuarter.getDate()}`;
                break;
            case 'year_end':
                this.state.asOfDate = `${year}-12-31`;
                break;
            case 'last_year_end':
                this.state.asOfDate = `${year - 1}-12-31`;
                break;
        }
        await this.loadReportData();
    }

    // ==================== ACTIONS ====================

    async onRefresh() {
        await this.loadReportData();
    }

    onExportExcel() {
        const sections = this.state.reportData.sections || {};
        const summary = this.state.reportData.summary || {};
        
        let csv = 'Section,Account Code,Account Name,Balance';
        if (this.state.comparison) {
            csv += ',Comparison,Change,Change %';
        }
        csv += '\n';

        // Assets
        csv += '\n=== ASSETS ===\n';
        
        csv += '\nCURRENT ASSETS\n';
        for (const acc of sections.current_assets?.accounts || []) {
            csv += `"Current Assets","${acc.code}","${acc.name}",${acc.balance}`;
            if (this.state.comparison) {
                csv += `,${acc.comp_balance},${acc.change},${acc.change_percent.toFixed(1)}%`;
            }
            csv += '\n';
        }
        csv += `"","","Total Current Assets",${sections.current_assets?.total || 0}\n`;

        csv += '\nNON-CURRENT ASSETS\n';
        for (const acc of sections.non_current_assets?.accounts || []) {
            csv += `"Non-Current Assets","${acc.code}","${acc.name}",${acc.balance}`;
            if (this.state.comparison) {
                csv += `,${acc.comp_balance},${acc.change},${acc.change_percent.toFixed(1)}%`;
            }
            csv += '\n';
        }
        csv += `"","","Total Non-Current Assets",${sections.non_current_assets?.total || 0}\n`;

        csv += `\n"","","TOTAL ASSETS",${summary.total_assets || 0}\n`;

        // Liabilities
        csv += '\n=== LIABILITIES ===\n';
        
        csv += '\nCURRENT LIABILITIES\n';
        for (const acc of sections.current_liabilities?.accounts || []) {
            csv += `"Current Liabilities","${acc.code}","${acc.name}",${acc.balance}`;
            if (this.state.comparison) {
                csv += `,${acc.comp_balance},${acc.change},${acc.change_percent.toFixed(1)}%`;
            }
            csv += '\n';
        }
        csv += `"","","Total Current Liabilities",${sections.current_liabilities?.total || 0}\n`;

        csv += '\nNON-CURRENT LIABILITIES\n';
        for (const acc of sections.non_current_liabilities?.accounts || []) {
            csv += `"Non-Current Liabilities","${acc.code}","${acc.name}",${acc.balance}`;
            if (this.state.comparison) {
                csv += `,${acc.comp_balance},${acc.change},${acc.change_percent.toFixed(1)}%`;
            }
            csv += '\n';
        }
        csv += `"","","Total Non-Current Liabilities",${sections.non_current_liabilities?.total || 0}\n`;

        csv += `\n"","","TOTAL LIABILITIES",${summary.total_liabilities || 0}\n`;

        // Equity
        csv += '\n=== EQUITY ===\n';
        for (const acc of sections.equity?.accounts || []) {
            csv += `"Equity","${acc.code}","${acc.name}",${acc.balance}`;
            if (this.state.comparison) {
                csv += `,${acc.comp_balance},${acc.change},${acc.change_percent.toFixed(1)}%`;
            }
            csv += '\n';
        }
        csv += `"","","TOTAL EQUITY",${summary.total_equity || 0}\n`;

        csv += `\n"","","TOTAL LIABILITIES & EQUITY",${summary.total_liabilities_equity || 0}\n`;

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `balance_sheet_${this.state.asOfDate}.csv`;
        link.click();
    }

    onPrint() {
        window.print();
    }

    // ==================== NAVIGATION ====================

    openAccount(accountId) {
        if (!accountId) return; // Skip for retained earnings
        
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "general_ledger_report",
            name: _t("General Ledger"),
            context: {
                default_account_ids: [accountId],
                date_to: this.state.asOfDate,
            },
        });
    }

    // ==================== HELPERS ====================

    getChangeClass(change) {
        if (change > 0) return 'change-positive';
        if (change < 0) return 'change-negative';
        return '';
    }

    getSectionClass(sectionKey) {
        const section = this.state.reportData.sections?.[sectionKey];
        if (!section) return '';
        return `section-${section.category}`;
    }

    getAccountTypeLabel(accountType) {
        const labels = {
            'asset_receivable': 'Receivable',
            'asset_cash': 'Cash',
            'asset_current': 'Current',
            'asset_non_current': 'Non-Current',
            'asset_prepayments': 'Prepaid',
            'asset_fixed': 'Fixed',
            'liability_payable': 'Payable',
            'liability_credit_card': 'Credit Card',
            'liability_current': 'Current',
            'liability_non_current': 'Non-Current',
            'equity': 'Equity',
            'equity_unaffected': 'Unaffected',
            'retained_earnings': 'Retained',
        };
        return labels[accountType] || accountType;
    }

    getAccountTypeBadgeClass(accountType) {
        if (accountType.startsWith('asset')) return 'badge-asset';
        if (accountType.startsWith('liability')) return 'badge-liability';
        return 'badge-equity';
    }
}

BalanceSheetReport.template = "accounting_reports.BalanceSheet";
registry.category("actions").add("balance_sheet_report", BalanceSheetReport);
