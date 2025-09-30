odoo.define('payment_cod.fee_display', ['web.public.widget'], function(require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.CODFeeDisplay = publicWidget.Widget.extend({
        selector: '.o_payment_option_card',

        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                // فقط للكارت الخاص بـ COD
                if (self.$el.text().toLowerCase().includes('cash')) {
                    self._addFeeDisplay();
                }
            });
        },

        _addFeeDisplay: function() {
            var self = this;
            // أضف مكان لعرض الرسوم
            this.$el.find('.card-body').append('<div class="cod-fee-info text-warning mt-2"></div>');

            // عند اختيار COD
            this.$('input[type="radio"]').on('change', function() {
                if ($(this).is(':checked')) {
                    self._fetchAndDisplayFee();
                }
            });
        },

        _fetchAndDisplayFee: function() {
            var self = this;
            // استدعي الـ endpoint الموجود بالفعل
            this._rpc({
                route: '/payment/cod/calculate_fee',
                params: {
                    provider_id: 1,
                    amount: this._getOrderAmount(),
                    currency_id: 128,
                    country_id: null
                }
            }).then(function(result) {
                if (result && result.fee_formatted) {
                    self.$('.cod-fee-info').html(
                        '<strong>رسوم الخدمة: ' + result.fee_formatted + '</strong>'
                    );
                }
            });
        },

        _getOrderAmount: function() {
            var total = 0;
            $('.oe_currency_value').each(function() {
                var val = parseFloat($(this).text().replace(',', ''));
                if (val > total) total = val;
            });
            return total;
        }
    });

    return publicWidget.registry.CODFeeDisplay;
});