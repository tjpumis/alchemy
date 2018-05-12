import inspect
from urllib.parse import urljoin
from collections import OrderedDict
from pkgutil import walk_packages
from importlib import  import_module

from aiohttp.web_urldispatcher import DynamicResource

from .handler import request_handler_factory
from .route_spec import parse_path, routespec_registry

import aiohttp.web

def register_module(app, root, *, prefix='/'):

    for module_name in list(routespec_registry.keys()):
        if module_name.startswith(root):
            del routespec_registry[module_name]

    if not prefix.startswith('/') :
        raise ValueError(f"The prefix '{prefix}' should start with '/'")

    assert isinstance(root, str) and len(root) > 1 and not root.endswith('.')

    resources = OrderedDict() # group route specs by the path's pattern
    for path_base, route_specs in _normal_path_base(root, prefix):
        for spec in route_specs:
            spec.set_prefix(path_base)
            group_key = (spec.path_pattern, spec.path_formatter)
            if group_key not in resources:
                resources[group_key] = [spec]
            else:
                specs = resources[group_key]

                for s in specs: # check method conflict
                    for m in spec.methods:
                        if m in s.methods:
                            raise ValueError('confict method')

                specs.append(spec)

    for (path_pattern, path_formatter), specs in resources.items():
        resource  = DynamicResource(path_pattern, path_formatter)
        app.router.register_resource(resource)

        for route_spec in specs:
            for method in route_spec.methods:
                handler = request_handler_factory(route_spec, method)
                route = resource.add_route(method, handler)
                setattr(route, '_route_spec', route_spec)

def _parent_name(module_name):
    idx = module_name.rfind('.')
    return module_name[0:idx] if idx != -1 else ''

def _stem_name(module_name):

    if not module_name: return ''

    idx = module_name.rfind('.')
    return (module_name[(idx+1):] if idx != -1 else module_name) + '/'

def _normal_path_base(root, prefix):
    if not prefix.endswith('/'):
        prefix += '/'

    path_start = len(root) + 1

    module_prefixs = {}
    module_prefixs[''] = prefix
    for module in _iter_submodules(root):

        module_name = module.__name__[path_start:]
        parent_name = _parent_name(module_name)

        route_group = routespec_registry.get(module.__name__)
        if route_group is None:
            path_base = urljoin(module_prefixs[parent_name], _stem_name(module_name))
            module_prefixs[module_name] = path_base
            continue

        if route_group.base_path is None:
            path_base = _stem_name(module_name)
        else:
            path_base = route_group.base_path

        path_base = urljoin(module_prefixs[parent_name], path_base)

        module_prefixs[module_name] = path_base

        if route_group._route_specs:
            yield (path_base, route_group._route_specs)

def _iter_submodules(root_module, recursive=True):
    """  """
    if isinstance(root_module, str):
        root_module = import_module(root_module)

    if not hasattr(root_module, '__path__'):
        yield root_module
        return

    if isinstance(root_module.__path__, list): # no namespace package
        yield root_module

    if not recursive:
        return

    prefix = root_module.__name__ + '.'

    for loader, module_name, ispkg in walk_packages(root_module.__path__, prefix):
        module = loader.find_module(module_name).load_module(module_name)
        if ispkg and not isinstance(module.__path__, list):
            continue

        yield module