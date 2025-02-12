# type: ignore[*]
from logging import getLogger, DEBUG
import typing

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from ..exceptions import *

log = getLogger(__name__)
log.setLevel(DEBUG)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:73.0) Gecko/20100101 Firefox/73.0"
}


@typing.no_type_check
def _educonnect(
    session: requests.Session, username: str, password: str, url: str
) -> requests.Response:
    """
    Generic function for EduConnect

    Parameters
    ----------
    username : str
        username
    password : str
        password
    url: str
        url of the ent login page

    Returns
    -------
    response: requests.Response
        the response returned by EduConnect login
    """
    if not url:
        raise ENTLoginError("Missing url attribute")

    log.debug(f"[EduConnect {url}] Logging in with {username}")

    payload = {"j_username": username, "j_password": password, "_eventId_proceed": ""}
    response = session.post(url, headers=HEADERS, data=payload)
    # 2nd SAML Authentication
    soup = BeautifulSoup(response.text, "html.parser")
    input_SAMLResponse = soup.find("input", {"name": "SAMLResponse"})
    if not input_SAMLResponse:
        return

    payload = {"SAMLResponse": input_SAMLResponse["value"]}

    input_relayState = soup.find("input", {"name": "RelayState"})
    if input_relayState:
        payload["RelayState"] = input_relayState["value"]

    response = session.post(soup.find("form")["action"], headers=HEADERS, data=payload)
    return response


def _cas_edu(
    username: str, password: str, url: str = ""
) -> requests.cookies.RequestsCookieJar:
    """
    Generic function for CAS with Educonnect

    Parameters
    ----------
    username : str
        username
    password : str
        password
    url: str
        url of the ent login page

    Returns
    -------
    cookies : cookies
        returns the ent session cookies
    """
    if not url:
        raise ENTLoginError("Missing url attribute")

    log.debug(f"[ENT {url}] Logging in with {username}")

    # ENT Connection
    session = requests.Session()

    response = session.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    payload = {
        "RelayState": soup.find("input", {"name": "RelayState"})["value"],
        "SAMLRequest": soup.find("input", {"name": "SAMLRequest"})["value"],
    }

    response = session.post(soup.find("form")["action"], data=payload, headers=HEADERS)

    educonnect(response.url, session, username, password)

    return session.cookies


def _cas(
    username: str, password: str, url: str = ""
) -> requests.cookies.RequestsCookieJar:
    """
    Generic function for CAS

    Parameters
    ----------
    username : str
        username
    password : str
        password
    url: str
        url of the ent login page

    Returns
    -------
    cookies : cookies
        returns the ent session cookies
    """
    if not url:
        raise ENTLoginError("Missing url attribute")

    log.debug(f"[ENT {url}] Logging in with {username}")

    # ENT Connection
    session = requests.Session()
    response = session.get(url, headers=HEADERS)

    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form", {"class": "cas__login-form"})
    payload = {}
    for input_ in form.findAll("input"):
        payload[input_["name"]] = input_.get("value")
    payload["username"] = username
    payload["password"] = password

    session.post(response.url, data=payload, headers=HEADERS)

    return session.cookies


def _open_ent_ng_edu(
    username: str, password: str, domain: str = ""
) -> requests.cookies.RequestsCookieJar:
    """
    ENT which has an authentication like https://connexion.l-educdenormandie.fr/

    Parameters
    ----------
    username : str
        username
    password : str
        password
    domain : str
        domain of the ENT

    Returns
    -------
    cookies : cookies
        returns the ent session cookies
    """
    if not domain:
        raise ENTLoginError("Missing domain attribute")

    log.debug(f"[ENT {domain}] Logging in with {username}")

    # URL required
    ent_login_page = (
        "https://educonnect.education.gouv.fr/idp/profile/SAML2/Unsolicited/SSO"
    )

    session = requests.Session()

    params = {"providerId": f"{domain}/auth/saml/metadata/idp.xml"}

    response = session.get(ent_login_page, params=params, headers=HEADERS)
    response = educonnect(response.url, session, username, password)

    if not response:
        return open_ent_ng(response.url, username, password)
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.find("title").get_text() == "Authentification":
            return open_ent_ng(response.url, username, password)

    return session.cookies


