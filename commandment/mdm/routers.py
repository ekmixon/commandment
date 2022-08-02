"""This module contains routers which direct the request towards a certain module or function based upon the CONTENT
of the request, rather than the URL."""

from typing import Union, Any, Type, Callable, Dict, List
from flask import Flask, app, Blueprint, request, abort, current_app
from functools import wraps
import biplist
from commandment.models import db, Device, Command
from commandment.mdm import commands

CommandHandler = Callable[[Command, Device, dict], None]
CommandHandlers = Dict[str, CommandHandler]


class CommandRouter(object):
    """The command router passes off commands to handlers which are registered by RequestType.
    
    When a reply is received from a device in relation to a specific CommandUUID, the router attempts to find a handler
     that was registered for the RequestType associated with that command. The handler is then called with the specific
     instance of the command that generated the response, and an instance of the device that is making the request to
     the MDM endpoint.

    Not handling the error status here allows handlers to freely interpret the error conditions of each response, which
    is generally a better approach as some errors are command specific.
    
    Args:
          app (app): The flask application or blueprint instance
    """
    def __init__(self, app: Union[Flask, Blueprint]) -> None:
        self._app = app
        self._handlers: CommandHandlers = {}

    def handle(self, command: Command, device: Device, response: dict):
        current_app.logger.debug(
            f'Looking for handler using command: {command.request_type}'
        )

        if command.request_type in self._handlers:
            return self._handlers[command.request_type](command, device, response)
        current_app.logger.warning(
            f'No handler found to process command response: {command.request_type}'
        )

        return None

    def route(self, request_type: str):
        """
        Route a plist request by its RequestType key value.
        
        The wrapped function must accept (command, plist_data)
        
        :param request_type: 
        :return: 
        """
        handlers = self._handlers
        # current_app.logger.debug('Registering command handler for request type: {}'.format(request_type))

        def decorator(f):
            handlers[request_type] = f

            @wraps(f)
            def wrapped(*args, **kwargs):
                return f(*args, **kwargs)

            return wrapped
        return decorator


class PlistRouter(object):
    """PlistRouter routes requests to view functions based on matching values to top level keys.
    
    """
    def __init__(self, app: app, url: str) -> None:
        self._app = app
        app.add_url_rule(url, view_func=self.view, methods=['PUT'])
        self.kv_routes: List[Dict[str, Any]] = []

    def view(self):
        current_app.logger.debug(request.data)

        try:
            plist_data = biplist.readPlistFromString(request.data)
        except biplist.NotBinaryPlistException:
            abort(400, 'The request body does not contain a plist as expected')
        except biplist.InvalidPlistException:
            abort(400, 'The request body does not contain a valid plist')

        for kvr in self.kv_routes:
            if kvr['key'] not in plist_data:
                continue

            if plist_data[kvr['key']] == kvr['value']:
                return kvr['handler'](plist_data)

        abort(404, 'No matching plist route')

    def route(self, key: str, value: Any):
        """
        Route a plist request if the content satisfies the key value test
        
        The wrapped function must accept (plist_data)
        """
        def decorator(f):
            self.kv_routes.append(dict(
                key=key,
                value=value,
                handler=f
            ))

            @wraps(f)
            def wrapped(*args, **kwargs):
                return f(*args, **kwargs)

            return wrapped
        return decorator
