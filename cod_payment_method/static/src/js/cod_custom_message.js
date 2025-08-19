/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.CODStatusMessage = publicWidget.Widget.extend({
    selector: '.o_payment_status',

    /**
     * @override
     */
    start() {
        this._super(...arguments);
        this._updateCODMessage();
        return Promise.resolve();
    },

    _updateCODMessage() {
        // Check if we have COD transaction info in the page
        const referenceEl = this.el.querySelector('dd:last-child');
        if (!referenceEl) return;

        const reference = referenceEl.textContent.trim();

        // Check if this is a COD transaction (you may need to adjust this check)
        if (reference && reference.startsWith('IQRA')) {
            // Hide the default message
            const defaultAlert = this.el.querySelector('.alert-info');
            if (defaultAlert) {
                defaultAlert.style.display = 'none';
            }

            // Add our custom message
            const customMessage = document.createElement('div');
            customMessage.className = 'alert alert-success text-center mt-3';
            customMessage.innerHTML = `
                <h3>
                    <i class="fa fa-check-circle"></i> تم استلام طلبك بنجاح
                </h3>
                <p class="mt-3 mb-1">
                    رقم الطلب: <strong>${reference}</strong>
                </p>
                <p>
                    سيتم التواصل معك في أقرب وقت
                </p>
            `;

            // Insert the custom message
            this.el.insertBefore(customMessage, this.el.firstChild);
        }
    }
});

export default publicWidget.registry.CODStatusMessage;