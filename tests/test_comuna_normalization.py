from etl.extract.comunas import normalizar_comuna, generar_variantes


class TestNormalizarComuna:
    def test_uppercase(self):
        assert normalizar_comuna("recoleta") == "RECOLETA"

    def test_remove_accents(self):
        assert normalizar_comuna("Concepción") == "CONCEPCION"

    def test_spaces_to_underscores(self):
        assert normalizar_comuna("San Bernardo") == "SAN_BERNARDO"

    def test_remove_apostrophes(self):
        assert normalizar_comuna("O'Higgins") == "OHIGGINS"

    def test_join_repeated_words(self):
        assert normalizar_comuna("BIO BIO") == "BIOBIO"

    def test_remove_hyphens(self):
        assert normalizar_comuna("TIL-TIL") == "TILTIL"


class TestGenerarVariantes:
    def test_strip_puerto(self):
        variantes = generar_variantes("PUERTO_NATALES")
        assert "NATALES" in variantes

    def test_without_article(self):
        variantes = generar_variantes("LA_REINA")
        assert "REINA" in variantes

    def test_strip_multiple_articles(self):
        variantes = generar_variantes("LA_DEHESA")
        assert "DEHESA" in variantes

    def test_original_included(self):
        variantes = generar_variantes("PUERTO_MONTT")
        assert "PUERTO_MONTT" in variantes
