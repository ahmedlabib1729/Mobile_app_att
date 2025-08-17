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
        'change #emirates_id_file': '_validateSingleFile',
        'change #residence_file': '_validateSingleFile',
        'change #passport_file': '_validateSingleFile',
        'change #other_document_file': '_validateSingleFile',
        'input #id_number': '_formatEmiratesId',
        'keydown #id_number': '_handleEmiratesIdKeydown',
        'paste #id_number': '_handleEmiratesIdPaste',
        'submit': '_onSubmit',
    },

    start() {
        this._super(...arguments);
        this._validateAge();
        this._setupFileValidation();
        this._setupEmiratesIdField();
    },

    _setupEmiratesIdField() {
        const idInput = this.$('#id_number');
        if (idInput.length) {
            // تعيين الحد الأقصى للأحرف
            idInput.attr('maxlength', '18'); // 784-XXXX-XXXXXXX-X
            // إضافة placeholder
            idInput.attr('placeholder', '784-XXXX-XXXXXXX-X');
        }
    },

    _formatEmiratesId(ev) {
        const input = ev.currentTarget;
        let value = input.value.replace(/[^\d]/g, ''); // إزالة كل شيء عدا الأرقام

        // التحقق من أن الرقم يبدأ بـ 784
        if (value.length > 0 && !value.startsWith('784')) {
            this._showEmiratesIdError('رقم الهوية يجب أن يبدأ بـ 784');
            return;
        }

        // تطبيق التنسيق: 784-XXXX-XXXXXXX-X
        let formatted = '';

        if (value.length > 0) {
            // الجزء الأول: 784
            formatted = value.substring(0, 3);

            if (value.length > 3) {
                // إضافة الشرطة الأولى والجزء الثاني (4 أرقام)
                formatted += '-' + value.substring(3, 7);

                if (value.length > 7) {
                    // إضافة الشرطة الثانية والجزء الثالث (7 أرقام)
                    formatted += '-' + value.substring(7, 14);

                    if (value.length > 14) {
                        // إضافة الشرطة الثالثة والرقم الأخير
                        formatted += '-' + value.substring(14, 15);
                    }
                }
            }
        }

        // تحديث القيمة في الحقل
        input.value = formatted;

        // التحقق من اكتمال الرقم
        if (value.length === 15) {
            this._hideEmiratesIdError();
        } else if (value.length > 0) {
            this._showEmiratesIdError('رقم الهوية غير مكتمل - يجب أن يكون 15 رقم');
        }
    },

    _handleEmiratesIdKeydown(ev) {
        const input = ev.currentTarget;
        const key = ev.key;
        const value = input.value;

        // السماح بمفاتيح التحكم
        if (['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight'].includes(key)) {
            return;
        }

        // السماح بالأرقام فقط
        if (!/^\d$/.test(key)) {
            ev.preventDefault();
            return;
        }

        // منع إدخال أكثر من 15 رقم
        const numbers = value.replace(/[^\d]/g, '');
        if (numbers.length >= 15) {
            ev.preventDefault();
        }
    },

    _handleEmiratesIdPaste(ev) {
        ev.preventDefault();

        // الحصول على النص المنسوخ
        const pastedText = (ev.originalEvent.clipboardData || window.clipboardData).getData('text');
        const numbers = pastedText.replace(/[^\d]/g, '');

        // التحقق من أن الرقم يبدأ بـ 784
        if (!numbers.startsWith('784')) {
            this._showEmiratesIdError('رقم الهوية يجب أن يبدأ بـ 784');
            return;
        }

        // أخذ أول 15 رقم فقط
        const truncated = numbers.substring(0, 15);

        // محاكاة الإدخال لتطبيق التنسيق
        ev.currentTarget.value = truncated;
        this._formatEmiratesId(ev);
    },

    _showEmiratesIdError(message) {
        const idInput = this.$('#id_number');
        idInput.addClass('is-invalid');

        // إزالة رسالة الخطأ السابقة
        idInput.siblings('.invalid-feedback').remove();

        // إضافة رسالة الخطأ الجديدة
        idInput.after(`<div class="invalid-feedback">${message}</div>`);
    },

    _hideEmiratesIdError() {
        const idInput = this.$('#id_number');
        idInput.removeClass('is-invalid');
        idInput.siblings('.invalid-feedback').remove();
    },

    _setupFileValidation() {
        // إضافة رسائل للملفات عند التحميل
        const fileInputs = ['emirates_id_file', 'residence_file', 'passport_file', 'other_document_file'];
        fileInputs.forEach(inputId => {
            const input = this.$(`#${inputId}`);
            if (input.length) {
                input.after(`<div class="file-info-${inputId} text-success mt-1" style="display: none;"></div>`);
            }
        });
    },

    _validateSingleFile(ev) {
        const input = ev.currentTarget;
        const inputId = input.id;
        const file = input.files[0];
        const maxSize = 5 * 1024 * 1024; // 5MB
        const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];

        // للمستندات الأخرى نسمح بملفات Word أيضاً
        if (inputId === 'other_document_file') {
            allowedTypes.push('application/msword');
            allowedTypes.push('application/vnd.openxmlformats-officedocument.wordprocessingml.document');
        }

        const infoDiv = this.$(`.file-info-${inputId}`);

        if (file) {
            // التحقق من الحجم
            if (file.size > maxSize) {
                this._showFileError(input, 'حجم الملف يتجاوز 5 ميجابايت');
                input.value = '';
                infoDiv.hide();
                return;
            }

            // التحقق من النوع
            const fileExtension = file.name.split('.').pop().toLowerCase();
            const isValidType = allowedTypes.includes(file.type) ||
                              ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'].includes(fileExtension);

            if (!isValidType) {
                this._showFileError(input, 'نوع الملف غير مسموح');
                input.value = '';
                infoDiv.hide();
                return;
            }

            // عرض معلومات الملف
            const fileSize = (file.size / 1024 / 1024).toFixed(2);
            infoDiv.html(`<i class="fa fa-check-circle"></i> ${file.name} (${fileSize} MB)`);
            infoDiv.show();
            this._hideFileError(input);
        } else {
            infoDiv.hide();
        }
    },

    _showFileError(input, message) {
        const $input = $(input);
        $input.addClass('is-invalid');

        // إزالة رسالة الخطأ السابقة إن وجدت
        $input.siblings('.invalid-feedback').remove();

        // إضافة رسالة الخطأ الجديدة
        $input.after(`<div class="invalid-feedback">${message}</div>`);
    },

    _hideFileError(input) {
        const $input = $(input);
        $input.removeClass('is-invalid');
        $input.siblings('.invalid-feedback').remove();
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
        // التحقق من رقم الهوية الإماراتية
        const idNumber = this.$('#id_number').val();
        const idNumberDigits = idNumber.replace(/[^\d]/g, '');

        if (!idNumberDigits.startsWith('784')) {
            ev.preventDefault();
            this._showError('رقم الهوية يجب أن يبدأ بـ 784');
            return false;
        }

        if (idNumberDigits.length !== 15) {
            ev.preventDefault();
            this._showError('رقم الهوية يجب أن يكون 15 رقم بالصيغة: 784-XXXX-XXXXXXX-X');
            return false;
        }

        // التحقق من رفع المستندات المطلوبة (الثلاثة الأولى فقط)
        const emiratesId = this.$('#emirates_id_file')[0].files.length > 0;
        const residence = this.$('#residence_file')[0].files.length > 0;
        const passport = this.$('#passport_file')[0].files.length > 0;
        // other_document_file اختياري - لا نتحقق منه

        let missingDocuments = [];

        if (!emiratesId) {
            missingDocuments.push('الهوية الإماراتية');
        }
        if (!residence) {
            missingDocuments.push('الإقامة');
        }
        if (!passport) {
            missingDocuments.push('جواز السفر');
        }

        if (missingDocuments.length > 0) {
            ev.preventDefault();
            this._showError('يجب رفع المستندات التالية: ' + missingDocuments.join(', '));

            // التمرير إلى قسم المستندات
            const documentsSection = this.$('.card-header:contains("المستندات المطلوبة")').parent();
            if (documentsSection.length) {
                $('html, body').animate({
                    scrollTop: documentsSection.offset().top - 100
                }, 'fast');
            }

            return false;
        }

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