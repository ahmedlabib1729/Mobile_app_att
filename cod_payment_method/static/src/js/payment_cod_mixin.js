/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import PaymentForm from '@payment/js/payment_form';

patch(PaymentForm.prototype, {
    /**
     * Override to handle COD without redirect
     */
    async _processRedirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        // If it's COD, redirect to our custom thank you page
        if (paymentMethodCode === 'cod' || providerCode === 'cod') {
            // Get the reference from the current transaction
            const reference = processingValues?.reference || this.txContext?.reference;
            if (reference) {
                // Redirect to our custom COD thank you page
                window.location.href = `/payment/cod/thank-you/${reference}`;
            } else {
                // Fallback to status page
                window.location.href = '/payment/status';
            }
            return;
        }

        // For other methods, call parent
        return super._processRedirectFlow(...arguments);
    },
});