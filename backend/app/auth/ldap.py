import logging
from dataclasses import dataclass
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ADUser:
    username: str
    first_name: str
    last_name: str
    email: Optional[str]
    department: Optional[str]
    groups: list[str]


def _get_server():
    from ldap3 import Server
    return Server(settings.ad_server, port=settings.ad_port, use_ssl=settings.ad_use_ssl)


def authenticate_user(username: str, password: str) -> Optional[ADUser]:
    """Authentifiziert einen Benutzer gegen Active Directory."""
    from ldap3 import ALL_ATTRIBUTES, SUBTREE, Connection

    server = _get_server()

    # Zuerst den Benutzer-DN finden mit Service-Account
    try:
        bind_conn = Connection(
            server,
            user=settings.ad_bind_user,
            password=settings.ad_bind_password,
            auto_bind=True,
        )
    except Exception:
        logger.error("Verbindung zum AD-Server fehlgeschlagen (Service-Account)")
        return None

    search_filter = f"(sAMAccountName={_sanitize_ldap_input(username)})"
    bind_conn.search(
        settings.ad_user_search_base,
        search_filter,
        SUBTREE,
        attributes=ALL_ATTRIBUTES,
    )

    if not bind_conn.entries:
        logger.info("Benutzer '%s' nicht im AD gefunden", username)
        bind_conn.unbind()
        return None

    user_entry = bind_conn.entries[0]
    user_dn = user_entry.entry_dn
    bind_conn.unbind()

    # Jetzt mit den Benutzer-Credentials authentifizieren
    try:
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
    except Exception:
        logger.info("AD-Authentifizierung fehlgeschlagen fuer '%s'", username)
        return None

    # Gruppen auslesen
    user_conn.search(
        settings.ad_user_search_base,
        search_filter,
        SUBTREE,
        attributes=ALL_ATTRIBUTES,
    )

    if not user_conn.entries:
        user_conn.unbind()
        return None

    entry = user_conn.entries[0]
    groups = _extract_group_names(entry)

    ad_user = ADUser(
        username=str(entry.sAMAccountName),
        first_name=str(getattr(entry, "givenName", "")),
        last_name=str(getattr(entry, "sn", "")),
        email=str(getattr(entry, "mail", "")) or None,
        department=str(getattr(entry, "department", "")) or None,
        groups=groups,
    )

    user_conn.unbind()
    return ad_user


def sync_user_details(username: str) -> Optional[ADUser]:
    """Liest Benutzerdaten aus dem AD (ohne Passwort-Pruefung)."""
    from ldap3 import ALL_ATTRIBUTES, SUBTREE, Connection

    server = _get_server()
    try:
        conn = Connection(
            server,
            user=settings.ad_bind_user,
            password=settings.ad_bind_password,
            auto_bind=True,
        )
    except Exception:
        logger.error("AD-Verbindung fehlgeschlagen")
        return None

    search_filter = f"(sAMAccountName={_sanitize_ldap_input(username)})"
    conn.search(
        settings.ad_user_search_base,
        search_filter,
        SUBTREE,
        attributes=ALL_ATTRIBUTES,
    )

    if not conn.entries:
        conn.unbind()
        return None

    entry = conn.entries[0]
    groups = _extract_group_names(entry)

    ad_user = ADUser(
        username=str(entry.sAMAccountName),
        first_name=str(getattr(entry, "givenName", "")),
        last_name=str(getattr(entry, "sn", "")),
        email=str(getattr(entry, "mail", "")) or None,
        department=str(getattr(entry, "department", "")) or None,
        groups=groups,
    )
    conn.unbind()
    return ad_user


def determine_role_from_groups(groups: list[str]) -> str:
    """Bestimmt die App-Rolle anhand der AD-Gruppenmitgliedschaft."""
    if settings.ad_group_admin in groups:
        return "ADMIN"
    if settings.ad_group_hr in groups:
        return "HR"
    if settings.ad_group_manager in groups:
        return "DEPARTMENT_MANAGER"
    return "EMPLOYEE"


def _extract_group_names(entry) -> list[str]:
    """Extrahiert Gruppennamen aus dem memberOf-Attribut."""
    member_of = getattr(entry, "memberOf", [])
    groups = []
    for dn in member_of:
        parts = str(dn).split(",")
        for part in parts:
            if part.strip().startswith("CN="):
                groups.append(part.strip()[3:])
                break
    return groups


def _sanitize_ldap_input(value: str) -> str:
    """Verhindert LDAP-Injection."""
    dangerous_chars = ["\\", "*", "(", ")", "\x00", "/"]
    sanitized = value
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, f"\\{char}")
    return sanitized
