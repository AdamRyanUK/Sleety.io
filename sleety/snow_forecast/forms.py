from django import forms
from .models import Resort

class ResortForm(forms.ModelForm):
    class Meta:
        model = Resort
        fields = ('country', 'name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].queryset = Resort.objects.none()

        if 'country' in self.data:
            try:
                country_id = int(self.data.get('country'))
                self.fields['name'].queryset = Resort.objects.filter(country_id=country_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
        elif self.instance.pk:
            self.fields['name'].queryset = self.instance.country.name_set.order_by('name')