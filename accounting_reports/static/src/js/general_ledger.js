/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { Component, useState, onWillStart } = owl;

export class GeneralLedgerReport extends Component {
    static template = "accounting_reports.GeneralLedger";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        
        // Get context from action
        const context = this.props.action?.context || {};

        this.state = useState({
            // Report Data
            reportData: { accounts: [], totals: {} },

            // Expanded states for accounts
            expandedAccounts: {},
            
            // Expanded states for journal entries (move details)
            expandedMoves: {},
            moveDetails: {},
            loadingMoveDetails: {},

            // KPIs
            totalOpening: 0,
            totalDebit: 0,
            totalCredit: 0,
            totalBalance: 0,

            // Filters
            journals: [],
            dateFrom: context.date_from || this.getFirstDayOfYear(),
            dateTo: context.date_to || this.getTodayDate(),
            selectedJournals: [],
            postedOnly: true,

            // Account Search
            allAccounts: [],
            filteredAccounts: [],
            selectedAccounts: [],
            accountSearch: '',
            showAccountDropdown: false,

            // UI
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadJournals();
            await this.loadAccounts();
            
            // Check if coming from Trial Balance with account filter
            if (context.default_account_ids && context.default_account_ids.length > 0) {
                // Find and select the accounts from context
                for (const accId of context.default_account_ids) {
                    const account = this.state.allAccounts.find(a => a.id === accId);
                    if (account) {
                        this.state.selectedAccounts.push(account);
                    }
                }
            }
            
            await this.loadReportData();
            
            // Auto-expand if single account selected
            if (context.default_account_ids && context.default_account_ids.length === 1) {
                this.state.expandedAccounts[context.default_account_ids[0]] = true;
            }
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

    async loadJournals() {
        try {
            this.state.journals = await this.orm.call(
                'report.general.ledger', 
                'get_journals', 
                []
            );
        } catch (error) {
            console.error("Error loading journals:", error);
        }
    }

    async loadAccounts() {
        try {
            this.state.allAccounts = await this.orm.call(
                'report.general.ledger',
                'get_accounts',
                []
            );
        } catch (error) {
            console.error("Error loading accounts:", error);
        }
    }

    async loadReportData() {
        this.state.isLoading = true;
        try {
            const selectedAccountIds = this.state.selectedAccounts.map(a => a.id);
            
            const data = await this.orm.call(
                'report.general.ledger',
                'get_report_data',
                [],
                {
                    date_from: this.state.dateFrom,
                    date_to: this.state.dateTo,
                    journal_ids: this.state.selectedJournals.length > 0 ? this.state.selectedJournals : false,
                    account_ids: selectedAccountIds.length > 0 ? selectedAccountIds : false,
                    partner_ids: false,
                    posted_only: this.state.postedOnly,
                    show_zero: false,
                }
            );
            
            this.state.reportData = data;
            
            // Update KPIs
            const totals = data.totals || {};
            this.state.totalOpening = totals.opening || 0;
            this.state.totalDebit = totals.debit || 0;
            this.state.totalCredit = totals.credit || 0;
            this.state.totalBalance = totals.balance || 0;
            
            // Reset expanded moves when data reloads
            this.state.expandedMoves = {};
            this.state.moveDetails = {};
            
        } catch (error) {
            console.error("Error loading report data:", error);
        }
        this.state.isLoading = false;
    }

    async loadMoveDetails(moveId) {
        if (this.state.moveDetails[moveId]) {
            return; // Already loaded
        }
        
        this.state.loadingMoveDetails[moveId] = true;
        try {
            const details = await this.orm.call(
                'report.general.ledger',
                'get_move_lines',
                [moveId]
            );
            this.state.moveDetails[moveId] = details;
        } catch (error) {
            console.error("Error loading move details:", error);
        }
        this.state.loadingMoveDetails[moveId] = false;
    }

    // ==================== ACCOUNT SEARCH ====================

    onAccountSearchInput(ev) {
        const query = ev.target.value.toLowerCase();
        this.state.accountSearch = ev.target.value;
        
        if (query.length < 1) {
            this.state.filteredAccounts = [];
            this.state.showAccountDropdown = false;
            return;
        }
        
        // Filter accounts not already selected
        const selectedIds = this.state.selectedAccounts.map(a => a.id);
        this.state.filteredAccounts = this.state.allAccounts
            .filter(a => 
                !selectedIds.includes(a.id) && 
                (a.code.toLowerCase().includes(query) || a.name.toLowerCase().includes(query))
            )
            .slice(0, 10);
        
        this.state.showAccountDropdown = this.state.filteredAccounts.length > 0;
    }

    onAccountSearchFocus() {
        if (this.state.accountSearch.length >= 1) {
            this.state.showAccountDropdown = this.state.filteredAccounts.length > 0;
        }
    }

    onAccountSearchBlur() {
        // Delay to allow click on dropdown item
        setTimeout(() => {
            this.state.showAccountDropdown = false;
        }, 200);
    }

    async selectAccount(account) {
        if (!this.state.selectedAccounts.find(a => a.id === account.id)) {
            this.state.selectedAccounts.push(account);
        }
        this.state.accountSearch = '';
        this.state.filteredAccounts = [];
        this.state.showAccountDropdown = false;
        await this.loadReportData();
    }

    async removeAccount(accountId) {
        this.state.selectedAccounts = this.state.selectedAccounts.filter(a => a.id !== accountId);
        await this.loadReportData();
    }

    async clearAllAccounts() {
        this.state.selectedAccounts = [];
        this.state.accountSearch = '';
        await this.loadReportData();
    }

    // ==================== FORMATTING ====================

    formatNumber(num) {
        return (num || 0).toLocaleString('en-US', { 
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2 
        });
    }

    // ==================== EXPAND/COLLAPSE ACCOUNTS ====================

    toggleAccount(accountId) {
        this.state.expandedAccounts[accountId] = !this.state.expandedAccounts[accountId];
    }

    isAccountExpanded(accountId) {
        return this.state.expandedAccounts[accountId] || false;
    }

    expandAll() {
        for (const account of this.state.reportData.accounts) {
            this.state.expandedAccounts[account.id] = true;
        }
    }

    collapseAll() {
        this.state.expandedAccounts = {};
        this.state.expandedMoves = {};
    }

    // ==================== EXPAND/COLLAPSE MOVES ====================

    async toggleMove(moveId) {
        const isExpanded = this.state.expandedMoves[moveId];
        
        if (!isExpanded) {
            // Load details if not already loaded
            await this.loadMoveDetails(moveId);
        }
        
        this.state.expandedMoves[moveId] = !isExpanded;
    }

    isMoveExpanded(moveId) {
        return this.state.expandedMoves[moveId] || false;
    }

    isMoveLoading(moveId) {
        return this.state.loadingMoveDetails[moveId] || false;
    }

    getMoveDetails(moveId) {
        return this.state.moveDetails[moveId] || null;
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

    async onChangeJournal(ev) {
        const options = ev.target.options;
        const selected = [];
        for (let i = 0; i < options.length; i++) {
            if (options[i].selected && options[i].value) {
                selected.push(parseInt(options[i].value));
            }
        }
        this.state.selectedJournals = selected;
        await this.loadReportData();
    }

    async onChangePostedOnly(ev) {
        this.state.postedOnly = ev.target.checked;
        await this.loadReportData();
    }

    // ==================== ACTIONS ====================

    async onRefresh() {
        await this.loadReportData();
    }

    onExportExcel() {
        let csv = 'Account Code,Account Name,Date,Reference,Journal,Partner,Label,Debit,Credit,Balance\n';
        
        for (const account of this.state.reportData.accounts) {
            csv += `"${account.code}","${account.name}",,,,,,${account.debit},${account.credit},${account.balance}\n`;
            csv += `"","Opening Balance",,,,,,,,${account.opening}\n`;
            
            for (const move of account.moves) {
                csv += `"","","${move.date}","${move.move_name}","${move.journal}","${move.partner || ''}","${move.label || ''}",${move.debit},${move.credit},${move.balance}\n`;
            }
        }
        
        const totals = this.state.reportData.totals;
        csv += `"GRAND TOTAL","",,,,,,,${totals.debit},${totals.credit},${totals.balance}\n`;
        
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `general_ledger_${this.state.dateFrom}_${this.state.dateTo}.csv`;
        link.click();
    }

    onPrint() {
        window.print();
    }

    // ==================== NAVIGATION ====================

    openMove(moveId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Journal Entry"),
            res_model: "account.move",
            res_id: moveId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAccount(accountId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Account"),
            res_model: "account.account",
            res_id: accountId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

GeneralLedgerReport.template = "accounting_reports.GeneralLedger";
registry.category("actions").add("general_ledger_report", GeneralLedgerReport);
