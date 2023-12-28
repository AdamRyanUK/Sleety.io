from django.db import models
from django.utils.translation import gettext as _

class Resort(models.Model):
    name = models.CharField(_("name"), max_length=100)
    country = models.CharField(_("country"), max_length=20)
    continent = models.CharField(_("continent"), max_length=64)
    state_province = models.CharField(_("state_province"), max_length=64, blank=True)
    timezone = models.CharField(_("timezone"), max_length=64, blank=True)
    lat = models.FloatField(_("lat"))
    lon = models.FloatField(_("lon"))
    base = models.IntegerField(_("base"))
    mid = models.IntegerField(_("mid"))
    top = models.IntegerField(_("top"))

    def to_json(self):
        return {
            'name': self.name,
            'country': self.country,
            'continent': self.continent,
            'state_province': self.state_province,
            'timezone': self.timezone,
            'lat': self.lat,
            'lon': self.lon,
            'base': self.base,
            'mid': self.mid,
            'top': self.top,
        }

    @classmethod
    def from_json(cls, data):
        return cls(
            name=data['name'],
            country=data['country'],
            continent=data['continent'],
            state_province=data['state_province'],
            timezone=data['timezone'],
            lat=data['lat'],
            lon=data['lon'],
            base=data['base'],
            mid=data['mid'],
            top=data['top'],
        )
    
    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Resorts'
