/** @odoo-module **/

import paymentForm from '@payment/js/payment_form';
import { patch } from "@web/core/utils/patch";

patch(paymentForm, {
    /**
     * Override to handle COD payment method without redirect
     */
    async _processPayment(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        // Get the selected payment option
        const checkedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');
        const paymentOptionId = parseInt(checkedRadio.dataset.paymentOptionId);
        const paymentMethodCode = checkedRadio.dataset.paymentOptionCode;
        
        // If COD is selected, handle it differently
        if (paymentMethodCode === 'cod') {
            // Get the form data
            const formData = new FormData(ev.target);
            
            // Prepare the transaction
            await this._prepareTransactionRouteParams(paymentMethodCode, paymentOptionId, formData);
            
            // For COD, we just need to create the transaction and redirect
            const processingValues = {
                'payment_option_id': paymentOptionId,
                'reference': formData.get('reference'),
                'amount': formData.get('amount'),
                'currency_id': formData.get('currency_id'),
                'partner_id': formData.get('partner_id'),
                'flow': 'redirect',
                'tokenization_requested': false,
                'landing_route': formData.get('landing_route'),
                'is_validation': false,
            };

            // Create transaction
            const response = await this.rpc('/payment/transaction', processingValues);
            
            if (response.redirect_url) {
                window.location = response.redirect_url;
            } else {
                // For COD, redirect directly to status page
                window.location = '/payment/status';
            }
            
            return;
        }
        
        // For other payment methods, use the original method
        return super._processPayment(ev);
    },

    /**
     * Override to skip redirect form for COD
     */
    async _processRedirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (paymentMethodCode === 'cod') {
            // For COD, we don't need redirect form processing
            // Just redirect to status page
            window.location = '/payment/status';
            return;
        }
        
        return super._processRedirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues);
    },
});