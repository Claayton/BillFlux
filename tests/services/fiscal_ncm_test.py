"""Testes da tabela embutida de NCMs vigentes (validação fiscal)."""

from billflux.services.fiscal import ncm


def test_tabela_embutida_tem_ncms_vigentes():
    info = ncm.table_info()

    assert info["count"] > 9000
    assert info["updated_at"]
    assert "siscomex" in (info["source"] or "").lower()


def test_ncm_valido_aceita_formatado():
    assert ncm.is_valid_ncm("22021000")
    assert ncm.is_valid_ncm("2202.10.00")
    assert ncm.normalize_ncm("2202.10.00") == "22021000"


def test_ncm_inexistente_e_invalido():
    assert not ncm.is_valid_ncm("12345678")
    assert not ncm.is_valid_ncm("00000000")


def test_ncm_com_tamanho_errado_e_invalido():
    assert not ncm.is_valid_ncm("")
    assert not ncm.is_valid_ncm(None)
    assert not ncm.is_valid_ncm("2202100")
    assert not ncm.is_valid_ncm("220210000")
    assert not ncm.is_valid_ncm("abcdefgh")


def test_tabela_ausente_degrada_para_formato(monkeypatch, tmp_path):
    """Sem o arquivo, aceita qualquer código de 8 dígitos (não bloqueia tudo)."""

    monkeypatch.setattr(ncm, "TABELA", tmp_path / "nao-existe.txt")
    ncm._codigos.cache_clear()
    try:
        assert ncm.is_valid_ncm("22021000")
        assert not ncm.is_valid_ncm("123")
        assert ncm.table_info()["count"] == 0
    finally:
        ncm._codigos.cache_clear()
