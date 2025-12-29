/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { Component, useState, onWillStart } = owl;

export class TaxReport extends Component {
    static template = "accounting_reports.TaxReport";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            // Report Data
            reportData: { 
                sales_taxes: [], 
                purchase_taxes: [], 
                totals: {} 
            },

            // Expanded states
            expandedSalesTaxes: {},
            expandedPurchaseTaxes: {},
            taxDetails: {},

            // Filters
            dateFrom: this.getFirstDayOfYear(),
            dateTo: this.getTodayDate(),
            postedOnly: true,

            // UI
            isLoading: true,
            loadingDetails: {},
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

    getFirstDayOfMonth() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    }

    getFirstDayOfQuarter() {
        const now = new Date();
        const quarter = Math.floor(now.getMonth() / 3);
        const month = quarter * 3 + 1;
        return `${now.getFullYear()}-${String(month).padStart(2, '0')}-01`;
    }

    // ==================== DATA LOADING ====================

    async loadReportData() {
        this.state.isLoading = true;
        try {
            const data = await this.orm.call(
                'report.tax.report',
                'get_report_data',
                [],
                {
                    date_from: this.state.dateFrom,
                    date_to: this.state.dateTo,
                    posted_only: this.state.postedOnly,
                }
            );

            this.state.reportData = data;
            // Reset expanded states
            this.state.expandedSalesTaxes = {};
            this.state.expandedPurchaseTaxes = {};
            this.state.taxDetails = {};

        } catch (error) {
            console.error("Error loading report data:", error);
        }
        this.state.isLoading = false;
    }

    async loadTaxDetails(taxId, taxType) {
        const key = `${taxType}_${taxId}`;
        
        if (this.state.taxDetails[key]) {
            return; // Already loaded
        }

        this.state.loadingDetails[key] = true;
        
        try {
            const details = await this.orm.call(
                'report.tax.report',
                'get_tax_details',
                [],
                {
                    tax_id: taxId,
                    date_from: this.state.dateFrom,
                    date_to: this.state.dateTo,
                    tax_type: taxType,
                    posted_only: this.state.postedOnly,
                }
            );

            this.state.taxDetails[key] = details;
        } catch (error) {
            console.error("Error loading tax details:", error);
        }
        
        this.state.loadingDetails[key] = false;
    }

    // ==================== FORMATTING ====================

    formatNumber(num) {
        return (num || 0).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    formatPercent(num) {
        return (num || 0).toFixed(2) + '%';
    }

    // ==================== EXPAND/COLLAPSE ====================

    async toggleSalesTax(taxId) {
        const isExpanded = this.state.expandedSalesTaxes[taxId];
        this.state.expandedSalesTaxes[taxId] = !isExpanded;
        
        if (!isExpanded) {
            await this.loadTaxDetails(taxId, 'sale');
        }
    }

    async togglePurchaseTax(taxId) {
        const isExpanded = this.state.expandedPurchaseTaxes[taxId];
        this.state.expandedPurchaseTaxes[taxId] = !isExpanded;
        
        if (!isExpanded) {
            await this.loadTaxDetails(taxId, 'purchase');
        }
    }

    isSalesTaxExpanded(taxId) {
        return this.state.expandedSalesTaxes[taxId] || false;
    }

    isPurchaseTaxExpanded(taxId) {
        return this.state.expandedPurchaseTaxes[taxId] || false;
    }

    getTaxDetails(taxId, taxType) {
        const key = `${taxType}_${taxId}`;
        return this.state.taxDetails[key] || [];
    }

    isLoadingDetails(taxId, taxType) {
        const key = `${taxType}_${taxId}`;
        return this.state.loadingDetails[key] || false;
    }

    expandAllSales() {
        for (const tax of this.state.reportData.sales_taxes) {
            this.state.expandedSalesTaxes[tax.tax_id] = true;
            this.loadTaxDetails(tax.tax_id, 'sale');
        }
    }

    expandAllPurchases() {
        for (const tax of this.state.reportData.purchase_taxes) {
            this.state.expandedPurchaseTaxes[tax.tax_id] = true;
            this.loadTaxDetails(tax.tax_id, 'purchase');
        }
    }

    collapseAll() {
        this.state.expandedSalesTaxes = {};
        this.state.expandedPurchaseTaxes = {};
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
        }
        await this.loadReportData();
    }

    // ==================== ACTIONS ====================

    async onRefresh() {
        await this.loadReportData();
    }

    onExportExcel() {
        let csv = 'Type,Tax Name,Rate,Base Amount,Tax Amount,Invoices\n';

        // Sales Taxes
        csv += '\nSALES TAXES\n';
        for (const tax of this.state.reportData.sales_taxes) {
            csv += `"Sales","${tax.tax_name}",${tax.tax_percent}%,${tax.base_amount},${tax.tax_total},${tax.invoice_count}\n`;
        }
        csv += `"","TOTAL SALES","",${this.state.reportData.totals.sales_base},${this.state.reportData.totals.sales_tax},""\n`;

        // Purchase Taxes
        csv += '\nPURCHASE TAXES\n';
        for (const tax of this.state.reportData.purchase_taxes) {
            csv += `"Purchases","${tax.tax_name}",${tax.tax_percent}%,${tax.base_amount},${tax.tax_total},${tax.invoice_count}\n`;
        }
        csv += `"","TOTAL PURCHASES","",${this.state.reportData.totals.purchase_base},${this.state.reportData.totals.purchase_tax},""\n`;

        // Net
        csv += `\n"","NET TAX DUE","","",${this.state.reportData.totals.net_tax},""\n`;

        const BOM = '\uFEFF';
        const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `tax_report_${this.state.dateFrom}_to_${this.state.dateTo}.csv`;
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

    openTaxMoves(taxData, taxType) {
        const moveIds = taxData.move_ids || [];
        if (moveIds.length === 0) return;

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: taxData.tax_name,
            res_model: "account.move",
            views: [[false, "list"], [false, "form"]],
            domain: [['id', 'in', moveIds]],
            target: "current",
        });
    }

    // ==================== HELPERS ====================

    getMoveTypeLabel(moveType) {
        const labels = {
            'out_invoice': 'Invoice',
            'out_refund': 'Credit Note',
            'in_invoice': 'Bill',
            'in_refund': 'Refund',
            'entry': 'Journal Entry',
        };
        return labels[moveType] || moveType;
    }

    getNetTaxClass() {
        const net = this.state.reportData.totals?.net_tax || 0;
        if (net > 0) return 'net-positive';  // You owe tax
        if (net < 0) return 'net-negative';  // Tax refund
        return '';
    }
}

TaxReport.template = "accounting_reports.TaxReport";
registry.category("actions").add("tax_report", TaxReport);
