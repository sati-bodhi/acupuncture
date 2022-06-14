from django.contrib.gis.geoip2 import GeoIP2
from django.conf import settings

settings.configure()

g = GeoIP2()