import colander
import deform
import shutil
import os

from deform import Form
from deform import ValidationFailure
from pyramid.view import view_config
from pyramid.threadlocal import get_current_registry
from pyramid.httpexceptions import HTTPBadRequest

from restrepo.db.settings import Settings
from restrepo.config import CACHE_SUBDIRECTORY
from restrepo.storage import real_path

from restrepo.browser.admin import _patch_request


class Store(dict):
    def preview_url(self, name):
        return ""


store = Store()


class Configuration(colander.MappingSchema):

    watermark_file = colander.SchemaNode(
        colander.String(),
        widget=deform.widget.TextInputWidget(size=1000),
        missing='',
        description='This should be a path on the local filesystem, relative to the directory ...'
    )

    watermark_pos_x = colander.SchemaNode(
        colander.String(),
        missing=10,
        description='The distance, in pixels, of the watermark relative to the right border of the image',
        title="watermark pos_x",
    )

    watermark_pos_y = colander.SchemaNode(
        colander.String(),
        missing=10,
        description='The distance, in pixels, of the watermark relative to the bottom border of the image',
        title="watermark pos_y",
    )

    watermark_size = colander.SchemaNode(
        colander.String(),
        missing='4%',
        description='The size of the watermark. This can be a percentage (such as "4%") or a number of pixels (such as "14")',
        title="watermark size",
    )


class ConfigurationViews(object):
    def __init__(self, request):
        _patch_request(request)
        self.request = request

    def get_setting(self, context, key, default_value):
        setting = context.db.query(Settings).get(key)
        if setting:
            return setting.value
        else:
            return default_value

    def set_setting(self, context, key, value):
        setting = context.db.query(Settings).get(key)
        if not setting:
            setting = Settings()
            setting.key = key
            context.db.add(setting)
        setting.value = value
        get_current_registry().settings.update(**{key: value})

    @view_config(
        route_name='configuration',
        permission='write',
        renderer='configuration.pt')
    def site_view(self):
        def refresh_cache():
            # we simply remove all cached files
            cache_directory = real_path(CACHE_SUBDIRECTORY)
            if os.path.exists(cache_directory):
                for fn in os.listdir(cache_directory):
                    shutil.rmtree(os.path.join(cache_directory, fn))

        schema = Configuration()
        settings = get_current_registry().settings

        def get_some_scan(request):
            result = request.solr_scan.search(q='*:*', rows=1)
            if not result.documents:
                return None
            doc = result.documents[0]
            url = request.route_url('service_scan_images_item', number=str(doc['number']), number_of_image=doc['default_image_id'])
            image_url = os.path.join(url, 'file_%s' % str(hash(doc['dateLastModified'])))
            return image_url

        example_image = ''

        default_values = [(node.name, unicode(settings.get(node.name, 'xxx'))) for node in schema.children]
        form = Form(schema, buttons=('submit',))
        if self.request.POST:
            controls = self.request.POST.items()
            try:
                appstruct = form.validate(controls)
            except ValidationFailure, e:
                return {'form': e.render(), 'example_image': example_image}

            # Process the valid form data, do some work
            # if the file does not exist, we raise a validation error
            if appstruct['watermark_file'] and not os.path.exists(appstruct['watermark_file']):
                raise HTTPBadRequest('This file {watermark_file} cannot be found'.format(**appstruct))
            # if anything has changed, we reset the cache
            for key in appstruct:
                if settings.get(key) != appstruct[key]:
                    refresh_cache()
                    continue

            for key in appstruct:
                # save the new settings in the database
                self.set_setting(self.request, key, appstruct[key])

            # update the global settings object with our new values
            settings.update(appstruct)
            example_image = get_some_scan(self.request)
            return {"form": form.render(), 'example_image': example_image}

        # We are a GET not a POST
        else:
            appstruct = form.validate(default_values)
            example_image = get_some_scan(self.request)
            return {"form": form.render(), 'example_image': example_image}
