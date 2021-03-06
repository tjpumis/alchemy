import inspect

import json
import sys

import arrow # TODO cpy3.7  datetime.fromisoformat('2017-01-01T12:30:59.000000+08:00')

from datetime import datetime, date

from aiohttp.web_exceptions import HTTPException
from .exception import RESTfulArgumentError

def argument_getter_factory(route_spec):
    """ 根据spec来生成handler函数参数值读取器 """ 
    
    func_sig = inspect.signature(route_spec.handler_func)

    param_names = list(func_sig.parameters.keys())
    arg_getters  = build_argval_getters(route_spec)
    n_args = len(arg_getters)

    async def argument_getters(request):
        errors = None
        values = {}
        for i in range(n_args):
            try:
                arg_name = param_names[i]
                values[arg_name] = await arg_getters[i](request)
            except HTTPException:
                raise
            except Exception as exc :
                if errors is None: 
                    errors = []

                request.app.logger.error('', exc_info=True)

                exc_type = type(exc)

                data = {
                    "name": arg_name, 
                    "type": f"{exc_type.__module__}.{exc_type.__qualname__}",
                    "error": str(exc)
                }

                errors.append(data)

        if errors is not None:
            raise RESTfulArgumentError(errors)

        return values

    return argument_getters


_handler_argval_getters = []

def register_argument_getter(getter_factory):
    _handler_argval_getters.append(getter_factory)

def build_argval_getters(route_spec):

    # proto, method, handler_func, path_fields
    # proto, method, handler, path_params

    getters = []
    for arg_name in inspect.signature(route_spec.handler_func).parameters:
        getter = _build_argval_getter(route_spec, arg_name)
        getters.append(getter)

    return getters

def _build_argval_getter(route_spec, arg_name):
    arg_spec = inspect.signature(route_spec.handler_func).parameters[arg_name]
    # print(123, arg_name)
    ann_type = arg_spec.annotation
    argval_getter = None
    if ann_type != inspect._empty:
        for getter_factory in _handler_argval_getters[::-1]:
            # print(3222, getter_factory)
            argval_getter = getter_factory(route_spec, arg_name)
            if argval_getter is not None:
                break

    if argval_getter is None:
        argval_getter = _defaul_argval_getter(route_spec, arg_name)

    if arg_spec.default is not inspect._empty:
        async def _getter(request):
            arg_val = await argval_getter(request)
            # if arg_val is None:
            #     arg_val = arg_spec.default

            return arg_val
    else:
        async def _getter(request):
            try:
                # print(arg_name, argval_getter)
                arg_val = await argval_getter(request)
            except TypeError as exc :
                raise TypeError(f"{exc} while reading '{arg_name}' with "
                                f"'{argval_getter.__qualname__}'")
            return arg_val

    return _getter



#----------------------------------------------------------------------------

def default_argval_getter_factory(route_spec, arg_name):

    if arg_name in route_spec.path_fields:
        async def _path_param_getter(request):
            return request.match_info.get(arg_name)
        return _path_param_getter

    async def _argvalue_func(request):
        if request.method in request.POST_METHODS:
            arg_val = request.post().get(arg_name)
            if arg_val is not None:
                return arg_val

        arg_val = request.query.get(arg_name)
        if arg_val is not None:
            return arg_val

        return None

    return _argvalue_func

def _defaul_argval_getter(route_spec, arg_name):
    arg_spec = inspect.signature(route_spec.handler_func).parameters[arg_name]
    ann_type = arg_spec.annotation

    read_argval = default_argval_getter_factory(route_spec, arg_name)

    if (issubclass(ann_type, int) or issubclass(ann_type, float)):
        async def _getter_func(request):
            arg_val = await read_argval(request)
            if arg_val is not None:
                arg_val = ann_type(arg_val)

            return arg_val
        return _getter_func

    async def _getter_func(request):
        return await read_argval(request)

    return read_argval


async def read_json(request):
    text = await request.text()
    return json.loads(text)


def _json_arg_getter(route_spec, arg_name):
    if arg_name not in ['json_arg', 'json_body']:
        return

    return read_json

def _identity_getter(route_spec, arg_name):
    if arg_name not in ['identity']:
        return
    
    async def _identify(request):
        secure_layer = request.app.get('secure_layer')
        if secure_layer is None:
            return None

        identity = await secure_layer.identify(request)
        return identity

    return _identify

def _datetime_value_getter(route_spec, arg_name):
    arg_spec = inspect.signature(route_spec.handler_func).parameters[arg_name]
    ann_type = arg_spec.annotation

    if not issubclass(ann_type, datetime):
        return

    read_argval = default_argval_getter_factory(route_spec, arg_name)

    async def getter(request):
        arg_val = arrow.get(read_argval(request)).datetime
        return arg_val

    return getter

def _date_value_getter(route_spec, arg_name):
    arg_spec = inspect.signature(route_spec.handler_func).parameters[arg_name]
    ann_type = arg_spec.annotation

    if not issubclass(ann_type, date):
        return

    read_argval = default_argval_getter_factory(route_spec, arg_name)

    async def getter(request, arg_val):
        arg_val = arrow.get(arg_val).datetime.date()
        return arg_val

    return getter


register_argument_getter(_identity_getter)
register_argument_getter(_json_arg_getter)
register_argument_getter(_date_value_getter)
register_argument_getter(_datetime_value_getter)
