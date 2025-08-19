/** @odoo-module **/
// quran_center/static/src/js/website_enrollment.js

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.QuranEnrollmentForm = publicWidget.Widget.extend({
    selector: '.enrollment-form-custom, form[action="/enrollment/submit"]', // تحديد أكثر دقة
    events: {
        'change input[name="memorization_start_page"]': '_onPageChange',
        'change input[name="memorization_end_page"]': '_onPageChange',
        'input input[name="memorization_start_page"]': '_onPageChange',
        'input input[name="memorization_end_page"]': '_onPageChange',
        'keyup input[name="memorization_start_page"]': '_onPageChange',
        'keyup input[name="memorization_end_page"]': '_onPageChange',
        'change input[name="birth_date"]': '_validateAge',
        'change input[name="attachments"]': '_validateAttachments',
        'change input[name="emirates_id_file"]': '_validateSingleFile',
        'change input[name="residence_file"]': '_validateSingleFile',
        'change input[name="passport_file"]': '_validateSingleFile',
        'change input[name="other_document_file"]': '_validateSingleFile',
        'input input[name="id_number"]': '_formatEmiratesId',
        'keydown input[name="id_number"]': '_handleEmiratesIdKeydown',
        'paste input[name="id_number"]': '_handleEmiratesIdPaste',
        'submit': '_onSubmit',
    },

    start() {
        console.log('QuranEnrollmentForm widget started'); // للتأكد من التحميل
        this._super(...arguments);
        this._initializeForm();
    },

    _initializeForm() {
        console.log('Initializing form...');
        this._validateAge();
        this._setupFileValidation();
        this._setupEmiratesIdField();
        this._setupPageFieldsUI();
        this._calculateTotalPages(); // حساب عند التحميل

        // إضافة مستمعين مباشرين للتأكد
        const startPageInput = this.$('input[name="memorization_start_page"]');
        const endPageInput = this.$('input[name="memorization_end_page"]');

        console.log('Start page input found:', startPageInput.length > 0);
        console.log('End page input found:', endPageInput.length > 0);

        // ربط الأحداث مباشرة
        if (startPageInput.length && endPageInput.length) {
            const self = this;

            startPageInput.on('input change keyup', function() {
                console.log('Start page changed to:', $(this).val());
                self._calculateTotalPages();
            });

            endPageInput.on('input change keyup', function() {
                console.log('End page changed to:', $(this).val());
                self._calculateTotalPages();
            });
        }
    },

    _setupPageFieldsUI() {
        // الحصول على حقل عدد الصفحات
        const totalPagesField = this.$('input[name="current_memorized_pages"]');

        if (totalPagesField.length) {
            console.log('Total pages field found');

            // جعله للقراءة فقط
            totalPagesField.prop('readonly', true);
            totalPagesField.attr('readonly', 'readonly');

            // تنسيق مميز
            totalPagesField.css({
                'background-color': '#f8f9fa',
                'cursor': 'not-allowed',
                'font-weight': 'bold',
                'color': '#495057',
                'border': '2px solid #dee2e6'
            });

            // إضافة رسالة توضيحية إذا لم تكن موجودة
            if (!totalPagesField.siblings('.auto-calc-note').length) {
                totalPagesField.closest('.form-group, .col-md-4, .mb-3').append(
                    '<small class="form-text text-info auto-calc-note mt-1">' +
                    '<i class="fa fa-info-circle"></i> يُحسب تلقائياً من نطاق الصفحات' +
                    '</small>'
                );
            }
        } else {
            console.log('Total pages field NOT found');
        }
    },

    _calculateTotalPages() {
        console.log('Calculating total pages...');

        // الحصول على القيم
        const startPageInput = this.$('input[name="memorization_start_page"]');
        const endPageInput = this.$('input[name="memorization_end_page"]');
        const totalPagesInput = this.$('input[name="current_memorized_pages"]');

        if (!startPageInput.length || !endPageInput.length || !totalPagesInput.length) {
            console.log('Some inputs not found:', {
                start: startPageInput.length,
                end: endPageInput.length,
                total: totalPagesInput.length
            });
            return;
        }

        const startPage = parseInt(startPageInput.val()) || 0;
        const endPage = parseInt(endPageInput.val()) || 0;

        console.log('Start page:', startPage, 'End page:', endPage);

        let totalPages = 0;

        // حساب عدد الصفحات
        if (startPage > 0 && endPage > 0) {
            if (endPage >= startPage) {
                // حفظ عادي
                totalPages = endPage - startPage + 1;
                console.log('Normal range calculation:', totalPages);
            } else {
                // حفظ متقاطع (من آخر المصحف للبداية)
                totalPages = startPage - endPage + 1;
                console.log('Cross-Quran calculation:', totalPages);
            }
        }

        console.log('Total pages calculated:', totalPages);

        // تحديث الحقل
        totalPagesInput.val(totalPages);

        // إضافة تأثير بصري
        totalPagesInput.css('background-color', '#ffffcc');
        setTimeout(() => {
            totalPagesInput.css('background-color', '#f8f9fa');
        }, 500);

        // عرض معلومات الحساب
        this._showPageCalculationInfo(startPage, endPage, totalPages);
    },

    _showPageCalculationInfo(startPage, endPage, totalPages) {
        // إزالة الرسائل السابقة
        this.$('.page-calculation-info').remove();

        const totalPagesField = this.$('input[name="current_memorized_pages"]');
        const container = totalPagesField.closest('.form-group, .col-md-4, .mb-3');

        if (totalPages > 0) {
            let message = '';

            if (endPage >= startPage) {

            } else if (endPage < startPage && endPage > 0) {
                const part1 = 604 - startPage + 1;

            }

            if (message && container.length) {
                container.append(message);
            }
        }

        // التحقق من صحة النطاق
        this._validatePageRange(startPage, endPage, totalPages);
    },

    _validatePageRange(startPage, endPage, totalPages) {
        // إزالة رسائل الخطأ السابقة
        this.$('.page-range-error').remove();

        const startPageInput = this.$('input[name="memorization_start_page"]');
        const endPageInput = this.$('input[name="memorization_end_page"]');

        let hasError = false;
        let errorMessage = '';

        // التحقق من النطاق
        if (startPage > 0 && (startPage < 1 || startPage > 604)) {
            hasError = true;
            errorMessage = 'صفحة البداية يجب أن تكون بين 1 و 604';
            startPageInput.addClass('is-invalid');
        } else {
            startPageInput.removeClass('is-invalid');
        }

        if (endPage > 0 && (endPage < 1 || endPage > 604)) {
            hasError = true;
            if (errorMessage) errorMessage += '<br>';
            errorMessage += 'صفحة النهاية يجب أن تكون بين 1 و 604';
            endPageInput.addClass('is-invalid');
        } else {
            endPageInput.removeClass('is-invalid');
        }

        if (totalPages > 604) {
            hasError = true;
            if (errorMessage) errorMessage += '<br>';
            errorMessage += 'عدد الصفحات الإجمالي لا يمكن أن يتجاوز 604 صفحة';
        }

        if (hasError && errorMessage) {
            const errorDiv = `
                <div class="alert alert-danger page-range-error mt-2">
                    <i class="fa fa-exclamation-circle"></i> ${errorMessage}
                </div>`;
            endPageInput.closest('.form-group, .col-md-4, .mb-3').append(errorDiv);
        }
    },

    _onPageChange(ev) {
        console.log('Page change event triggered');
        this._calculateTotalPages();
    },

    // باقي الدوال كما هي...
    _setupEmiratesIdField() {
        const idInput = this.$('input[name="id_number"]');
        if (idInput.length) {
            idInput.attr('maxlength', '18');
            idInput.attr('placeholder', '784-XXXX-XXXXXXX-X');
        }
    },

    _formatEmiratesId(ev) {
        const input = ev.currentTarget;
        let value = input.value.replace(/[^\d]/g, '');

        if (value.length > 0 && !value.startsWith('784')) {
            this._showEmiratesIdError('رقم الهوية يجب أن يبدأ بـ 784');
            return;
        }

        let formatted = '';
        if (value.length > 0) {
            formatted = value.substring(0, 3);
            if (value.length > 3) {
                formatted += '-' + value.substring(3, 7);
                if (value.length > 7) {
                    formatted += '-' + value.substring(7, 14);
                    if (value.length > 14) {
                        formatted += '-' + value.substring(14, 15);
                    }
                }
            }
        }

        input.value = formatted;

        if (value.length === 15) {
            this._hideEmiratesIdError();
        } else if (value.length > 0) {
            this._showEmiratesIdError('رقم الهوية غير مكتمل - يجب أن يكون 15 رقم');
        }
    },

    _validateAge() {
        const birthDate = this.$('input[name="birth_date"]').val();
        if (birthDate) {
            const today = new Date();
            const birth = new Date(birthDate);
            let age = today.getFullYear() - birth.getFullYear();
            const m = today.getMonth() - birth.getMonth();

            if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) {
                age--;
            }

            if (age < 5) {
                this._showWarning('الحد الأدنى للعمر هو 5 سنوات');
            } else if (age > 100) {
                this._showWarning('يرجى التحقق من تاريخ الميلاد');
            } else {
                this._hideWarning();
            }
        }
    },

    _onSubmit(ev) {
        const totalPages = parseInt(this.$('input[name="current_memorized_pages"]').val()) || 0;

        if (totalPages === 0) {
            ev.preventDefault();
            this._showError('يجب تحديد نطاق الصفحات المحفوظة');

            const memorization_section = this.$('input[name="memorization_start_page"]').closest('.card');
            if (memorization_section.length) {
                $('html, body').animate({
                    scrollTop: memorization_section.offset().top - 100
                }, 'fast');
            }
            return false;
        }
    },

    _showError(message) {
        const $alert = $('<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
                      message +
                      '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
                      '</div>');
        this.$el.prepend($alert);
        $('html, body').animate({ scrollTop: 0 }, 'fast');
    },

    _showWarning(message) {
        if (!this.$('.age-warning').length) {
            this.$('input[name="birth_date"]').after('<div class="age-warning text-warning mt-1">' + message + '</div>');
        } else {
            this.$('.age-warning').text(message);
        }
    },

    _hideWarning() {
        this.$('.age-warning').remove();
    },

    _showEmiratesIdError(message) {
        const idInput = this.$('input[name="id_number"]');
        idInput.addClass('is-invalid');
        idInput.siblings('.invalid-feedback').remove();
        idInput.after(`<div class="invalid-feedback">${message}</div>`);
    },

    _hideEmiratesIdError() {
        const idInput = this.$('input[name="id_number"]');
        idInput.removeClass('is-invalid');
        idInput.siblings('.invalid-feedback').remove();
    },

    _setupFileValidation() {
        // Implementation as before
    },

    _validateSingleFile(ev) {
        // Implementation as before
    },

    _validateAttachments() {
        // Implementation as before
    },

    _handleEmiratesIdKeydown(ev) {
        const key = ev.key;
        if (['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight'].includes(key)) {
            return;
        }
        if (!/^\d$/.test(key)) {
            ev.preventDefault();
        }
    },

    _handleEmiratesIdPaste(ev) {
        ev.preventDefault();
        const pastedText = (ev.originalEvent.clipboardData || window.clipboardData).getData('text');
        const numbers = pastedText.replace(/[^\d]/g, '');
        if (!numbers.startsWith('784')) {
            this._showEmiratesIdError('رقم الهوية يجب أن يبدأ بـ 784');
            return;
        }
        const truncated = numbers.substring(0, 15);
        ev.currentTarget.value = truncated;
        this._formatEmiratesId(ev);
    }
});

