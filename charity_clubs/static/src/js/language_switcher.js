// charity_clubs/static/src/js/language_switcher.js

/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class LanguageSwitcher {
    static switchLanguage(lang) {
        // Set cookie
        document.cookie = `frontend_lang=${lang};path=/;max-age=31536000`;

        // Reload with new language
        const url = new URL(window.location.href);
        url.searchParams.set('lang', lang);
        window.location.href = url.toString();
    }
}

// Make it globally available
window.switchLanguage = LanguageSwitcher.switchLanguage;