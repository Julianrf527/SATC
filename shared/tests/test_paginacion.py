from satc_shared.paginacion import patron_contiene, respuesta_paginada, total_paginas


def test_total_paginas_minimo_uno():
    assert total_paginas(0, 20) == 1
    assert total_paginas(40, 20) == 2
    assert total_paginas(41, 20) == 3


def test_respuesta_paginada_forma_estandar():
    r = respuesta_paginada([1, 2], total=5, page=1, limit=2, conteos={"x": 1})
    assert r == {"ok": True, "data": [1, 2], "total": 5, "page": 1, "limit": 2, "total_pages": 3, "conteos": {"x": 1}}


def test_patron_contiene_escapa_comodines():
    assert patron_contiene(" CA 001_26 ") == "%CA 001\\_26%"
    assert patron_contiene("50%") == "%50\\%%"
    assert patron_contiene("a\\b") == "%a\\\\b%"
