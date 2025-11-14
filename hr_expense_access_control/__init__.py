# -*- coding: utf-8 -*-

def post_init_hook(cr, registry):
    """تطبيق الصلاحيات على المستخدمين الموجودين بعد تثبيت الموديول"""
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # إضافة كل المستخدمين الداخليين للمجموعة الأساسية
    users = env['res.users'].search([('share', '=', False)])
    default_group = env.ref('hr_expense_access_control.group_expense_own_only')
    
    for user in users:
        # تجنب إضافة المجموعة للمدراء
        if not user.has_group('hr_expense.group_hr_expense_team_approver') and \
           not user.has_group('hr_expense.group_hr_expense_manager'):
            user.groups_id = [(4, default_group.id)]
    
    # تسجيل رسالة نجاح
    env['ir.logging'].create({
        'name': 'hr_expense_access_control',
        'type': 'info',
        'level': 'info',
        'message': f'تم تطبيق صلاحيات المصاريف على {len(users)} مستخدم',
        'path': 'hr_expense_access_control',
        'line': '0',
        'func': 'post_init_hook',
    })