def _open_ent_ng(
    username: str, password: str, url: str = ""
) -> requests.cookies.RequestsCookieJar:
    """
    ENT which has an authentication like https://ent.iledefrance.fr/auth/login

    Parameters
    ----------
    username : str
        username
    password : str
        password
    url : str
        url of the ENT

    Returns
    -------
    cookies : cookies
        returns the ent session cookies
    """
    if not url:
        raise ENTLoginError("Missing url attribute")

    log.debug(f"[ENT {url}] Logging in with {username}")

    # ENT Connection
    session = requests.Session()

    payload = {"email": username, "password": password}
    response = session.post(url, headers=HEADERS, data=payload)
    return session.cookies


def _wayf(
    username: str,
    password: str,
    domain: str = "",
    entityID: str = "",
    returnX: str = "",
) -> requests.cookies.RequestsCookieJar:
    """
    Generic function for WAYF

    Parameters
    ----------
    username : str
        username
    password : str
        password
    domain : str
        domain of the ENT
    entityID : str
        request param entityID
    returnX : str
        request param returnX

    Returns
    -------
    cookies : cookies
        returns the ent session cookies
    """
    if not domain:
        raise ENTLoginError("Missing domain attribute")
    if not entityID:
        entityID = f"{domain}/shibboleth"
    if not returnX:
        returnX = f"{domain}/Shibboleth.sso/Login"

    log.debug(f"[ENT {domain}] Logging in with {username}")

    ent_login_page = f"{domain}/discovery/WAYF"

    # ENT Connection
    session = requests.Session()

    params = {
        "entityID": entityID,
        "returnX": returnX,
        "returnIDParam": "entityID",
        "action": "selection",
        "origin": "https://_educonnect.education.gouv.fr/idp",
    }

    response = session.get(ent_login_page, params=params, headers=HEADERS)
    _educonnect(response.url, session, username, password)

    return session.cookies


def _oze_ent(
    username: str, password: str, url: str = ""
) -> requests.cookies.RequestsCookieJar:
    """
    Generic function for Oze ENT

    Parameters
    ----------
    username : str
        username
    password : str
        password
    url : str
        url of the ENT

    Returns
    -------
    cookies : cookies
        returns the ent session cookies
    """
    if not url:
        raise ENTLoginError("Missing url attribute")

    log.debug(f"[ENT {url}] Logging in with {username}")

    # ENT Connection
    session = requests.Session()
    response = session.get(url, headers=HEADERS)

    domain = urlparse(url).netloc

    if not domain in username:
        username = f"{username}@{domain}"

    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form", {"id": "auth_form"})
    payload = {}
    for input_ in form.findAll("input"):
        payload[input_["name"]] = input_.get("value")
    payload["username"] = username
    payload["password"] = password

    session.post(response.url, data=payload, headers=HEADERS)

    return session.cookies


def _simple_auth(
    username: str, password: str, url: str = "", form_attr: dict = {}
) -> requests.cookies.RequestsCookieJar:
    """
    Generic function for ENT with simple login form

    Parameters
    ----------
    username : str
        username
    password : str
        password
    url: str
        url of the ent login page
    form_attr: dict
        attr to locate form

    Returns
    -------
    cookies : cookies
        returns the ent session cookies
    """
    if not url:
        raise ENTLoginError("Missing url attribute")

    log.debug(f"[ENT {url}] Logging in with {username}")

    # ENT Connection
    session = requests.Session()
    response = session.get(url, headers=HEADERS)

    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form", form_attr)
    payload = {}
    for input_ in form.findAll("input"):
        payload[input_["name"]] = input_.get("value")
    payload["username"] = username
    payload["password"] = password

    session.post(response.url, data=payload, headers=HEADERS)

    return session.cookies
