# Intercompany Payment Batch Module

## Overview
This module enables centralized payment processing for multi-company environments in Odoo 18.

## Features
- **Centralized Payment Processing**: Process vendor payments from a central company
- **Automatic Intercompany Entries**: Generate journal entries automatically in target companies
- **Batch Management**: Group multiple vendor bills in a single payment batch
- **Multi-Vendor Support**: Process payments for multiple vendors in one batch
- **Flexible Configuration**: Configure intercompany account mappings
- **Full Tracking**: Complete audit trail with chatter support
- **Reconciliation**: Automatic matching of payments with vendor bills

## Installation
1. Copy the module to your Odoo addons directory
2. Update the module list
3. Install the module from Apps

## Configuration
1. Go to **Intercompany Payments > Configuration > Intercompany Settings**
2. Create configurations for each company pair:
   - Select source company (paying company)
   - Select related party account in source company
   - Select target company
   - Select related party account in target company
   - Select journal for target company

## Usage
1. **Create Payment Batch**:
   - Go to **Intercompany Payments > Operations > Payment Batches**
   - Click Create or use the wizard
   - Select paying company and payment journal
   - Add vendor bills from different companies

2. **Process Batch**:
   - Confirm the batch
   - Click "Create Payments" to generate payments and intercompany entries
   - Reconcile to match payments with bills

## Workflow
1. **Draft**: Initial state, bills can be added/removed
2. **Confirmed**: Batch is validated, ready for payment
3. **Posted**: Payments created and intercompany entries generated
4. **Reconciled**: All bills matched with payments

## Security
- User group: View and create batches
- Manager group: Full access including configuration

## Dependencies
- account
- account_payment
- mail

## License
LGPL-3

## Support
For support and customization, contact your Odoo partner.
