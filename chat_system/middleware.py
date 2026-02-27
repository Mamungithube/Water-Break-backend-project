from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.authentication import JWTAuthentication
from channels.auth import AuthMiddlewareStack

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token):
    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token)
        user = jwt_auth.get_user(validated_token)
        # print(f"✅ Token validated for user: {user.email}")
        return user
    except Exception as e:
        # print(f"❌ Token validation failed: {str(e)}")
        return AnonymousUser()


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        try:
            query_string = scope.get("query_string", b"").decode()
            query_params = parse_qs(query_string)

            token = query_params.get("token")
            if token:
                user = await get_user_from_token(token[0])
                scope["user"] = user
            else:
                print("❌ No token provided in query params")
                scope["user"] = AnonymousUser()

        except Exception as e:
            print(f"❌ Middleware error: {str(e)}")
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))