/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.CODInstantUpdate = publicWidget.Widget.extend({
    selector: '.o_payment_form',
    events: {
        'change input[name="o_payment_radio"]': '_onPaymentMethodChange',
    },

    /**
     * @override
     */
    start() {
        this._super(...arguments);
        this._checkInitialCOD();
        return Promise.resolve();
    },

    /**
     * Check if COD is already selected on page load
     */
    async _checkInitialCOD() {
        const selectedRadio = this.el.querySelector('input[name="o_payment_radio"]:checked');
        if (selectedRadio && selectedRadio.dataset.paymentOptionCode === 'cod') {
            await this._handleCODSelection(selectedRadio);
        }
    },

    /**
     * Handle payment method change
     */
    async _onPaymentMethodChange(ev) {
        const selectedRadio = ev.currentTarget;
        const paymentCode = selectedRadio.dataset.paymentOptionCode;
        const providerId = selectedRadio.dataset.paymentOptionProviderId;

        if (paymentCode === 'cod') {
            await this._handleCODSelection(selectedRadio);
        } else {
            // Remove COD fee if another payment method is selected
            await this._removeCODFee();
        }
    },

    /**
     * Handle COD selection
     */
    async _handleCODSelection(radioElement) {
        const providerId = radioElement.dataset.paymentOptionProviderId;

        // Show loading
        this._showLoading('جاري إضافة رسوم التوصيل...');

        try {
            // Call server to add COD fee
            const result = await jsonrpc('/payment/cod/update-fee', {
                provider_id: parseInt(providerId),
                add_fee: true
            });

            if (result.success) {
                // Update displayed amounts
                this._updateAmounts(result);

                // Show success message
                this._showMessage('success', 'تم إضافة رسوم التوصيل بنجاح');
            } else {
                this._showMessage('danger', result.error || 'حدث خطأ أثناء إضافة الرسوم');
            }
        } catch (error) {
            console.error('Error adding COD fee:', error);
            this._showMessage('danger', 'حدث خطأ في الاتصال');
        } finally {
            this._hideLoading();
        }
    },

    /**
     * Remove COD fee when another payment method is selected
     */
    async _removeCODFee() {
        this._showLoading('جاري إزالة رسوم التوصيل...');

        try {
            const result = await jsonrpc('/payment/cod/update-fee', {
                add_fee: false
            });

            if (result.success) {
                this._updateAmounts(result);
                this._showMessage('info', 'تم إزالة رسوم التوصيل');
            }
        } catch (error) {
            console.error('Error removing COD fee:', error);
        } finally {
            this._hideLoading();
        }
    },

    /**
     * Update displayed amounts
     */
    _updateAmounts(data) {
        // Update order total
        const totalElements = this.el.querySelectorAll('.oe_currency_value');
        totalElements.forEach(el => {
            if (el.closest('.o_total_amount')) {
                el.textContent = data.amount_total_formatted;
            }
        });

        // Update order lines if fee was added
        if (data.fee_line_html) {
            const orderLinesContainer = this.el.querySelector('#order_summary tbody');
            if (orderLinesContainer) {
                // Remove existing COD fee line if any
                const existingFeeLine = orderLinesContainer.querySelector('.cod_fee_line');
                if (existingFeeLine) {
                    existingFeeLine.remove();
                }

                // Add new fee line
                orderLinesContainer.insertAdjacentHTML('beforeend', data.fee_line_html);
            }
        }

        // Update transaction amount in hidden field
        const amountInput = this.el.querySelector('input[name="amount"]');
        if (amountInput) {
            amountInput.value = data.amount_total;
        }
    },

    /**
     * Show loading state
     */
    _showLoading(message) {
        const submitBtn = this.el.querySelector('button[name="o_payment_submit_button"]');
        if (submitBtn) {
            this._originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fa fa-spinner fa-spin"></i> ${message}`;
        }
    },

    /**
     * Hide loading state
     */
    _hideLoading() {
        const submitBtn = this.el.querySelector('button[name="o_payment_submit_button"]');
        if (submitBtn && this._originalBtnText) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = this._originalBtnText;
        }
    },

    /**
     * Show message to user
     */
    _showMessage(type, message) {
        // Remove existing messages
        const existingMsg = this.el.querySelector('.cod-message');
        if (existingMsg) {
            existingMsg.remove();
        }

        // Create new message
        const msgDiv = document.createElement('div');
        msgDiv.className = `alert alert-${type} cod-message mt-2`;
        msgDiv.innerHTML = `
            <button type="button" class="close" data-dismiss="alert">&times;</button>
            ${message}
        `;

        // Insert message
        const paymentOptions = this.el.querySelector('.o_payment_option_cards');
        if (paymentOptions) {
            paymentOptions.parentNode.insertBefore(msgDiv, paymentOptions);

            // Auto-hide after 3 seconds
            setTimeout(() => {
                msgDiv.remove();
            }, 3000);
        }
    }
});

export default publicWidget.registry.CODInstantUpdate;