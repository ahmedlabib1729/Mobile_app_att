/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { Component, useState, onWillStart } = owl;

export class PartnerLedgerReport extends Component {
    static template = "accounting_reports.PartnerLedger";

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            // Report Data
            reportData: { partners: [], totals: {} },

            // Expanded states
            expandedPartners: {},

            // KPIs
            totalOpening: 0,
            totalDebit: 0,
            totalCredit: 0,
            totalBalance: 0,

            // Partner Search
            allPartners: [],
            filteredPartners: [],
            selectedPartners: [],
            partnerSearch: '',
            showPartnerDropdown: false,

            // Tag Search
            allTags: [],
            filteredTags: [],
            selectedTags: [],
            tagSearch: '',
            showTagDropdown: false,

            // Other Filters
            dateFrom: this.getFirstDayOfYear(),
            dateTo: this.getTodayDate(),
            accountType: false,
            postedOnly: true,

            // UI
            isLoading: true,
            showExportMenu: false,
        });

        onWillStart(async () => {
            await this.loadPartners();
            await this.loadTags();
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

    async loadPartners() {
        try {
            const partners = await this.orm.call(
                'report.partner.ledger',
                'get_partners',
                []
            );
            this.state.allPartners = partners;
            this.state.filteredPartners = [];
        } catch (error) {
            console.error("Error loading partners:", error);
        }
    }

    async loadTags() {
        try {
            const tags = await this.orm.call(
                'report.partner.ledger',
                'get_partner_tags',
                []
            );
            this.state.allTags = tags;
            this.state.filteredTags = [];
        } catch (error) {
            console.error("Error loading tags:", error);
        }
    }

    // ==================== PARTNER SEARCH ====================

    onPartnerSearchInput(ev) {
        const query = ev.target.value.toLowerCase().trim();
        this.state.partnerSearch = ev.target.value;

        if (query.length < 1) {
            this.state.filteredPartners = [];
            this.state.showPartnerDropdown = false;
            return;
        }

        // Filter partners
        this.state.filteredPartners = this.state.allPartners
            .filter(p => {
                const name = (p.name || '').toLowerCase();
                const ref = (p.ref || '').toLowerCase();
                return name.includes(query) || ref.includes(query);
            })
            .filter(p => !this.state.selectedPartners.find(sp => sp.id === p.id))
            .slice(0, 10); // Limit to 10 results

        this.state.showPartnerDropdown = this.state.filteredPartners.length > 0;
    }

    onPartnerSearchFocus() {
        if (this.state.partnerSearch.length >= 1 && this.state.filteredPartners.length > 0) {
            this.state.showPartnerDropdown = true;
        }
    }

    onPartnerSearchBlur() {
        // Delay to allow click on dropdown item
        setTimeout(() => {
            this.state.showPartnerDropdown = false;
        }, 200);
    }

    async selectPartner(partner) {
        // Add to selected
        this.state.selectedPartners.push(partner);

        // Clear search
        this.state.partnerSearch = '';
        this.state.filteredPartners = [];
        this.state.showPartnerDropdown = false;

        // Reload report
        await this.loadReportData();
    }

    async removePartner(partnerId) {
        this.state.selectedPartners = this.state.selectedPartners.filter(p => p.id !== partnerId);
        await this.loadReportData();
    }

    async clearAllPartners() {
        this.state.selectedPartners = [];
        await this.loadReportData();
    }

    // ==================== TAG SEARCH ====================

    onTagSearchInput(ev) {
        const query = ev.target.value.toLowerCase().trim();
        this.state.tagSearch = ev.target.value;

        if (query.length < 1) {
            this.state.filteredTags = [];
            this.state.showTagDropdown = false;
            return;
        }

        // Filter tags
        this.state.filteredTags = this.state.allTags
            .filter(t => {
                const name = (t.name || '').toLowerCase();
                return name.includes(query);
            })
            .filter(t => !this.state.selectedTags.find(st => st.id === t.id))
            .slice(0, 10);

        this.state.showTagDropdown = this.state.filteredTags.length > 0;
    }

    onTagSearchFocus() {
        if (this.state.tagSearch.length >= 1 && this.state.filteredTags.length > 0) {
            this.state.showTagDropdown = true;
        }
    }

    onTagSearchBlur() {
        setTimeout(() => {
            this.state.showTagDropdown = false;
        }, 200);
    }

    async selectTag(tag) {
        this.state.selectedTags.push(tag);
        this.state.tagSearch = '';
        this.state.filteredTags = [];
        this.state.showTagDropdown = false;
        await this.loadReportData();
    }

    async removeTag(tagId) {
        this.state.selectedTags = this.state.selectedTags.filter(t => t.id !== tagId);
        await this.loadReportData();
    }

    async clearAllTags() {
        this.state.selectedTags = [];
        await this.loadReportData();
    }

    getTagColor(colorIndex) {
        const colors = [
            '#6c757d', '#007bff', '#28a745', '#17a2b8', '#ffc107',
            '#dc3545', '#e83e8c', '#6f42c1', '#fd7e14', '#20c997',
            '#343a40', '#6610f2'
        ];
        return colors[colorIndex % colors.length] || colors[0];
    }

    // ==================== REPORT DATA ====================

    async loadReportData() {
        this.state.isLoading = true;
        try {
            // Prepare account_type - send false if empty
            const accountType = this.state.accountType && this.state.accountType !== ''
                ? this.state.accountType
                : false;

            // Get partner IDs from selected partners
            const partnerIds = this.state.selectedPartners.length > 0
                ? this.state.selectedPartners.map(p => p.id)
                : false;

            // Get tag IDs from selected tags
            const tagIds = this.state.selectedTags.length > 0
                ? this.state.selectedTags.map(t => t.id)
                : false;

            const data = await this.orm.call(
                'report.partner.ledger',
                'get_report_data',
                [],
                {
                    date_from: this.state.dateFrom,
                    date_to: this.state.dateTo,
                    partner_ids: partnerIds,
                    account_type: accountType,
                    posted_only: this.state.postedOnly,
                    tag_ids: tagIds,
                }
            );

            this.state.reportData = data;

            // Update KPIs
            const totals = data.totals || {};
            this.state.totalOpening = totals.opening || 0;
            this.state.totalDebit = totals.debit || 0;
            this.state.totalCredit = totals.credit || 0;
            this.state.totalBalance = totals.balance || 0;

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

    // ==================== EXPAND/COLLAPSE ====================

    togglePartner(partnerId) {
        this.state.expandedPartners[partnerId] = !this.state.expandedPartners[partnerId];
    }

    isPartnerExpanded(partnerId) {
        return this.state.expandedPartners[partnerId] || false;
    }

    expandAll() {
        for (const partner of this.state.reportData.partners) {
            this.state.expandedPartners[partner.id] = true;
        }
    }

    collapseAll() {
        this.state.expandedPartners = {};
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

    async onChangeAccountType(ev) {
        const value = ev.target.value;
        this.state.accountType = value && value !== '' ? value : false;
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

    toggleExportMenu() {
        this.state.showExportMenu = !this.state.showExportMenu;
    }

    onExportExcel(withDetails = true) {
    this.state.showExportMenu = false;

    let csv = '';
    const totals = this.state.reportData.totals;

    if (withDetails) {
        // Export with full details
        csv = 'Partner,Ref,Tags,Date,Reference,Journal,Account,Label,Debit,Credit,Balance\n';

        for (const partner of this.state.reportData.partners) {
            const tags = (partner.tags || []).map(t => t.name).join('; ');
            csv += `"${partner.name}","${partner.ref}","${tags}",,,,,${partner.debit},${partner.credit},${partner.balance}\n`;
            csv += `"","","","Opening Balance",,,,,${partner.opening}\n`;

            for (const move of partner.moves) {
                csv += `"","","","${move.date}","${move.move_name}","${move.journal_code}","${move.account_code}","${move.label || ''}",${move.debit},${move.credit},${move.balance}\n`;
            }
        }

        csv += `"GRAND TOTAL","","",,,,,,,${totals.debit},${totals.credit},${totals.balance}\n`;
    } else {
        // Export summary only
        csv = 'Partner,Ref,Tags,Debit,Credit,Balance\n';

        for (const partner of this.state.reportData.partners) {
            const tags = (partner.tags || []).map(t => t.name).join('; ');
            csv += `"${partner.name}","${partner.ref}","${tags}",${partner.debit},${partner.credit},${partner.balance}\n`;
        }

        csv += `"GRAND TOTAL","","",${totals.debit},${totals.credit},${totals.balance}\n`;
    }

    // ✅ إضافة BOM للـ UTF-8 عشان يدعم العربي
    const BOM = '\uFEFF';
    const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8;' });

    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    const suffix = withDetails ? 'detailed' : 'summary';
    link.download = `partner_ledger_${suffix}_${this.state.dateFrom}_${this.state.dateTo}.csv`;
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

    openPartner(partnerId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Partner"),
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

PartnerLedgerReport.template = "accounting_reports.PartnerLedger";
registry.category("actions").add("partner_ledger_report", PartnerLedgerReport);