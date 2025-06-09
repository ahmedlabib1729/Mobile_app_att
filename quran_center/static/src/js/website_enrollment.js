/** @odoo-module **/
// quran_center/static/src/js/website_enrollment.js

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.QuranEnrollmentForm = publicWidget.Widget.extend({
    selector: '.s_website_form',
    events: {
        'change #memorization_start_page': '_onPageChange',
        'change #memorization_end_page': '_onPageChange',
        'change #birth_date': '_validateAge',
        'change #attachments': '_validateAttachments',
        'submit': '_onSubmit',
    },

    start() {
        this._super(...arguments);
        this._validateAge();
    },

    _onPageChange() {
        const startPage = parseInt(this.$('#memorization_start_page').val()) || 1;
        const endPage = parseInt(this.$('#memorization_end_page').val()) || 1;

        if (endPage < startPage) {
            this.$('#memorization_end_page').val(startPage);
        }
    },

    _validateAge() {
        const birthDate = this.$('#birth_date').val();
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

    _validateAttachments() {
        const input = this.$('#attachments')[0];
        const files = input.files;
        const maxSize = 5 * 1024 * 1024; // 5MB
        const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png',
                             'application/msword',
                             'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

        let hasError = false;
        let errorMessage = '';
        const fileList = this.$('#fileList');
        const fileError = this.$('#fileError');

        // مسح القوائم السابقة
        fileList.empty();
        fileError.hide().empty();

        if (files.length > 0) {
            let fileListHtml = '<strong>الملفات المختارة:</strong><ul class="mb-0">';

            for (let i = 0; i < files.length; i++) {
                const file = files[i];

                // التحقق من الحجم
                if (file.size > maxSize) {
                    hasError = true;
                    errorMessage += `<li>الملف "${file.name}" يتجاوز الحد الأقصى المسموح (5 ميجابايت)</li>`;
                }

                // التحقق من النوع
                const fileExtension = file.name.split('.').pop().toLowerCase();
                const isValidType = allowedTypes.includes(file.type) ||
                                  ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'].includes(fileExtension);

                if (!isValidType) {
                    hasError = true;
                    errorMessage += `<li>نوع الملف "${file.name}" غير مسموح</li>`;
                } else {
                    // إضافة الملف للقائمة
                    const fileSize = (file.size / 1024 / 1024).toFixed(2);
                    fileListHtml += `<li><i class="fa fa-file-o"></i> ${file.name} (${fileSize} MB)</li>`;
                }
            }

            fileListHtml += '</ul>';

            if (!hasError) {
                fileList.html(fileListHtml);
            }
        }

        if (hasError) {
            fileError.html('<ul class="mb-0">' + errorMessage + '</ul>').show();
            input.value = ''; // مسح الملفات
            fileList.empty();
        }
    },

    _onSubmit(ev) {
        // التحقق من الاسم العربي
        const nameAr = this.$('#name_ar').val();
        const arabicPattern = /^[\u0600-\u06FF\s]+$/;
        if (!arabicPattern.test(nameAr)) {
            ev.preventDefault();
            this._showError('الاسم باللغة العربية يجب أن يحتوي على حروف عربية فقط');
            return false;
        }

        // التحقق من الاسم الإنجليزي
        const nameEn = this.$('#name_en').val();
        const englishPattern = /^[a-zA-Z\s]+$/;
        if (!englishPattern.test(nameEn)) {
            ev.preventDefault();
            this._showError('Name in English must contain English letters only');
            return false;
        }

        // التحقق من نطاق الصفحات
        const startPage = parseInt(this.$('#memorization_start_page').val());
        const endPage = parseInt(this.$('#memorization_end_page').val());

        if (startPage < 1 || startPage > 604 || endPage < 1 || endPage > 604) {
            ev.preventDefault();
            this._showError('الصفحات يجب أن تكون بين 1 و 604');
            return false;
        }
    },

    _showWarning(message) {
        if (!this.$('.age-warning').length) {
            this.$('#birth_date').after('<div class="age-warning text-warning mt-1">' + message + '</div>');
        } else {
            this.$('.age-warning').text(message);
        }
    },

    _hideWarning() {
        this.$('.age-warning').remove();
    },

    _showError(message) {
        const $alert = $('<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
                      message +
                      '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
                      '</div>');
        this.$el.prepend($alert);
        $('html, body').animate({ scrollTop: 0 }, 'fast');
    }
});