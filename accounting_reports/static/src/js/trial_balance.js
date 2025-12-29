/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { Component, useState, onWillStart } = owl;

export class TrialBalanceReport extends Component {
    static template = "accounting_reports.TrialBalance";

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            // Report Data
            reportData: { accounts: [], totals: {} },

            // KPIs
            totalOpeningDebit: 0,
            totalOpeningCredit: 0,
            totalDebit: 0,
            totalCredit: 0,
            totalClosingDebit: 0,
            totalClosingCredit: 0,

            // Filters
            allAccountTypes: [],
            filteredAccountTypes: [],
            selectedAccountTypes: [],
            accountTypeSearch: '',
            showAccountTypeDropdown: false,
            dateFrom: this.getFirstDayOfYear(),
            dateTo: this.getTodayDate(),
            postedOnly: true,
            hideZero: true,

            // UI
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadAccountTypes();
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

    async loadAccountTypes() {
        try {
            const types = await this.orm.call(
                'report.trial.balance', 
                'get_account_types', 
                []
            );
            this.state.allAccountTypes = types;
            this.state.filteredAccountTypes = [];
        } catch (error) {
            console.error("Error loading account types:", error);
        }
    }

    // ==================== ACCOUNT TYPE SEARCH ====================

    onAccountTypeSearchInput(ev) {
        const query = ev.target.value.toLowerCase().trim();
        this.state.accountTypeSearch = ev.target.value;
        
        if (query.length < 1) {
            this.state.filteredAccountTypes = [];
            this.state.showAccountTypeDropdown = false;
            return;
        }
        
        // Filter account types
        this.state.filteredAccountTypes = this.state.allAccountTypes
            .filter(t => {
                const name = (t.name || '').toLowerCase();
                return name.includes(query);
            })
            .filter(t => !this.state.selectedAccountTypes.find(st => st.id === t.id));
        
        this.state.showAccountTypeDropdown = this.state.filteredAccountTypes.length > 0;
    }

    onAccountTypeSearchFocus() {
        // Show all if no search text
        if (this.state.accountTypeSearch.length < 1) {
            this.state.filteredAccountTypes = this.state.allAccountTypes
                .filter(t => !this.state.selectedAccountTypes.find(st => st.id === t.id));
        }
        this.state.showAccountTypeDropdown = this.state.filteredAccountTypes.length > 0;
    }

    onAccountTypeSearchBlur() {
        setTimeout(() => {
            this.state.showAccountTypeDropdown = false;
        }, 200);
    }

    async selectAccountType(accountType) {
        this.state.selectedAccountTypes.push(accountType);
        this.state.accountTypeSearch = '';
        this.state.filteredAccountTypes = [];
        this.state.showAccountTypeDropdown = false;
        await this.loadReportData();
    }

    async removeAccountType(accountTypeId) {
        this.state.selectedAccountTypes = this.state.selectedAccountTypes.filter(t => t.id !== accountTypeId);
        await this.loadReportData();
    }

    async clearAllAccountTypes() {
        this.state.selectedAccountTypes = [];
        await this.loadReportData();
    }

    async loadReportData() {
        this.state.isLoading = true;
        try {
            // Get account type IDs from selected
            const accountTypeIds = this.state.selectedAccountTypes.length > 0 
                ? this.state.selectedAccountTypes.map(t => t.id) 
                : false;
            
            const data = await this.orm.call(
                'report.trial.balance',
                'get_report_data',
                [],
                {
                    date_from: this.state.dateFrom,
                    date_to: this.state.dateTo,
                    account_types: accountTypeIds,
                    posted_only: this.state.postedOnly,
                    hide_zero: this.state.hideZero,
                }
            );
            
            this.state.reportData = data;
            
            // Update KPIs
            const totals = data.totals || {};
            this.state.totalOpeningDebit = totals.opening_debit || 0;
            this.state.totalOpeningCredit = totals.opening_credit || 0;
            this.state.totalDebit = totals.debit || 0;
            this.state.totalCredit = totals.credit || 0;
            this.state.totalClosingDebit = totals.closing_debit || 0;
            this.state.totalClosingCredit = totals.closing_credit || 0;
            
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

    async onChangeHideZero(ev) {
        this.state.hideZero = ev.target.checked;
        await this.loadReportData();
    }

    // ==================== ACTIONS ====================

    async onRefresh() {
        await this.loadReportData();
    }

    onExportExcel() {
        let csv = 'Account Code,Account Name,Type,Opening Debit,Opening Credit,Debit,Credit,Closing Debit,Closing Credit\n';
        
        for (const acc of this.state.reportData.accounts) {
            csv += `"${acc.code}","${acc.name}","${acc.account_type_name}",${acc.opening_debit},${acc.opening_credit},${acc.debit},${acc.credit},${acc.closing_debit},${acc.closing_credit}\n`;
        }
        
        const totals = this.state.reportData.totals;
        csv += `"TOTAL","","",${totals.opening_debit},${totals.opening_credit},${totals.debit},${totals.credit},${totals.closing_debit},${totals.closing_credit}\n`;
        
        const BOM = '\uFEFF';
        const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `trial_balance_${this.state.dateFrom}_${this.state.dateTo}.csv`;
        link.click();
    }

    onPrint() {
        window.print();
    }

    // ==================== NAVIGATION ====================

    openAccount(accountId) {
        // Navigate to General Ledger with this account filtered
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
}

TrialBalanceReport.template = "accounting_reports.TrialBalance";
registry.category("actions").add("trial_balance_report", TrialBalanceReport);
