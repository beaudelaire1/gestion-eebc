from django import forms
from django.utils.html import escape
from apps.core.models import NewsArticle, PageContent, Testimony, WorshipSchedule, ContactMessage, PublicEvent

class NewsArticleForm(forms.ModelForm):
    class Meta:
        model = NewsArticle
        fields = [
            'title', 'slug', 'category', 'excerpt', 'content', 
            'featured_image', 'site', 'author_name', 'is_published', 
            'is_featured', 'publish_date', 'display_start_date', 'display_end_date'
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10, 'class': 'tinymce-editor'}),
            'publish_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'display_start_date': forms.DateInput(attrs={'type': 'date'}),
            'display_end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = False
        self.fields['content'].help_text = (
            "Optionnel pour une actualité courte : si vide, le résumé sera utilisé automatiquement."
        )

    def clean_content(self):
        if content := (self.cleaned_data.get('content') or '').strip():
            return content

        if excerpt := (self.cleaned_data.get('excerpt') or '').strip():
            safe_excerpt = escape(excerpt).replace('\n', '<br>')
            return f'<p>{safe_excerpt}</p>'

        raise forms.ValidationError("Le contenu ou le résumé est requis.")

class PageContentForm(forms.ModelForm):
    class Meta:
        model = PageContent
        fields = [
            'page_type', 'title', 'slug', 'subtitle', 'content', 
            'header_image', 'meta_description', 'is_published', 
            'show_in_menu', 'menu_order'
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 15}),
        }

class TestimonyForm(forms.ModelForm):
    class Meta:
        model = Testimony
        fields = [
            'author_name', 'author_photo', 'title', 'content', 
            'member', 'is_published', 'is_featured', 'publish_date'
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
            'publish_date': forms.DateInput(attrs={'type': 'date'}),
        }

class WorshipScheduleForm(forms.ModelForm):
    class Meta:
        model = WorshipSchedule
        fields = [
            'site', 'name', 'day_of_week', 'start_time', 'end_time', 
            'description', 'is_active'
        ]
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class PublicEventForm(forms.ModelForm):
    class Meta:
        model = PublicEvent
        fields = [
            'title', 'slug', 'description', 'start_date', 'start_time',
            'end_date', 'end_time', 'location', 'address', 'site',
            'image', 'is_published', 'is_featured', 'allow_registration',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'tinymce-editor'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }
