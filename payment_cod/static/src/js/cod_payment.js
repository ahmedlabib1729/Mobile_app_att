odoo.define('payment_cod.cod_handler', [], function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;

    publicWidget.registry.CODFeeCalculator = publicWidget.Widget.extend({
        selector: '.o_payment_form',
        events: {
            'change input[name="o_payment_radio"]': '_onPaymentMethodChange',
        },

        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.originalTotal = 0;
                self.codFee = 0;
                self._setupFeeDisplay();
                self._captureOriginalTotal();
                self._checkInitialSelection();
            });
        },

        /**
         * Setup fee display in the payment options
         */
        _setupFeeDisplay: function() {
            var self = this;

            // Add fee display to COD payment option
            $('.o_payment_option_card').each(function() {
                var $card = $(this);
                var providerCode = $card.data('provider-code');

                if (providerCode === 'cod') {
                    // Add fee badge to the card
                    var $cardBody = $card.find('.card-body');
                    if ($cardBody.length && !$cardBody.find('.cod-fee-badge').length) {
                        var $feeBadge = $('<div class="cod-fee-badge float-end mt-2">' +
                            '<span class="badge bg-info">جاري حساب الرسوم...</span>' +
                            '</div>');
                        $cardBody.append($feeBadge);

                        // Calculate fee for this provider
                        self._calculateFeeForProvider($card);
                    }
                }
            });
        },

        /**
         * Calculate fee for a specific provider
         */
        _calculateFeeForProvider: function($card) {
            var self = this;
            var providerId = $card.data('provider-id');

            if (!providerId) {
                // Try to extract from payment option id
                var optionId = $card.data('payment-option-id');
                if (optionId) {
                    var match = optionId.match(/\/payment\/provider\/(\d+)/);
                    if (match) {
                        providerId = match[1];
                    }
                }
            }

            if (!providerId) {
                console.warn('No provider ID found for COD card');
                return;
            }

            // Get order amount
            var amount = this._getOrderAmount();
            var currencyId = this._getCurrencyId();
            var countryId = this._getCountryId();

            ajax.jsonRpc('/payment/cod/calculate_fee', 'call', {
                provider_id: providerId,
                amount: amount,
                currency_id: currencyId,
                country_id: countryId
            }).then(function(result) {
                var $badge = $card.find('.cod-fee-badge .badge');
                if (result.fee > 0) {
                    $badge.removeClass('bg-info').addClass('bg-warning text-dark');
                    $badge.html('رسوم COD: ' + (result.fee_formatted || result.fee + ' AED'));
                    $card.attr('data-cod-fee', result.fee);
                } else {
                    $badge.removeClass('bg-info').addClass('bg-success');
                    $badge.html('بدون رسوم إضافية');
                    $card.attr('data-cod-fee', '0');
                }
            }).catch(function(error) {
                console.error('Error calculating COD fee:', error);
                var $badge = $card.find('.cod-fee-badge .badge');
                $badge.removeClass('bg-info').addClass('bg-secondary');
                $badge.html('غير متاح');
            });
        },

        /**
         * Capture the original total amount
         */
        _captureOriginalTotal: function() {
            // Look for the total in different possible locations
            var $totalElement = $('.oe_website_sale_total_line .monetary_field, .fw-bold .monetary_field').last();
            if ($totalElement.length) {
                var totalText = $totalElement.text().replace(/[^\d.,]/g, '').replace(',', '.');
                this.originalTotal = parseFloat(totalText) || 0;
            } else {
                // Try to get from order summary
                this.originalTotal = this._getOrderAmount();
            }
            console.log('Original total captured:', this.originalTotal);
        },

        /**
         * Get order amount from the page
         */
        _getOrderAmount: function() {
            // Try multiple selectors to find the amount
            var amount = 0;

            // Try from total line
            var $total = $('.oe_website_sale_total_line .monetary_field, .fw-bold .monetary_field').last();
            if ($total.length) {
                var text = $total.text().replace(/[^\d.,]/g, '').replace(',', '.');
                amount = parseFloat(text) || 0;
            }

            // Try from hidden input
            if (!amount) {
                var $amountInput = $('input[name="amount"]');
                if ($amountInput.length) {
                    amount = parseFloat($amountInput.val()) || 0;
                }
            }

            return amount || this.originalTotal || 299.00; // fallback to the amount shown in your screenshot
        },

        /**
         * Check if COD is initially selected
         */
        _checkInitialSelection: function() {
            var $selectedRadio = $('input[name="o_payment_radio"]:checked');
            if ($selectedRadio.length) {
                var $card = $selectedRadio.closest('.o_payment_option_card');
                if ($card.data('provider-code') === 'cod') {
                    this._showCODFee($card);
                }
            }
        },

        /**
         * Handle payment method change
         */
        _onPaymentMethodChange: function (ev) {
            var $radio = $(ev.currentTarget);
            var $card = $radio.closest('.o_payment_option_card');
            var providerCode = $card.data('provider-code');

            if (providerCode === 'cod') {
                this._showCODFee($card);
            } else {
                this._hideCODFee();
            }
        },

        /**
         * Show COD fee in summary
         */
        _showCODFee: function($card) {
            var codFee = parseFloat($card.attr('data-cod-fee')) || 0;
            this.codFee = codFee;

            var $feeRow = $('#cod_fee_row');
            if ($feeRow.length) {
                if (codFee > 0) {
                    $('#cod_fee_amount').text(codFee.toFixed(2) + ' AED');
                } else {
                    $('#cod_fee_amount').html('<span class="text-success">مجاناً</span>');
                }
                $feeRow.removeClass('d-none');

                // Update total
                this._updateTotal(this.originalTotal + codFee);
            }

            // Add visual feedback
            $('.o_payment_option_card').removeClass('border-success cod-selected');
            $card.addClass('border-success cod-selected');
        },

        /**
         * Hide COD fee from summary
         */
        _hideCODFee: function() {
            $('#cod_fee_row').addClass('d-none');
            this._updateTotal(this.originalTotal);
            $('.o_payment_option_card').removeClass('border-success cod-selected');
        },

        /**
         * Update total amount display
         */
        _updateTotal: function(newTotal) {
            // Update all total displays
            $('.oe_website_sale_total_line .monetary_field, .fw-bold .monetary_field').last().each(function() {
                $(this).text(newTotal.toFixed(2) + ' AED');
            });

            // Update payment button if exists
            var $payButton = $('button[name="o_payment_submit_button"]');
            if ($payButton.length) {
                var buttonText = $payButton.text();
                var newButtonText = buttonText.replace(/[\d.,]+\s*AED/, newTotal.toFixed(2) + ' AED');
                $payButton.text(newButtonText);
            }
        },

        /**
         * Get currency ID
         */
        _getCurrencyId: function() {
            // Try from various sources
            return $('input[name="currency_id"]').val() ||
                   $('[data-currency-id]').data('currency-id') ||
                   128; // AED default
        },

        /**
         * Get country ID
         */
        _getCountryId: function() {
            // Try from shipping address or form
            return $('select[name="country_id"]').val() ||
                   $('[data-country-id]').data('country-id') ||
                   null;
        }
    });

    return publicWidget.registry.CODFeeCalculator;
});