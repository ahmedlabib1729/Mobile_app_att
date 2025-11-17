/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const data = super.getReceiptHeaderData(order);

        // Company info
        if (this.company?.logo) {
            data.company.logo = this.company.logo;
        }
        if (this.company?.street) {
            data.company.street = this.company.street;
        }
        if (this.company?.city) {
            data.company.city = this.company.city;
        }
        if (this.company?.phone) {
            data.company.phone = this.company.phone;
        }
        if (this.company?.email) {
            data.company.email = this.company.email;
        }
        if (this.company?.vat) {
            data.company.vat = this.company.vat;
        }

        // Custom settings
        if (this.config?.receipt_footer) {
            data.footer_text = this.config.receipt_footer;
        }
        data.show_line_numbers = this.config?.show_line_numbers || false;
        data.show_barcode = this.config?.show_barcode || false;

        // Add line numbers and discount to orderlines
        if (data.orderlines) {
            let totalDiscount = 0;
            data.orderlines = data.orderlines.map((line, index) => {
                const newLine = {...line};
                newLine.line_number = index + 1;

                if (line.discount > 0) {
                    totalDiscount += (line.price * line.quantity * line.discount / 100);
                }

                return newLine;
            });
            data.total_discount = totalDiscount;
        }

        return data;
    }
});