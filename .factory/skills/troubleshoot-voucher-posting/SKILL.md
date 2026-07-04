---
name: troubleshoot-voucher-posting
description: Diagnose and fix voucher posting issues in the accounting ledger. Checks balance, account codes, period status, and posting service.
---

# Skill: Troubleshoot Voucher Posting

When a voucher fails to post to the general ledger, follow these diagnostic steps.

## Common Issues

1. **Unbalanced entry**: debit_total != credit_total
   - Check: `voucher.lines.aggregate(d=Sum('debit_vnd'), c=Sum('credit_vnd'))`
   - Fix: ensure all lines balance

2. **Wrong period status**: period is locked (status=LOCKED)
   - Check: `PeriodClosingService.is_period_closed(fiscal_year, period)`
   - Fix: unlock period via PeriodClosingView

3. **Invalid account code**: account doesn't exist in chart of accounts
   - Check: `Account.objects.filter(code=account_code).exists()`
   - Fix: create account or correct the code

4. **Missing object_code for 131/331**: customer/vendor not set
   - Check: `VoucherLine.objects.filter(account_code__startswith='131', object_code='').exists()`
   - Fix: set object_code + object_name

5. **Voucher status < LEDGER**: not yet posted
   - Check: `voucher.status >= AccountingVoucher.Status.LEDGER`
   - Fix: call `voucher_posting_service.post_voucher(voucher)`

## Debug Commands

```python
from apps.ledger.services.voucher_posting_service import VoucherPostingService

# Check voucher
v = AccountingVoucher.objects.get(voucher_no='...')
VoucherPostingService.validate(v)  # Raises if invalid
VoucherPostingService.post(v)      # Posts to ledger
```
