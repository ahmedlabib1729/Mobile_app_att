
{
    'name': 'Student Application Form',
    'version': '1.0',
    'summary': 'Module for student registration form',
    'description': 'A custom module for managing student applications and exporting to PDF.',
    'author': 'Ahmed Labib',
    'depends': ['base', 'web', 'product', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/week_days_data.xml',
        'views/student_application_view.xml',



        'report/application_print.xml',
        'report/ir_actions_report.xml',
        'report/layout.xml',
    ],
    'installable': True,
    'application': True,
}
