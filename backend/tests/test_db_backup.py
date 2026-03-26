from scripts.db_backup import parse_database_url


def test_parse_url():
    url = "postgresql+asyncpg://user:pass@host:5432/mydb"
    result = parse_database_url(url)
    assert result["host"] == "host"
    assert result["port"] == 5432
    assert result["database"] == "mydb"
    assert result["user"] == "user"
    assert result["password"] == "pass"


def test_parse_url_defaults():
    url = "postgresql+asyncpg://localhost/quakemind"
    result = parse_database_url(url)
    assert result["host"] == "localhost"
    assert result["database"] == "quakemind"
