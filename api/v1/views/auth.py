from functools import wraps
from flask import request, g, abort
from jose import jwt
import requests

AUTH0_DOMAIN = 'dev-mvz0o2d83zbkctso.us.auth0.com'
API_IDENTIFIER = 'http://localhost:5000/api/v1'
ALGORITHMS = ['RS256']

# def get_token_auth_header():
#     auth = request.headers.get("Authorization", None)
#     if not auth:
#         abort(401)
#     parts = auth.split()
#     if parts[0].lower() != "bearer" or len(parts) != 2:
#         abort(401)
#     return parts[1]

def get_token_auth_header():
    auth = request.headers.get("Authorization", None)
    if not auth:
        print("❌ No Authorization header found")
        abort(401)
    parts = auth.split()
    if parts[0].lower() != "bearer" or len(parts) != 2:
        print("❌ Invalid Authorization header format")
        abort(401)
    
    print("🔐 Token received:", parts[1][:30], "...")  # Log token start
    return parts[1]


def requires_auth(f):
    print("entered requires_auth")
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        print(token)
        jsonurl = requests.get(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
        jwks = jsonurl.json()
        unverified_header = jwt.get_unverified_header(token)
        print(unverified_header)
        rsa_key = {}
        if "kid" not in unverified_header:
            print("❌ 'kid' not found in token header")
            abort(401)
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }

        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=API_IDENTIFIER,
                    issuer=f"https://{AUTH0_DOMAIN}/"
                )
                g.current_user = payload
            except Exception as e:
                print("Token error:", str(e))
                abort(401)
        return f(*args, **kwargs)
    return decorated
