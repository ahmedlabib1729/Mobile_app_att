# Base models first
from . import week_days
from . import hallway_student

# Program models
from . import program
from . import program_level
from . import program_unit

# Application models (depends on student and program)
from . import application_program
from . import student_application

# Enrollment models
from . import enrollment
from . import enrollment_payment_plan
from . import enrollment_installment
from . import enrollment_payment