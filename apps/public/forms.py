from django import forms
from apps.core.models import NewsArticle, PageContent, Testimony, WorshipSchedule, ContactMessage

class NewsArticleForm(forms.ModelForm):
    class Meta:
        model = NewsArticle
        fields = [
            'title', 'slug', 'category', 'excerpt', 'content', 
            'featured_image', 'site', 'author_name', 'is_published', 
            'is_featured', 'publish_date', 'display_start_date', 'display_end_date'
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
            'publish_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'display_start_date': forms.DateInput(attrs={'type': 'date'}),
            'display_end_date': forms.DateInput(attrs={'type': 'date'}),
        }

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
