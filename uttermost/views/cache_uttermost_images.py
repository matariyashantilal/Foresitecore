from django.http import HttpResponse
from . import get_uttermost_image_urls

getuttermostimageurlsObj = get_uttermost_image_urls.GetUttermostImageUrls()


def cache_uttermost_images(request):
    return HttpResponse(getuttermostimageurlsObj.cache_uttermost_images_links())
