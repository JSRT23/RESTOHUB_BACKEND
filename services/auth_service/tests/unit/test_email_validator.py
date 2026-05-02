# tests/unit/test_email_validator.py
# Pruebas unitarias de email_validator.py.
# Los tests de MX lookup mockean dns.resolver para no depender de red.

import pytest

from app.auth.email_validator import (
    validar_dominio_mx,
    validar_email_completo,
    validar_formato,
    DOMINIOS_CONOCIDOS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# validar_formato
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidarFormato:

    @pytest.mark.parametrize("email", [
        "usuario@gmail.com",
        "user.name+tag@example.co",
        "test123@hotmail.es",
        "a@b.io",
        "nombre.apellido@dominio.com.co",
    ])
    def test_emails_validos(self, email):
        assert validar_formato(email) is True

    @pytest.mark.parametrize("email", [
        "",
        "sinArroba",
        "@sinlocal.com",
        "sin@",
        "doble@@dominio.com",
        "sin punto@dominio",
        "espacios en@medio.com",
        "a@b",              # TLD muy corto
    ])
    def test_emails_invalidos(self, email):
        assert validar_formato(email) is False


# ═══════════════════════════════════════════════════════════════════════════════
# validar_dominio_mx
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidarDominioMx:

    @pytest.mark.parametrize("email", [
        "user@gmail.com",
        "user@hotmail.com",
        "user@outlook.com",
        "user@yahoo.com",
        "user@icloud.com",
        "user@protonmail.com",
        "user@unicordoba.edu.co",
    ])
    def test_dominios_conocidos_no_hacen_lookup(self, email, mocker):
        """Dominios en DOMINIOS_CONOCIDOS deben retornar True sin llamar dns.resolver."""
        mock_resolve = mocker.patch("dns.resolver.resolve")
        ok, msg = validar_dominio_mx(email)
        mock_resolve.assert_not_called()
        assert ok is True
        assert msg == ""

    def test_dominio_desconocido_con_mx_valido(self, mocker):
        """Dominio no conocido con registros MX → válido."""
        mocker.patch("dns.resolver.resolve", return_value=["mx1.custom.com"])
        ok, msg = validar_dominio_mx("user@customdomain.com")
        assert ok is True

    def test_dominio_nxdomain_retorna_false(self, mocker):
        """Dominio inexistente (NXDOMAIN) → inválido."""
        import dns.resolver

        class FakeNXDOMAIN(dns.resolver.NXDOMAIN):
            pass

        mocker.patch("dns.resolver.resolve", side_effect=FakeNXDOMAIN())
        ok, msg = validar_dominio_mx("user@dominioquenoexiste99.xyz")
        assert ok is False
        assert "no existe" in msg.lower()

    def test_dominio_sin_mx_retorna_false(self, mocker):
        import dns.resolver

        mocker.patch(
            "dns.resolver.resolve",
            side_effect=dns.resolver.NoAnswer(),
        )
        ok, msg = validar_dominio_mx("user@sinmx.test")
        assert ok is False

    def test_timeout_asume_valido(self, mocker):
        """Timeout de DNS → no bloquear el registro, asumir válido."""
        import dns.resolver

        mocker.patch(
            "dns.resolver.resolve",
            side_effect=dns.resolver.LifetimeTimeout(),
        )
        ok, msg = validar_dominio_mx("user@lento.net")
        assert ok is True

    def test_email_sin_formato_retorna_false(self):
        ok, msg = validar_dominio_mx("esto no es un email")
        assert ok is False

    def test_email_vacio_retorna_false(self):
        ok, msg = validar_dominio_mx("")
        assert ok is False


# ═══════════════════════════════════════════════════════════════════════════════
# validar_email_completo
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidarEmailCompleto:

    def test_email_valido_conocido(self, mocker):
        mocker.patch("dns.resolver.resolve")
        ok, msg = validar_email_completo("juan@gmail.com")
        assert ok is True
        assert msg == ""

    def test_email_vacio(self):
        ok, msg = validar_email_completo("")
        assert ok is False
        assert "obligatorio" in msg.lower()

    def test_email_none_equivalente(self):
        ok, msg = validar_email_completo("")
        assert ok is False

    def test_formato_invalido_sin_lookup(self, mocker):
        mock_dns = mocker.patch("dns.resolver.resolve")
        ok, msg = validar_email_completo("sinArroba")
        mock_dns.assert_not_called()
        assert ok is False
        assert "formato" in msg.lower()

    def test_dominio_falso_retorna_false(self, mocker):
        import dns.resolver
        mocker.patch(
            "dns.resolver.resolve",
            side_effect=dns.resolver.NXDOMAIN(),
        )
        ok, msg = validar_email_completo("x@dominiofalso99999.xyz")
        assert ok is False

    def test_dominios_conocidos_siempre_validos(self):
        for dominio in list(DOMINIOS_CONOCIDOS)[:5]:
            ok, msg = validar_email_completo(f"test@{dominio}")
            assert ok is True, f"Falló para dominio conocido: {dominio}"
