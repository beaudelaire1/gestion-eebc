"""Script de test pour générer un PDF fiscal avec données fictives."""
import os, django, re
os.environ['DJANGO_SETTINGS_MODULE'] = 'gestion_eebc.settings.dev'
django.setup()

from datetime import date
from decimal import Decimal
from django.template.loader import render_to_string
from apps.finance.pdf_service import _get_logo_base64, _amount_to_words, CHURCH_INFO
from weasyprint import HTML, CSS

logo_base64 = _get_logo_base64()


class FakeReceipt:
    receipt_number = 'RF-2025-0001'
    fiscal_year = 2025
    donor_name = 'Marie-Claire DUPONT'
    donor_address = '15 Avenue des Flamboyants\n97300 Cayenne'
    donor_email = 'mc.dupont@email.com'
    total_amount = Decimal('2450.00')
    issue_date = date(2026, 1, 15)

    class transactions:
        @staticmethod
        def exists():
            return True

        @staticmethod
        def all():
            class FakeTx:
                def __init__(s, d, t, m, a):
                    s.transaction_date = d
                    s._type = t
                    s._method = m
                    s.amount = a
                def get_transaction_type_display(s):
                    return s._type
                def get_payment_method_display(s):
                    return s._method

            return [
                FakeTx(date(2025, 1, 15), 'Don', 'Espèces', Decimal('200.00')),
                FakeTx(date(2025, 3, 10), 'Dîme', 'Chèque', Decimal('350.00')),
                FakeTx(date(2025, 5, 22), 'Don', 'Virement', Decimal('500.00')),
                FakeTx(date(2025, 7, 8), 'Offrande', 'Espèces', Decimal('150.00')),
                FakeTx(date(2025, 9, 14), 'Dîme', 'Chèque', Decimal('350.00')),
                FakeTx(date(2025, 11, 3), 'Don', 'Virement', Decimal('900.00')),
            ]


receipt = FakeReceipt()

context = {
    'receipt': receipt,
    'logo_base64': logo_base64,
    'church_name': CHURCH_INFO['name'],
    'church_address': CHURCH_INFO['address'],
    'church_siret': CHURCH_INFO['siret'],
    'church_rna': CHURCH_INFO['rna'],
    'amount_words': _amount_to_words(receipt.total_amount),
}

html_content = render_to_string('finance/tax_receipt_pdf.html', context)

# Extract CSS from pdf_service.py
src = open('apps/finance/pdf_service.py', encoding='utf-8').read()
match = re.search(r"CSS\(string='''(.*?)'''\)", src, re.DOTALL)
css_text = match.group(1)

html = HTML(string=html_content)
css = CSS(string=css_text)
pdf_bytes = html.write_pdf(stylesheets=[css])

with open('test_tax_receipt.pdf', 'wb') as f:
    f.write(pdf_bytes)
print(f'OK: {len(pdf_bytes)} bytes')
