
from django import forms
from django.forms.extras import SelectDateWidget
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from .models import get_domains

class SideBySideSelectMultiple(forms.SelectMultiple):
    class Media:
        css = {
            'all': [static('css/multi-select.css')],
        }
        js = [static('js/jquery.multi-select.js'),]

    def render(self, name, value, attrs=None, choices=()):
        output = [super(SideBySideSelectMultiple, self).render(name, value, attrs, choices)]
        output.append('<script type="text/javascript">$(window).ready(function(){ $("#id_%s").multiSelect({selectableHeader: "<p>exclude</p>", selectionHeader: "<p>include</p>"}); })</script>' % name)
        return mark_safe(''.join(output))


class ExportForm(forms.Form):
    domains = forms.MultipleChoiceField(label='Which domains', choices=lambda: [(x, x) for x in get_domains()], widget=SideBySideSelectMultiple)

    date_field = forms.ChoiceField(label='Select period by', choices=[('downloaded__parsed_date', 'Published'),
                                                                      ('fb_created', 'Facebook catalogued'),
                                                                      ('spideredurl__sharewarsurl__when', 'Sharewars spidered')])
    date_since = forms.DateField(label='Since', widget=SelectDateWidget(years=range(2011, 2020)))
    date_until = forms.DateField(label='Until', widget=SelectDateWidget(years=range(2011, 2020)))

    contains = forms.CharField(label='Article contains')

    grouping = forms.ChoiceField(label='Group and filter', choices=[('topn', 'Get top overall'),
                                                                    ('topndomain', 'Get top per domain'),
                                                                    ('sd', 'Get standard deviation ranges')],
                                 widget=forms.RadioSelect)
    measure = forms.ChoiceField(label='Rank articles by', choices=[('fb_count_5d', 'Facebook total @5 days'),
                                                                   ('tw_count_5d', 'Twitter total @5 days'),
                                                                   ('fb_count_longterm', 'Facebook total @>1 month'),
                                                                   ('tw_fb_ratio_5d', 'Twitter/facebook @5 days')])
    normalise = forms.BooleanField(label='Normalise for month and domain', required=False)

    # Quality controls
    min_fb_count_5d = forms.IntegerField(label='Minimum Facebook total @5 days', min_value=0)
    min_tw_count_5d = forms.IntegerField(label='Minimum Twitter total @5 days', min_value=0)
    min_fb_count_longterm = forms.IntegerField(label='Minimum Facebook total @>1 month', min_value=0)
    require_longterm_valid = forms.BooleanField(label='Require FB total @>1 month larger than @5 days', required=False)
    has_extracted = forms.MultipleChoiceField(label='Has extracted', choices=[('headline', 'Headline'),
                                                                              ('byline', 'Byline'),
                                                                              ('dateline', 'Dateline'),
                                                                              ('body text', 'Body text')])
    date_validity = forms.IntegerField(label='Days between spider and FB cataloguing', min_value=0)

    # XXX: Would be nice to automatically sub in radio sub-fields
    sampling = forms.ChoiceField(label='Reduced sample', choices=[('', 'get all matching (may be very big)'),
                                                                  ('undersample', 'undersample: sample all groups to be the same size as the smallest group'),
                                                                  ('atmost', 'at most N per group'),
                                                                  ('percent', 'N percent')],
                                 widget=forms.RadioSelect)

    # TODO: name this setup, notes, export format options
