from pyramid.view import view_config
from pyramid.renderers import render_to_response
from pyramid.threadlocal import get_current_registry


@view_config(route_name='root', permission='write')
def list_view(request):
    _patch_request(request)
    return render_to_response('index.pt', {}, request=request)


@view_config(route_name='admin_archives', permission='write')
def admin_archives(request):
    _patch_request(request)
    return render_to_response('admin_archives.pt', {}, request=request)


def _patch_request(request):
    # XXX: nasty emergency hack because I cannot seem to get wsgi.url_scheme to work
    _old = request.static_url
    settings = get_current_registry().settings

    def _new(*args, **kwargs):
        if settings.get('url_scheme') == 'https':
            kwargs['_scheme'] = 'https'
        return _old(*args, **kwargs)

    request.static_url = _new
