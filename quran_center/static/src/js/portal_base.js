/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.QuranStudentPortal = publicWidget.Widget.extend({
    selector: '.student-portal',
    events: {
        'click .btn-join-session': '_onJoinSession',
        'click .filter-tab': '_onFilterChange',
        'click .btn-refresh': '_onRefreshData',
    },

    start() {
        this._super(...arguments);
        this._initializePortal();
        this._checkActiveSession();
        this._initializeCountdown();
    },

    /**
     * Initialize portal components
     */
    _initializePortal() {
        // Initialize tooltips
        $('[data-bs-toggle="tooltip"]').tooltip();

        // Initialize progress bars animation
        this._animateProgressBars();

        // Set active navigation
        this._setActiveNavigation();
    },

    /**
     * Check for active online sessions periodically
     */
    _checkActiveSession() {
        // Check every 30 seconds for active sessions
        setInterval(() => {
            this._updateActiveSessionStatus();
        }, 30000);
    },

    /**
     * Initialize countdown timers for upcoming sessions
     */
    _initializeCountdown() {
        $('.session-countdown').each(function() {
            const startTime = new Date($(this).data('start-time'));
            const $element = $(this);

            const updateCountdown = () => {
                const now = new Date();
                const diff = startTime - now;

                if (diff > 0) {
                    const hours = Math.floor(diff / (1000 * 60 * 60));
                    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

                    $element.text(`يبدأ بعد ${hours} ساعة و ${minutes} دقيقة`);
                } else {
                    $element.text('الجلسة متاحة الآن');
                    $element.addClass('text-success pulse-animation');
                }
            };

            updateCountdown();
            setInterval(updateCountdown, 60000); // Update every minute
        });
    },

    /**
     * Handle join session button click
     */
    _onJoinSession(ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const sessionUrl = $btn.data('session-url');

        // Show loading
        $btn.prop('disabled', true);
        $btn.html('<i class="fa fa-spinner fa-spin"></i> جاري الدخول...');

        // Add loading overlay
        this._showLoading();

        // Redirect to session
        setTimeout(() => {
            window.location.href = sessionUrl;
        }, 1000);
    },

    /**
     * Handle filter tab changes
     */
    _onFilterChange(ev) {
        ev.preventDefault();
        const $tab = $(ev.currentTarget);
        const filterType = $tab.data('filter');

        // Update active tab
        $('.filter-tab').removeClass('active');
        $tab.addClass('active');

        // Redirect to filtered URL
        window.location.href = `/my/sessions/${filterType}`;
    },

    /**
     * Refresh data
     */
    _onRefreshData(ev) {
        ev.preventDefault();
        window.location.reload();
    },

    /**
     * Update active session status via AJAX
     */
    _updateActiveSessionStatus() {
        $.ajax({
            url: '/my/sessions/check-active',
            method: 'GET',
            success: (data) => {
                if (data.has_active_session) {
                    this._showActiveSessionNotification(data.session_info);
                }
            }
        });
    },

    /**
     * Show notification for active session
     */
    _showActiveSessionNotification(sessionInfo) {
        // Check if notification already shown
        if ($('.active-session-notification').length) {
            return;
        }

        const notification = `
            <div class="alert alert-success alert-dismissible fade show active-session-notification" role="alert">
                <strong><i class="fa fa-video-camera"></i> جلسة نشطة!</strong>
                <p class="mb-2">الجلسة "${sessionInfo.name}" متاحة الآن للدخول</p>
                <a href="${sessionInfo.join_url}" class="btn btn-sm btn-light">
                    <i class="fa fa-sign-in"></i> دخول الجلسة
                </a>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        $('.o_portal_wrap').prepend(notification);
    },

    /**
     * Animate progress bars
     */
    _animateProgressBars() {
        $('.progress-bar').each(function() {
            const $bar = $(this);
            const width = $bar.attr('aria-valuenow') + '%';

            $bar.css('width', '0%');
            setTimeout(() => {
                $bar.css({
                    'width': width,
                    'transition': 'width 1.5s ease-in-out'
                });
            }, 200);
        });
    },

    /**
     * Set active navigation item
     */
    _setActiveNavigation() {
        const currentPath = window.location.pathname;
        $('.o_portal_my_nav .nav-link').each(function() {
            const $link = $(this);
            if ($link.attr('href') === currentPath) {
                $link.addClass('active');
            }
        });
    },

    /**
     * Show loading overlay
     */
    _showLoading() {
        const loading = `
            <div class="loading-overlay">
                <div class="loading-spinner"></div>
            </div>
        `;
        $('body').append(loading);
    },

    /**
     * Hide loading overlay
     */
    _hideLoading() {
        $('.loading-overlay').remove();
    }
});

// Auto-refresh for active sessions page
if (window.location.pathname.includes('/my/sessions/active')) {
    setInterval(() => {
        window.location.reload();
    }, 60000); // Refresh every minute
}

export default publicWidget.registry.QuranStudentPortal;