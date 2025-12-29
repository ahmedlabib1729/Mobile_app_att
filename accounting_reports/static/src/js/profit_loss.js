/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { Component, useState, onWillStart } = owl;

export class ProfitLossReport extends Component {
    static template = "accounting_reports.ProfitLoss";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            // Report Data
            reportData: { sections: {}, summary: {} },

            // Expanded states
            expandedSections: {
                operating_income: true,
                cost_of_revenue: true,
                operating_expenses: true,
                other_income: true,
            },

            // Filters
            dateFrom: this.getFirstDayOfYear(),
            dateTo: this.getTodayDate(),
            postedOnly: true,
            comparison: false,
            comparisonType: 'previous_period',

            // UI
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadReportData();
        });
    }

    // ==================== DATE HELPERS ====================

    getFirstDayOfYear() {
        const now = new Date();
        return `${now.getFullYear()}-01-01`;
    }

    getTodayDate() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    }

    // ==================== DATA LOADING ====================

    async loadReportData() {
        this.state.isLoading = true;
        try {
            const data = await this.orm.call(
                'report.profit.loss',
                'get_report_data',
                [],
                {
                    date_from: this.state.dateFrom,
                    date_to: this.state.dateTo,
                    posted_only: this.state.postedOnly,
                    comparison: this.state.comparison,
                    comparison_type: this.state.comparisonType,
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

    formatPercent(num) {
        return (num || 0).toFixed(1) + '%';
    }

    formatChange(num) {
        if (num > 0) return '+' + this.formatNumber(num);
        return this.formatNumber(num);
    }

    formatChangePercent(num) {
        if (num > 0) return '+' + this.formatPercent(num);
        return this.formatPercent(num);
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
            operating_income: true,
            cost_of_revenue: true,
            operating_expenses: true,
            other_income: true,
        };
    }

    collapseAll() {
        this.state.expandedSections = {
            operating_income: false,
            cost_of_revenue: false,
            operating_expenses: false,
            other_income: false,
        };
    }

    // ==================== FILTER HANDLERS ====================

    async onChangeDateFrom(ev) {
        this.state.dateFrom = ev.target.value;
        await this.loadReportData();
    }

    async onChangeDateTo(ev) {
        this.state.dateTo = ev.target.value;
        await this.loadReportData();
    }

    async onChangePostedOnly(ev) {
        this.state.postedOnly = ev.target.checked;
        await this.loadReportData();
    }

    async onChangeComparison(ev) {
        this.state.comparison = ev.target.checked;
        await this.loadReportData();
    }

    async onChangeComparisonType(ev) {
        this.state.comparisonType = ev.target.value;
        if (this.state.comparison) {
            await this.loadReportData();
        }
    }

    async setPeriod(period) {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth();

        switch(period) {
            case 'this_month':
                this.state.dateFrom = `${year}-${String(month + 1).padStart(2, '0')}-01`;
                this.state.dateTo = this.getTodayDate();
                break;
            case 'last_month':
                const lastMonth = month === 0 ? 12 : month;
                const lastMonthYear = month === 0 ? year - 1 : year;
                const lastDay = new Date(lastMonthYear, lastMonth, 0).getDate();
                this.state.dateFrom = `${lastMonthYear}-${String(lastMonth).padStart(2, '0')}-01`;
                this.state.dateTo = `${lastMonthYear}-${String(lastMonth).padStart(2, '0')}-${lastDay}`;
                break;
            case 'this_quarter':
                const quarter = Math.floor(month / 3);
                const qMonth = quarter * 3 + 1;
                this.state.dateFrom = `${year}-${String(qMonth).padStart(2, '0')}-01`;
                this.state.dateTo = this.getTodayDate();
                break;
            case 'this_year':
                this.state.dateFrom = `${year}-01-01`;
                this.state.dateTo = this.getTodayDate();
                break;
            case 'last_year':
                this.state.dateFrom = `${year - 1}-01-01`;
                this.state.dateTo = `${year - 1}-12-31`;
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

        // Operating Income
        csv += '\nOPERATING INCOME\n';
        for (const acc of sections.operating_income?.accounts || []) {
            csv += `"Operating Income","${acc.code}","${acc.name}",${acc.balance}`;
            if (this.state.comparison) {
                csv += `,${acc.comp_balance},${acc.change},${acc.change_percent.toFixed(1)}%`;
            }
            csv += '\n';
        }
        csv += `"","","Total Operating Income",${sections.operating_income?.total || 0}\n`;

        // Cost of Revenue
        csv += '\nCOST OF REVENUE\n';
        for (const acc of sections.cost_of_revenue?.accounts || []) {
            csv += `"Cost of Revenue","${acc.code}","${acc.name}",${acc.balance}`;
            if (this.state.comparison) {
                csv += `,${acc.comp_balance},${acc.change},${acc.change_percent.toFixed(1)}%`;
            }
            csv += '\n';
        }
        csv += `"","","Total Cost of Revenue",${sections.cost_of_revenue?.total || 0}\n`;

        // Gross Profit
        csv += `\n"","","GROSS PROFIT",${summary.gross_profit || 0}\n`;

        // Operating Expenses
        csv += '\nOPERATING EXPENSES\n';
        for (const acc of sections.operating_expenses?.accounts || []) {
            csv += `"Operating Expenses","${acc.code}","${acc.name}",${acc.balance}`;
            if (this.state.comparison) {
                csv += `,${acc.comp_balance},${acc.change},${acc.change_percent.toFixed(1)}%`;
            }
            csv += '\n';
        }
        csv += `"","","Total Operating Expenses",${sections.operating_expenses?.total || 0}\n`;

        // Operating Profit
        csv += `\n"","","OPERATING PROFIT",${summary.operating_profit || 0}\n`;

        // Other Income
        csv += '\nOTHER INCOME\n';
        for (const acc of sections.other_income?.accounts || []) {
            csv += `"Other Income","${acc.code}","${acc.name}",${acc.balance}`;
            if (this.state.comparison) {
                csv += `,${acc.comp_balance},${acc.change},${acc.change_percent.toFixed(1)}%`;
            }
            csv += '\n';
        }
        csv += `"","","Total Other Income",${sections.other_income?.total || 0}\n`;

        // Net Profit
        csv += `\n"","","NET PROFIT",${summary.net_profit || 0}\n`;

        const BOM = '\uFEFF';
        const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `profit_loss_${this.state.dateFrom}_to_${this.state.dateTo}.csv`;
        link.click();
    }

    onPrint() {
        window.print();
    }

    // ==================== NAVIGATION ====================

    openAccount(accountId) {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "general_ledger_report",
            name: _t("General Ledger"),
            context: {
                default_account_ids: [accountId],
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
            },
        });
    }

    // ==================== HELPERS ====================

    getChangeClass(change) {
        if (change > 0) return 'change-positive';
        if (change < 0) return 'change-negative';
        return '';
    }

    getProfitClass(amount) {
        if (amount > 0) return 'profit-positive';
        if (amount < 0) return 'profit-negative';
        return '';
    }

    getSectionIcon(sectionKey) {
        const icons = {
            operating_income: 'fa-arrow-circle-up',
            cost_of_revenue: 'fa-shopping-cart',
            operating_expenses: 'fa-credit-card',
            other_income: 'fa-plus-circle',
        };
        return icons[sectionKey] || 'fa-folder';
    }

    getSectionClass(sectionKey) {
        const classes = {
            operating_income: 'section-income',
            cost_of_revenue: 'section-cogs',
            operating_expenses: 'section-expense',
            other_income: 'section-other',
        };
        return classes[sectionKey] || '';
    }
}

ProfitLossReport.template = "accounting_reports.ProfitLoss";
registry.category("actions").add("profit_loss_report", ProfitLossReport);
