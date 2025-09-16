// charity_clubs/static/src/js/website_registration_language.js

/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.LanguageSwitcher = publicWidget.Widget.extend({
    selector: '.lang-switcher',
    events: {
        'click .switch-to-english': '_onSwitchToEnglish',
        'click .switch-to-arabic': '_onSwitchToArabic',
    },

    _onSwitchToEnglish: function(ev) {
        ev.preventDefault();
        this._switchLanguage('en_US');
    },

    _onSwitchToArabic: function(ev) {
        ev.preventDefault();
        this._switchLanguage('ar_001');
    },

    _switchLanguage: function(lang) {
        // Set cookie
        document.cookie = "frontend_lang=" + lang + ";path=/;SameSite=Lax;max-age=31536000";

        // Reload with new language
        var url = window.location.pathname;
        if (window.location.search) {
            // Check if lang parameter already exists
            if (window.location.search.includes('lang=')) {
                url += window.location.search.replace(/lang=[^&]*/, 'lang=' + lang);
            } else {
                url += window.location.search + '&lang=' + lang;
            }
        } else {
            url += '?lang=' + lang;
        }
        window.location.href = url;
    },
});

export default publicWidget.registry.LanguageSwitcher;