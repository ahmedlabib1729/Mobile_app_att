/** @odoo-module */
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { xml, markup } from "@odoo/owl";

/**
 * Following Odoo 18 POS documentation for extending receipts
 * The key is to avoid DOM manipulation and use proper Owl patterns
 */

// Extend the OrderReceipt component following Odoo 18 patterns
patch(OrderReceipt.prototype, {
    /**
     * Check if custom receipt is enabled
     * Using proper Odoo 18 service access pattern
     */
    get isCustomReceiptEnabled() {
        // Access POS data through proper Odoo 18 pattern
        const posData = this.pos || this.env?.services?.pos;
        if (!posData) return false;

        const config = posData.config;
        if (!config) return false;

        // Check configuration flags
        const enabled = config.is_custom_receipt === true;
        const hasTemplate = Boolean(config.design_receipt);

        console.log('Custom receipt check - Enabled:', enabled, 'Has template:', hasTemplate);

        return enabled && hasTemplate;
    },

    /**
     * Get processed custom receipt HTML
     * Following Odoo 18 data access patterns
     */
    get customReceiptHtml() {
        if (!this.isCustomReceiptEnabled) {
            return '';
        }

        try {
            const posData = this.pos || this.env?.services?.pos;
            const template = posData.config.design_receipt;

            // Get receipt data using Odoo 18 pattern
            const receiptData = this.receiptData;

            // Process template
            const processedHtml = this._processCustomTemplate(template, receiptData);

            // ONLY CHANGE: Use markup() to render HTML properly
            return markup(processedHtml);

        } catch (error) {
            console.error('Error processing custom receipt:', error);
            return '';
        }
    },

    /**
     * Get receipt data in Odoo 18 format
     */
    get receiptData() {
        // Use props data if available (for past orders)
        if (this.props && this.props.data) {
            return this.props.data;
        }

        // Otherwise get current order data
        const posData = this.pos || this.env?.services?.pos;
        const order = posData?.get_order?.();

        if (!order) {
            return {
                orderlines: [],
                paymentlines: [],
                headerData: {},
                amount_total: 0,
                total_without_tax: 0
            };
        }

        // Export order data in receipt format
        return order.export_for_printing?.() || {};
    },

    /**
     * Process custom template with data
     * @private
     */
    _processCustomTemplate(template, data) {
        if (!template) return '';

        let html = template;
        const posData = this.pos || this.env?.services?.pos;

        // Company data replacements
        const company = posData?.company || {};
        html = html.replace(/env\.services\.pos\.company\.name/g, company.name || '');
        html = html.replace(/env\.services\.pos\.company\.phone/g, company.phone || '');
        html = html.replace(/env\.services\.pos\.company\.email/g, company.email || '');
        html = html.replace(/env\.services\.pos\.company\.website/g, company.website || '');
        html = html.replace(/env\.services\.pos\.company\.vat/g, company.vat || '');
        html = html.replace(/env\.services\.pos\.company\.vat_label/g, company.vat_label || 'VAT');

        // Config data
        const config = posData?.config || {};
        html = html.replace(/env\.services\.pos\.config\.logo/g, config.logo || '');

        // Receipt/Order data
        const receipt = data.receipt || data || {};
        const order = data.order || {};
        const headerData = data.headerData || {};

        html = html.replace(/props\.receipt\.name/g, receipt.name || order.name || '');
        html = html.replace(/props\.receipt\.date/g, receipt.date || data.date || '');
        html = html.replace(/props\.receipt\.headerData\.cashier/g, headerData.cashier || '');
        html = html.replace(/props\.receipt\.headerData\.header/g, headerData.header || '');
        html = html.replace(/props\.receipt\.footer/g, receipt.footer || '');
        html = html.replace(/props\.receipt\.footer_html/g, receipt.footer_html || '');
        html = html.replace(/props\.receipt\.change/g, String(receipt.change || 0));
        html = html.replace(/props\.receipt\.total_discount/g, String(receipt.total_discount || 0));
        html = html.replace(/props\.receipt\.total_tax/g, String(receipt.total_tax || 0));
        html = html.replace(/props\.receipt\.amount_total/g, String(receipt.amount_total || receipt.total_with_tax || 0));
        html = html.replace(/props\.receipt\.total_with_tax/g, String(receipt.total_with_tax || 0));
        html = html.replace(/props\.receipt\.tax_details/g, 'false'); // Simplified for now

        html = html.replace(/props\.order\.name/g, order.name || '');
        html = html.replace(/props\.order\.validation_date/g, order.validation_date || '');
        html = html.replace(/props\.order\.partner_id\.name/g, order.partner_id?.name || '');
        html = html.replace(/props\.order\.partner_id/g, order.partner_id ? 'true' : '');

        html = html.replace(/props\.data\.amount_total/g, String(data.amount_total || 0));
        html = html.replace(/props\.data\.total_without_tax/g, String(data.total_without_tax || 0));
        html = html.replace(/props\.data\.tax_details/g, 'false'); // Simplified

        // Handle formatCurrency calls
        html = html.replace(/env\.utils\.formatCurrency\(([^)]+)\)/g, (match, expr) => {
            // Simple currency formatting
            let amount = 0;
            if (expr.includes('amount_total')) {
                amount = parseFloat(data.amount_total) || 0;
            } else if (expr.includes('total_without_tax')) {
                amount = parseFloat(data.total_without_tax) || 0;
            } else if (expr.includes('change')) {
                amount = parseFloat(receipt.change) || 0;
            }
            return amount.toFixed(2) + ' AED';
        });

        // Process orderlines - IMPROVED VERSION
        html = this._processOrderlines(html, data.orderlines || []);

        // Process paymentlines
        html = this._processPaymentlines(html, data.paymentlines || []);

        // Clean QWeb directives
        html = this._cleanQWebDirectives(html);

        return html;
    },

    /**
     * Process orderlines in template - FIXED VERSION
     * @private
     */
    _processOrderlines(html, orderlines) {
        console.log('Processing orderlines, count:', orderlines?.length || 0);

        // Check if this is the new simple template (uses props.data.orderlines)
        const isSimpleTemplate = html.includes('props.data.orderlines');

        if (isSimpleTemplate) {
            console.log('Simple template detected - no processing needed');
            // Don't process the simple template - it already uses the correct path
            return html;
        }

        // Below is for the old complex templates only
        if (!orderlines || orderlines.length === 0) {
            console.log('No orderlines to process');
            html = html.replace(/<tr[^>]*t-foreach=['"].*?orderlines.*?['"][^>]*>[\s\S]*?<\/tr>/gi, '');
            html = html.replace(/<t[^>]*t-if=['"].*?orderlines.*?['"][^>]*>[\s\S]*?<\/t>/gi, '');
            html = html.replace(/<t[^>]*t-else=""[^>]*>[\s\S]*?<\/t>/gi, '');
            return html;
        }

        console.log('Orderline data:', orderlines[0]);

        // Rest of the processing for old templates...
        const hasComplexCondition = html.includes('props.order and props.order.length');
        const hasElseBlock = html.includes('t-else=""');
        const hasOrderlinesCondition = html.includes('props.orderlines and props.orderlines.length');

        console.log('Template patterns found:', {
            hasComplexCondition,
            hasElseBlock,
            hasOrderlinesCondition
        });

        if (hasComplexCondition) {
            html = html.replace(/<t[^>]*t-if=['"]props\.order and props\.order\.length.*?props\.order\.orderlines\.length['"][^>]*>[\s\S]*?<\/t>(?=[\s\S]*?<t[^>]*t-else)/gi, '');
            console.log('Removed complex condition');
        }

        html = html.replace(/<t[^>]*t-else=""[^>]*>([\s\S]*?)<\/t>/gi, (match, content) => {
            console.log('Found else block with content');
            return content;
        });

        if (hasOrderlinesCondition) {
            html = html.replace(/<t[^>]*t-if=['"]props\.orderlines and props\.orderlines\.length['"][^>]*>([\s\S]*?)<\/t>/gi, (match, content) => {
                console.log('Found orderlines condition block');
                return content;
            });
        }

        let orderlinesForeachFound = false;
        const foreachPatterns = [
            /<tr[^>]*t-foreach=['"]props\.orderlines['"][^>]*>([\s\S]*?)<\/tr>/gi,
            /<tr[^>]*t-foreach="props\.orderlines"[^>]*>([\s\S]*?)<\/tr>/gi,
            /<tr\s+t-foreach=['"]props\.orderlines['"][^>]*>([\s\S]*?)<\/tr>/gi
        ];

        for (const pattern of foreachPatterns) {
            html = html.replace(pattern, (match, content) => {
                orderlinesForeachFound = true;
                console.log('Processing orderlines foreach, template content length:', content.length);

                const rows = orderlines.map((line, index) => {
                    console.log(`Processing line ${index}:`, line);
                    let row = content;

                    const productName = line.productName || line.product_name || 'Unknown Product';
                    const qty = line.qty || line.quantity || 0;
                    const price = typeof line.price === 'string' ? line.price : (line.price || 0).toFixed(2) + ' AED';
                    const discount = parseFloat(line.discount || 0);
                    const note = line.customerNote || line.customer_note || '';

                    console.log(`Line ${index} data:`, { productName, qty, price, discount });

                    row = row.replace(/orderline\.productName/gi, productName);
                    row = row.replace(/orderline\.get_quantity_str_with_unit\(\)/gi, String(qty));
                    row = row.replace(/orderline\.qty/gi, String(qty));
                    row = row.replace(/orderline\.get_display_price\(\)/gi, price);
                    row = row.replace(/orderline\.price/gi, price);
                    row = row.replace(/orderline\.get_discount\(\)/gi, String(discount));
                    row = row.replace(/orderline\.discount/gi, String(discount));
                    row = row.replace(/orderline\.customerNote/gi, note);

                    return '<tr>' + row + '</tr>';
                });

                console.log('Generated', rows.length, 'rows');
                return rows.join('');
            });
        }

        if (!orderlinesForeachFound) {
            console.log('WARNING: No orderlines foreach found in template!');
        }

        return html;
    },

    /**
     * Process paymentlines in template
     * @private
     */
    _processPaymentlines(html, paymentlines) {
        if (!paymentlines || paymentlines.length === 0) {
            html = html.replace(/<[^>]*t-foreach=['"].*?paymentlines.*?['"][^>]*>[\s\S]*?<\/[^>]+>/gi, '');
            return html;
        }

        // Replace paymentline loops - handle both patterns
        const patterns = [
            /<t[^>]*t-foreach=['"]props\.paymentlines['"][^>]*>([\s\S]*?)<\/t>/gi,
            /<div[^>]*t-foreach=['"]props\.paymentlines['"][^>]*>([\s\S]*?)<\/div>/gi,
            /<t[^>]*t-foreach=['"].*?paymentlines.*?['"][^>]*>([\s\S]*?)<\/t>/gi,
            /<div[^>]*t-foreach=['"].*?paymentlines.*?['"][^>]*>([\s\S]*?)<\/div>/gi
        ];

        for (const pattern of patterns) {
            html = html.replace(pattern, (match, content) => {
                const lines = paymentlines.map(line => {
                    let lineHtml = content;

                    const name = line.name || line.payment_method || '';
                    const amount = parseFloat(line.amount || 0);

                    lineHtml = lineHtml.replace(/line\.name/g, name);
                    lineHtml = lineHtml.replace(/line\.amount/g, amount.toFixed(2) + ' AED');

                    return lineHtml;
                });

                return lines.join('');
            });
        }

        return html;
    },

    /**
     * Clean QWeb directives from HTML
     * @private
     */
    _cleanQWebDirectives(html) {
        // Remove all t- attributes
        const directives = [
            't-if', 't-else', 't-elif', 't-foreach', 't-as', 't-key',
            't-esc', 't-out', 't-raw', 't-set', 't-value',
            't-att-src', 't-att-href', 't-att-class', 't-att-id'
        ];

        for (const directive of directives) {
            const pattern = new RegExp(`\\s*${directive}\\s*=\\s*['"][^'"]*['"]`, 'gi');
            html = html.replace(pattern, '');
        }

        return html;
    }
});

// Patch the template to use our custom content
patch(OrderReceipt, {
    template: xml`
        <t t-name="OrderReceipt" owl="1">
            <t t-if="isCustomReceiptEnabled and customReceiptHtml">
                <div class="pos-receipt custom-receipt" t-out="customReceiptHtml"/>
            </t>
            <t t-else="">
                <t t-call-assets="point_of_sale.OrderReceipt.assets"/>
            </t>
        </t>
    `
});