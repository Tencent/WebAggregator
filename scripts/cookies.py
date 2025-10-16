from requests.cookies import RequestsCookieJar

# set the cookies here. Please refre the smolagents project.
COOKIES_LIST = [
    {
        "domain": ".web.archive.org",
        "expirationDate": 1718886430,
        "hostOnly": False,
        "httpOnly": False,
        "name": "_gat",
        "path": "/web/20201123221659/http://orcid.org/",
        "sameSite": None,
        "secure": False,
        "session": False,
        "storeId": None,
        "value": "1",
    }
]

# Create a RequestsCookieJar instance
COOKIES = RequestsCookieJar()

# Add cookies to the jar
for cookie in COOKIES_LIST:
    COOKIES.set(cookie["name"], cookie["value"], domain=cookie["domain"], path=cookie["path"])
