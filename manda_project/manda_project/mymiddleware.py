from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from urllib.parse import parse_qs
import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger('TokenAuthMiddleware')

class TokenAuthMiddleware(BaseMiddleware):
    """
    Custom token auth middleware for Django Channels 2
    """

    @sync_to_async
    def log_message(self, message):
        logger.debug(message)

    async def __call__(self, scope, receive, send):
        # Get the token from the query string
        query_string = scope['query_string'].decode()
        await self.log_message(f'Query string: {query_string}')

        parsed_query = parse_qs(query_string)
        token_key = parsed_query.get('token', [None])[0]

        if token_key:
            user = await self.get_user_from_token(token_key)
            await self.log_message(f'Authenticated user: {user}')
            scope['user'] = user
        else:
            await self.log_message('No token found, setting user as AnonymousUser')
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, token_key):
        print('token_key: ', token_key)
        try:
            token = Token.objects.get(key=token_key)
            print('token: ', token)
            return token.user
        except Token.DoesNotExist:
            return AnonymousUser()