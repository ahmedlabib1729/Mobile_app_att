$(document).ready(function() {
    'use strict';

    // Initialize on subscription request page
    if ($('.subscription-request-page').length) {
        var playerCount = 0;
        var existingPlayers = [];

        // Add initial player
        addNewPlayer();

        // Check mobile button
        $('#check_mobile_btn').on('click', function(e) {
            e.preventDefault();
            checkMobile();
        });

        // Add player button
        $('#add_player_btn').on('click', function(e) {
            e.preventDefault();
            addNewPlayer();
        });

        // Remove player (delegated)
        $(document).on('click', '.remove-player', function(e) {
            e.preventDefault();
            removePlayer($(this).data('player-num'));
        });

        // Use existing player (delegated)
        $(document).on('click', '.use-existing-player', function(e) {
            e.preventDefault();
            var $btn = $(this);
            var playerData = {
                id: $btn.data('player-id'),
                name: $btn.data('player-name'),
                birth_date: $btn.data('player-birth'),
                gender: $btn.data('player-gender')
            };
            addNewPlayer(playerData);
            $btn.prop('disabled', true).text('تمت الإضافة');
        });

        // Sport or period change (delegated)
        $(document).on('change', '.sport-select, .period-select', function() {
            var $elem = $(this);
            var playerNum = $elem.data('player-num');
            var sportId = $('select[name="sport_id_' + playerNum + '"]').val();
            var period = $('select[name="subscription_period_' + playerNum + '"]').val();

            if (sportId && period) {
                updatePlayerFee(playerNum, sportId, period);
            }
        });

        // Mobile change
        $('#parent_mobile, #parent_country_code').on('change', function() {
            resetParentState();
        });

        // Form validation before submit
        $('#subscription_form').on('submit', function(e) {
            var isValid = true;
            var errors = [];

            // Check if at least one player exists
            if (playerCount === 0) {
                errors.push('يجب إضافة لاعب واحد على الأقل');
                isValid = false;
            }

            // Validate parent data
            if ($('#parent_exists').val() !== 'true') {
                if (!$('#parent_name').val()) {
                    errors.push('يرجى إدخال اسم ولي الأمر');
                    isValid = false;
                }
                if (!$('#parent_mobile').val()) {
                    errors.push('يرجى إدخال رقم الموبايل');
                    isValid = false;
                }
            }

            // Show errors if any
            if (!isValid) {
                e.preventDefault();
                var errorHtml = '<div class="alert alert-danger alert-dismissible fade show" role="alert">';
                errorHtml += '<strong>يرجى تصحيح الأخطاء التالية:</strong><ul>';
                errors.forEach(function(error) {
                    errorHtml += '<li>' + error + '</li>';
                });
                errorHtml += '</ul><button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>';

                // Add error message at top of form
                if ($('#form-errors').length === 0) {
                    $('<div id="form-errors"></div>').insertBefore($('.card').first());
                }
                $('#form-errors').html(errorHtml);

                // Scroll to top
                $('html, body').animate({ scrollTop: 0 }, 'slow');
                return false;
            }

            // If valid, show loading
            $(this).find('button[type="submit"]').prop('disabled', true)
                .html('<i class="fa fa-spinner fa-spin"></i> جاري الإرسال...');
        });

        // Check mobile function
        function checkMobile() {
            var countryCode = $('#parent_country_code').val();
            var mobile = $('#parent_mobile').val();

            if (!mobile) {
                showAlert('parent_check_result', 'يرجى إدخال رقم الموبايل', 'danger');
                return;
            }

            var $btn = $('#check_mobile_btn');
            $btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"/> جاري التحقق...');

            $.ajax({
                url: '/subscription/check_mobile',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'params': {
                        'country_code': countryCode,
                        'mobile': mobile
                    },
                    'id': Math.floor(Math.random() * 1000000)
                }),
                success: function(data) {
                    var result = data.result;
                    if (result && result.exists) {
                        // Parent exists
                        $('#parent_exists').val('true');
                        $('#parent_id').val(result.parent_id);

                        $('#parent_name').val(result.parent_name).prop('readonly', true);
                        $('#parent_email').val(result.parent_email).prop('readonly', true);
                        $('#parent_address').val(result.parent_address).prop('readonly', true);

                        showAlert('parent_check_result',
                            'تم العثور على ولي الأمر: ' + result.parent_name,
                            'success');

                        existingPlayers = result.children;

                        if (result.children && result.children.length > 0) {
                            showExistingPlayers(result.children);
                        }
                    } else {
                        // New parent
                        $('#parent_exists').val('false');
                        $('#parent_id').val('');

                        $('#parent_name').prop('readonly', false);
                        $('#parent_email').prop('readonly', false);
                        $('#parent_address').prop('readonly', false);

                        showAlert('parent_check_result',
                            'رقم جديد - يرجى إكمال بيانات ولي الأمر',
                            'info');

                        $('#existing_players_list').addClass('d-none');
                    }
                },
                error: function() {
                    showAlert('parent_check_result', 'حدث خطأ في التحقق', 'danger');
                },
                complete: function() {
                    $btn.prop('disabled', false).html('<i class="fa fa-search"/> تحقق');
                }
            });
        }

        // Reset parent state
        function resetParentState() {
            $('#parent_exists').val('false');
            $('#parent_id').val('');
            $('#parent_name').prop('readonly', false);
            $('#parent_email').prop('readonly', false);
            $('#parent_address').prop('readonly', false);
            $('#parent_check_result').addClass('d-none');
            $('#existing_players_list').addClass('d-none');
        }

        // Show existing players
        function showExistingPlayers(players) {
            var html = '<div class="list-group">';

            players.forEach(function(player) {
                html += '<div class="list-group-item">' +
                    '<div class="d-flex justify-content-between align-items-center">' +
                        '<div>' +
                            '<h6 class="mb-1">' + player.name + '</h6>' +
                            '<small class="text-muted">' +
                                (player.gender ? (player.gender === 'male' ? 'ذكر' : 'أنثى') + ' - ' : '') +
                                'تاريخ الميلاد: ' + player.birth_date +
                            '</small>' +
                            '<br/>' +
                            '<small>الألعاب: ' + player.sports + '</small>' +
                        '</div>' +
                        '<button type="button" class="btn btn-sm btn-primary use-existing-player" ' +
                                'data-player-id="' + player.id + '" ' +
                                'data-player-name="' + player.name + '" ' +
                                'data-player-birth="' + player.birth_date + '" ' +
                                'data-player-gender="' + (player.gender || '') + '">' +
                            '<i class="fa fa-plus"/> إضافة للطلب' +
                        '</button>' +
                    '</div>' +
                '</div>';
            });

            html += '</div>';

            $('#existing_players_container').html(html);
            $('#existing_players_list').removeClass('d-none');
        }

        // Add new player
        function addNewPlayer(existingData) {
            playerCount++;
            var playerNum = playerCount;
            var isExisting = existingData ? true : false;

            // Get sports options from first select if exists
            var sportsOptions = '';
            if ($('.sport-select').length > 0) {
                $('.sport-select').first().find('option').each(function() {
                    sportsOptions += $(this).prop('outerHTML');
                });
            } else {
                // Get from template sports data
                $('select[name="sport_template"] option').each(function() {
                    sportsOptions += $(this).prop('outerHTML');
                });
            }

            var playerHtml = '<div class="player-item border rounded p-3 mb-3" data-player-num="' + playerNum + '">' +
                '<div class="d-flex justify-content-between align-items-center mb-3">' +
                    '<h6 class="mb-0">لاعب ' + playerNum + '</h6>' +
                    '<button type="button" class="btn btn-sm btn-danger remove-player" data-player-num="' + playerNum + '">' +
                        '<i class="fa fa-trash"/> حذف' +
                    '</button>' +
                '</div>' +

                '<input type="hidden" name="player_exists_' + playerNum + '" value="' + isExisting + '" />' +
                '<input type="hidden" name="player_id_' + playerNum + '" value="' + (existingData ? existingData.id : '') + '" />' +

                '<div class="player-details ' + (isExisting ? 'existing-player' : 'new-player') + '">';

            if (isExisting) {
                playerHtml += '<div class="alert alert-info">' +
                    '<strong>لاعب مسجل:</strong> ' + existingData.name +
                    '<br/>' +
                    '<small>' +
                    (existingData.gender ? (existingData.gender === 'male' ? 'ذكر' : 'أنثى') + ' - ' : '') +
                    'تاريخ الميلاد: ' + existingData.birth_date + '</small>' +
                '</div>';
            } else {
                playerHtml += '<div class="row">' +
                    '<div class="col-md-6 mb-3">' +
                        '<label class="form-label">اسم اللاعب <span class="text-danger">*</span></label>' +
                        '<input type="text" name="player_name_' + playerNum + '" class="form-control" required />' +
                    '</div>' +
                    '<div class="col-md-6 mb-3">' +
                        '<label class="form-label">تاريخ الميلاد <span class="text-danger">*</span></label>' +
                        '<input type="date" name="player_birth_date_' + playerNum + '" class="form-control" required />' +
                    '</div>' +
                '</div>' +
                '<div class="row">' +
                    '<div class="col-md-6 mb-3">' +
                        '<label class="form-label">الجنس <span class="text-danger">*</span></label>' +
                        '<select name="player_gender_' + playerNum + '" class="form-select" required>' +
                            '<option value="">اختر...</option>' +
                            '<option value="male">ذكر</option>' +
                            '<option value="female">أنثى</option>' +
                        '</select>' +
                    '</div>' +
                    '<div class="col-md-6 mb-3">' +
                        '<label class="form-label">الحالة الصحية</label>' +
                        '<textarea name="player_medical_' + playerNum + '" class="form-control" rows="2" ' +
                                  'placeholder="أي حالات صحية أو حساسية..."></textarea>' +
                    '</div>' +
                '</div>';
            }

            playerHtml += '</div>' +

                '<hr/>' +

                '<div class="row">' +
                    '<div class="col-md-6 mb-3">' +
                        '<label class="form-label">اللعبة <span class="text-danger">*</span></label>' +
                        '<select name="sport_id_' + playerNum + '" class="form-select sport-select" ' +
                                'data-player-num="' + playerNum + '" required>' +
                            sportsOptions +
                        '</select>' +
                    '</div>' +
                    '<div class="col-md-4 mb-3">' +
                        '<label class="form-label">مدة الاشتراك <span class="text-danger">*</span></label>' +
                        '<select name="subscription_period_' + playerNum + '" class="form-select period-select" ' +
                                'data-player-num="' + playerNum + '" required>' +
                            '<option value="">اختر المدة...</option>' +
                            '<option value="1">شهر واحد</option>' +
                            '<option value="3">3 شهور (خصم 5%)</option>' +
                            '<option value="6">6 شهور (خصم 10%)</option>' +
                            '<option value="12">سنة كاملة (خصم 15%)</option>' +
                        '</select>' +
                    '</div>' +
                    '<div class="col-md-2 mb-3">' +
                        '<label class="form-label">الرسوم</label>' +
                        '<div class="player-fee" id="player_fee_' + playerNum + '">' +
                            '<span class="text-muted">---</span>' +
                        '</div>' +
                    '</div>' +
                '</div>' +

                '<div class="mb-3">' +
                    '<label class="form-label">ملاحظات</label>' +
                    '<textarea name="player_note_' + playerNum + '" class="form-control" rows="2"></textarea>' +
                '</div>' +
            '</div>';

            $('#players_container').append(playerHtml);
            $('#player_count').val(playerCount);

            updateFeesSummary();
        }

        // Remove player
        function removePlayer(playerNum) {
            $('.player-item[data-player-num="' + playerNum + '"]').remove();
            renumberPlayers();
            updateFeesSummary();
        }

        // Renumber players
        function renumberPlayers() {
            var newCount = 0;

            $('.player-item').each(function(index) {
                newCount++;
                var $item = $(this);
                var oldNum = $item.data('player-num');
                var newNum = newCount;

                $item.attr('data-player-num', newNum);
                $item.find('h6').first().text('لاعب ' + newNum);

                $item.find('[name^="player_"]').each(function() {
                    var name = $(this).attr('name');
                    $(this).attr('name', name.replace(/_\d+$/, '_' + newNum));
                });

                $item.find('[id^="player_"]').each(function() {
                    var id = $(this).attr('id');
                    $(this).attr('id', id.replace(/_\d+$/, '_' + newNum));
                });

                $item.find('[data-player-num]').attr('data-player-num', newNum);
            });

            playerCount = newCount;
            $('#player_count').val(playerCount);
        }

        // Update player fee
        function updatePlayerFee(playerNum, sportId, period) {
            $.ajax({
                url: '/subscription/get_sport_fee',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'params': {
                        'sport_id': sportId,
                        'period': period
                    },
                    'id': Math.floor(Math.random() * 1000000)
                }),
                success: function(data) {
                    var result = data.result;
                    if (result && result.success) {
                        var feeHtml = '<strong>' + result.total + ' ' + result.currency + '</strong>';
                        if (result.discount > 0) {
                            feeHtml += '<br/><small class="text-success">خصم ' + result.discount + '%</small>';
                        }
                        $('#player_fee_' + playerNum).html(feeHtml);
                        updateFeesSummary();
                    }
                }
            });
        }

        // Update fees summary
        function updateFeesSummary() {
            var total = 0;
            var summaryHtml = '';

            $('.player-item').each(function() {
                var $item = $(this);
                var playerNum = $item.data('player-num');
                var $feeDiv = $item.find('#player_fee_' + playerNum);
                var feeText = $feeDiv.find('strong').text();

                if (feeText && feeText !== '---') {
                    var fee = parseFloat(feeText.replace(/[^\d.]/g, ''));
                    if (!isNaN(fee)) {
                        total += fee;

                        var playerName = $item.find('input[name^="player_name_"]').val() ||
                                       $item.find('.alert strong').text() ||
                                       'لاعب ' + playerNum;
                        var sportName = $item.find('.sport-select option:selected').text();
                        var period = $item.find('.period-select option:selected').text();

                        if (sportName && sportName !== 'اختر اللعبة...') {
                            summaryHtml += '<div class="d-flex justify-content-between mb-2">' +
                                '<div>' +
                                    '<strong>' + playerName + '</strong>' +
                                    '<br/>' +
                                    '<small class="text-muted">' + sportName + ' - ' + period + '</small>' +
                                '</div>' +
                                '<div class="text-end">' +
                                    feeText + ' ر.س' +
                                '</div>' +
                            '</div>';
                        }
                    }
                }
            });

            if (summaryHtml) {
                $('#fees_summary').html(summaryHtml);
            } else {
                $('#fees_summary').html('<p class="text-muted text-center">لم يتم إضافة أي لاعبين بعد</p>');
            }

            $('#total_amount').text(total.toFixed(2) + ' ر.س');
        }

        // Show alert
        function showAlert(elementId, message, type) {
            var $alert = $('#' + elementId);
            $alert.removeClass('d-none alert-success alert-danger alert-info alert-warning')
                  .addClass('alert-' + type)
                  .html(message);
        }
    }
});