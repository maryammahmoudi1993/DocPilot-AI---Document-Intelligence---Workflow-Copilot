from apps.extraction.providers import INVOICE_SCHEMA, RegexInvoiceExtractionProvider


def test_extracts_a_value_for_every_matching_labeled_line():
    text = "Invoice Number: INV-42\nTotal: 99.99\n"
    provider = RegexInvoiceExtractionProvider()

    results = {r.key: r.value for r in provider.extract(text=text)}

    assert results["invoice_number"] == "INV-42"
    assert results["total"] == "99.99"


def test_missing_fields_come_back_empty_with_zero_confidence():
    provider = RegexInvoiceExtractionProvider()

    results = {r.key: r for r in provider.extract(text="nothing useful here")}

    assert results["vendor_name"].value == ""
    assert results["vendor_name"].confidence == 0.0


def test_output_is_deterministic_for_the_same_input():
    text = "Vendor Name: Acme\nTotal: 10.00\n"
    provider = RegexInvoiceExtractionProvider()

    first = provider.extract(text=text)
    second = provider.extract(text=text)

    assert first == second


def test_every_schema_field_is_always_present_in_the_result():
    provider = RegexInvoiceExtractionProvider()

    results = provider.extract(text="")

    assert {r.key for r in results} == {key for key, _, _ in INVOICE_SCHEMA}
