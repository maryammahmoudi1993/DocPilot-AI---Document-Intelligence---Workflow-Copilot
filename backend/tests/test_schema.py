from drf_spectacular.generators import SchemaGenerator


def test_openapi_schema_generates_without_errors() -> None:
    generator = SchemaGenerator()
    schema = generator.get_schema(request=None, public=True)

    assert schema["info"]["title"] == "DocPilot AI API"
    assert "/api/health/" in schema["paths"]
    assert "/api/readiness/" in schema["paths"]