// تشغيل الكود عند تحميل الصفحة أيضاً
$(document).ready(function() {
    console.log('Document ready - checking for enrollment form...');

    // البحث عن النموذج
    const form = $('form[action="/enrollment/submit"]');

    if (form.length) {
        console.log('Enrollment form found, initializing...');

        // ربط الأحداث مباشرة
        const startPage = $('input[name="memorization_start_page"]');
        const endPage = $('input[name="memorization_end_page"]');
        const totalPages = $('input[name="current_memorized_pages"]');

        function calculatePages() {
            const start = parseInt(startPage.val()) || 0;
            const end = parseInt(endPage.val()) || 0;
            let total = 0;

            if (start > 0 && end > 0) {
                if (end >= start) {
                    total = end - start + 1;
                } else {
                    total = (604 - start + 1) + end;
                }
            }

            totalPages.val(total);
            console.log('Pages calculated:', start, end, total);
        }

        // ربط الأحداث
        startPage.on('input change keyup', calculatePages);
        endPage.on('input change keyup', calculatePages);

        // حساب أولي
        calculatePages();

        // جعل حقل المجموع للقراءة فقط
        totalPages.prop('readonly', true).css({
            'background-color': '#f8f9fa',
            'cursor': 'not-allowed'
        });
    }
});