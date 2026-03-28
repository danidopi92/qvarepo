from django.core import signing

PORTAL_TOKEN_SALT = "client-portal-access"
PORTAL_TOKEN_MAX_AGE = 60 * 60 * 24 * 7
PORTAL_REGISTER_SALT = "client-portal-register"
PORTAL_RESET_SALT = "client-portal-reset"


def build_portal_access_token(customer):
    return signing.dumps({"customer_id": customer.pk}, salt=PORTAL_TOKEN_SALT)


def resolve_portal_access_token(token, max_age=PORTAL_TOKEN_MAX_AGE):
    try:
        payload = signing.loads(token, salt=PORTAL_TOKEN_SALT, max_age=max_age)
    except signing.BadSignature:
        return None
    return payload.get("customer_id")


def build_portal_register_token(customer):
    return signing.dumps({"customer_id": customer.pk, "purpose": "register"}, salt=PORTAL_REGISTER_SALT)


def resolve_portal_register_token(token, max_age=PORTAL_TOKEN_MAX_AGE):
    try:
        payload = signing.loads(token, salt=PORTAL_REGISTER_SALT, max_age=max_age)
    except signing.BadSignature:
        return None
    if payload.get("purpose") != "register":
        return None
    return payload.get("customer_id")


def build_portal_reset_token(account):
    return signing.dumps({"account_id": account.pk, "purpose": "reset"}, salt=PORTAL_RESET_SALT)


def resolve_portal_reset_token(token, max_age=60 * 60 * 24):
    try:
        payload = signing.loads(token, salt=PORTAL_RESET_SALT, max_age=max_age)
    except signing.BadSignature:
        return None
    if payload.get("purpose") != "reset":
        return None
    return payload.get("account_id")
