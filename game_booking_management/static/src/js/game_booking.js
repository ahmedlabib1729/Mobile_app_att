/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.GameBookingForm = publicWidget.Widget.extend({
    selector: '#gameBookingForm',
    events: {
        'click .game-card': '_onGameSelect',
        'click .schedule-card:not(.full)': '_onScheduleSelect',
        'click #nextBtn': '_onNextClick',
        'click #prevBtn': '_onPrevClick',
        'submit': '_onFormSubmit',
        'input #mobile': '_onMobileInput',
    },

    start() {
        this._super(...arguments);
        this.currentStep = 1;
        this.selectedGameId = null;
        this.selectedScheduleId = null;
        this._updateProgressIndicators();
        return Promise.resolve();
    },

    _onGameSelect(ev) {
        // Remove previous selection
        this.$('.game-card').removeClass('selected');

        // Add selection to clicked card
        const $card = $(ev.currentTarget);
        $card.addClass('selected');

        // Store selected game ID
        this.selectedGameId = $card.data('game-id');
        this.$('#selected_game_id').val(this.selectedGameId);

        // Enable next button
        this.$('#nextBtn').prop('disabled', false);
    },

    _onScheduleSelect(ev) {
        // Remove previous selection
        this.$('.schedule-card').removeClass('selected');

        // Add selection to clicked card
        const $card = $(ev.currentTarget);
        $card.addClass('selected');

        // Store selected schedule ID
        this.selectedScheduleId = $card.data('schedule-id');
        this.$('#selected_schedule_id').val(this.selectedScheduleId);

        // Enable next button
        this.$('#nextBtn').prop('disabled', false);
    },

    _onNextClick(ev) {
        ev.preventDefault();

        if (this.currentStep === 1 && !this.selectedGameId) {
            this._showError('يرجى اختيار اللعبة أولاً');
            return;
        }

        if (this.currentStep === 2 && !this.selectedScheduleId) {
            this._showError('يرجى اختيار الموعد أولاً');
            return;
        }

        if (this.currentStep < 3) {
            this.currentStep++;
            this._updateFormStep();

            // Load schedules when moving to step 2
            if (this.currentStep === 2) {
                this._loadSchedules();
            }
        }
    },

    _onPrevClick(ev) {
        ev.preventDefault();

        if (this.currentStep > 1) {
            this.currentStep--;
            this._updateFormStep();
        }
    },

    _updateFormStep() {
        // Hide all steps
        this.$('.form-step').removeClass('active');

        // Show current step
        this.$('#step' + this.currentStep).addClass('active');

        // Update progress indicators
        this._updateProgressIndicators();

        // Update navigation buttons
        this._updateNavigationButtons();
    },

    _updateProgressIndicators() {
        // Remove all active and completed classes
        this.$('.progress-step').removeClass('active completed');

        // Add active class to current step
        this.$('#step' + this.currentStep + '-indicator').addClass('active');

        // Add completed class to previous steps
        for (let i = 1; i < this.currentStep; i++) {
            this.$('#step' + i + '-indicator').addClass('completed');
        }
    },

    _updateNavigationButtons() {
        // Show/hide navigation buttons based on current step
        if (this.currentStep === 1) {
            this.$('#prevBtn').hide();
            this.$('#nextBtn').show();
            this.$('#submitBtn').hide();
        } else if (this.currentStep === 3) {
            this.$('#prevBtn').show();
            this.$('#nextBtn').hide();
            this.$('#submitBtn').show();
        } else {
            this.$('#prevBtn').show();
            this.$('#nextBtn').show();
            this.$('#submitBtn').hide();
        }
    },

    async _loadSchedules() {
        const $container = this.$('#schedules-container');

        // Show loading state
        $container.html('<div class="text-center"><i class="fa fa-spinner fa-spin fa-3x"></i><p>جاري تحميل المواعيد...</p></div>');

        try {
            // Fetch schedules from server using rpc
            const data = await rpc(`/game-booking/get-schedules/${this.selectedGameId}`);

            if (data.schedules && data.schedules.length > 0) {
                let html = '';
                data.schedules.forEach(schedule => {
                    const isFullClass = schedule.available_slots === 0 ? 'full' : '';
                    const slotText = schedule.available_slots > 0
                        ? 'متاح ' + schedule.available_slots + ' من ' + schedule.max_players
                        : 'مكتمل';

                    html += '<div class="schedule-card ' + isFullClass + '" data-schedule-id="' + schedule.id + '">';
                    html += '<div class="schedule-date">' + schedule.date_display + '</div>';
                    html += '<div class="schedule-time">' + schedule.time + '</div>';
                    html += '<div class="schedule-slots">' + slotText + '</div>';
                    html += '</div>';
                });
                $container.html(html);
            } else {
                $container.html('<div class="alert alert-warning text-center">لا توجد مواعيد متاحة حالياً لهذه اللعبة</div>');
            }
        } catch (error) {
            $container.html('<div class="alert alert-danger text-center">حدث خطأ في تحميل المواعيد</div>');
            console.error('Error loading schedules:', error);
        }
    },

    _onMobileInput(ev) {
        const $input = $(ev.currentTarget);
        let value = $input.val();

        // Auto-format mobile number
        if (value && !value.startsWith('+966')) {
            if (value.startsWith('966')) {
                $input.val('+' + value);
            } else if (value.startsWith('0')) {
                $input.val('+966' + value.substring(1));
            } else if (value.startsWith('5')) {
                $input.val('+966' + value);
            }
        }
    },

    async _onFormSubmit(ev) {
        ev.preventDefault();

        // Validate form
        if (!this._validateForm()) {
            return;
        }

        // Show loading state
        this.$('#submitBtn').addClass('loading').prop('disabled', true);

        // Prepare data
        const formData = {
            player_name: this.$('#player_name').val().trim(),
            mobile: this.$('#mobile').val().trim(),
            schedule_id: this.selectedScheduleId,
        };

        try {
            // Submit booking using rpc
            const result = await rpc('/game-booking/submit', formData);

            if (result.success) {
                this._showSuccess(result.message);
                // Reset form after 3 seconds
                setTimeout(() => {
                    $('#successModal').modal('hide');
                    window.location.reload();
                }, 3000);
            } else {
                this._showError(result.error || 'حدث خطأ في معالجة الحجز');
            }
        } catch (error) {
            this._showError('حدث خطأ في الاتصال بالخادم');
            console.error('Booking submission error:', error);
        } finally {
            this.$('#submitBtn').removeClass('loading').prop('disabled', false);
        }
    },

    _validateForm() {
        const playerName = this.$('#player_name').val().trim();
        const mobile = this.$('#mobile').val().trim();

        if (!playerName) {
            this._showError('يرجى إدخال اسمك');
            this.$('#player_name').focus();
            return false;
        }

        if (!mobile) {
            this._showError('يرجى إدخال رقم الجوال');
            this.$('#mobile').focus();
            return false;
        }

        // Validate mobile format
        const mobileRegex = /^\+966[0-9]{9}$/;
        if (!mobileRegex.test(mobile)) {
            this._showError('رقم الجوال غير صحيح. يجب أن يكون بالصيغة: +966XXXXXXXXX');
            this.$('#mobile').focus();
            return false;
        }

        return true;
    },

    _showSuccess(message) {
        $('#successModal .modal-body p').text(message || 'تم الحجز بنجاح!');
        $('#successModal').modal('show');
    },

    _showError(message) {
        $('#errorMessage').text(message || 'حدث خطأ!');
        $('#errorModal').modal('show');
    },

    _resetForm() {
        // Reset form values using safer method
        const formElement = this.$('#gameBookingForm').get(0);
        if (formElement && formElement.reset) {
            formElement.reset();
        }

        // Reset selections
        this.$('.game-card').removeClass('selected');
        this.$('.schedule-card').removeClass('selected');
        this.selectedGameId = null;
        this.selectedScheduleId = null;

        // Reset to first step
        this.currentStep = 1;
        this._updateFormStep();

        // Clear schedules
        this.$('#schedules-container').empty();

        // Close modal
        $('#successModal').modal('hide');
    },
});

export default publicWidget.registry.GameBookingForm;