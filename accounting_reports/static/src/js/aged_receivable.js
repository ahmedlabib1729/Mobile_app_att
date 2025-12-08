/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { Component, useState, onWillStart } = owl;

export class AgedReceivableReport extends Component {
    static template = "accounting_reports.AgedReceivable";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            // Report Data
            reportData: { partners: [], totals: {}, period_labels: [] },

            // Expanded states
            expandedPartners: {},

            // Filters
            allPartners: [],
            filteredPartners: [],
            selectedPartners: [],
            partnerSearch: '',
            showPartnerDropdown: false,
            asOfDate: this.getTodayDate(),
            periodLength: 30,

            // UI
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadPartners();
            await this.loadReportData();
        });
    }

    getTodayDate() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    }

    async loadPartners() {
        try {
            const partners = await this.orm.call(
                'report.aged.partner',
                'get_partners',
                [],
                { report_type: 'receivable' }
            );
            this.state.allPartners = partners;
        } catch (error) {
            console.error("Error loading partners:", error);
        }
    }

    async loadReportData() {
        this.state.isLoading = true;
        try {
            const partnerIds = this.state.selectedPartners.length > 0
                ? this.state.selectedPartners.map(p => p.id)
                : false;

            const data = await this.orm.call(
                'report.aged.partner',
                'get_report_data',
                [],
                {
                    as_of_date: this.state.asOfDate,
                    partner_ids: partnerIds,
                    report_type: 'receivable',
                    period_length: this.state.periodLength,
                }
            );

            this.state.reportData = data;
        } catch (error) {
            console.error("Error loading report data:", error);
        }
        this.state.isLoading = false;
    }

    formatNumber(num) {
        return (num || 0).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    onPartnerSearchInput(ev) {
        const query = ev.target.value.toLowerCase().trim();
        this.state.partnerSearch = ev.target.value;

        if (query.length < 1) {
            this.state.filteredPartners = [];
            this.state.showPartnerDropdown = false;
            return;
        }

        this.state.filteredPartners = this.state.allPartners
            .filter(p => {
                const name = (p.name || '').toLowerCase();
                const ref = (p.ref || '').toLowerCase();
                return name.includes(query) || ref.includes(query);
            })
            .filter(p => !this.state.selectedPartners.find(sp => sp.id === p.id))
            .slice(0, 10);

        this.state.showPartnerDropdown = this.state.filteredPartners.length > 0;
    }

    onPartnerSearchFocus() {
        if (this.state.partnerSearch.length >= 1 && this.state.filteredPartners.length > 0) {
            this.state.showPartnerDropdown = true;
        }
    }

    onPartnerSearchBlur() {
        setTimeout(() => { this.state.showPartnerDropdown = false; }, 200);
    }

    async selectPartner(partner) {
        this.state.selectedPartners.push(partner);
        this.state.partnerSearch = '';
        this.state.filteredPartners = [];
        this.state.showPartnerDropdown = false;
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

    async onChangeAsOfDate(ev) {
        this.state.asOfDate = ev.target.value;
        await this.loadReportData();
    }

    async onChangePeriodLength(ev) {
        this.state.periodLength = parseInt(ev.target.value);
        await this.loadReportData();
    }

    async onRefresh() {
        await this.loadReportData();
    }

    onExportExcel() {
        const labels = this.state.reportData.period_labels || [];
        let csv = `Partner,Ref,${labels.join(',')},Total\n`;

        for (const partner of this.state.reportData.partners) {
            csv += `"${partner.name}","${partner.ref}",${partner.not_due},${partner.period1},${partner.period2},${partner.period3},${partner.period4},${partner.older},${partner.total}\n`;
        }

        const totals = this.state.reportData.totals;
        csv += `"TOTAL","",${totals.not_due},${totals.period1},${totals.period2},${totals.period3},${totals.period4},${totals.older},${totals.total}\n`;

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `aged_receivable_${this.state.asOfDate}.csv`;
        link.click();
    }

    onPrint() {
        window.print();
    }

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

    openPartnerLedger(partnerId) {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "partner_ledger_report",
            name: _t("Partner Ledger"),
            context: {
                default_partner_ids: [partnerId],
                default_account_type: 'asset_receivable',
            },
        });
    }

    getPeriodClass(period) {
        const classes = {
            'not_due': 'not-due',
            'period1': 'period-1',
            'period2': 'period-2',
            'period3': 'period-3',
            'period4': 'period-4',
            'older': 'period-older',
        };
        return classes[period] || '';
    }
}

AgedReceivableReport.template = "accounting_reports.AgedReceivable";
registry.category("actions").add("aged_receivable_report", AgedReceivableReport);
