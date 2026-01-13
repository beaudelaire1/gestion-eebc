"""
Widgets personnalisés pour les formulaires Django.
"""
from django import forms
from django.utils.safestring import mark_safe
from django.conf import settings

# TinyMCE Self-Hosted CDN (sans clé API, sans restriction de domaine)
TINYMCE_CDN_URL = 'https://cdn.jsdelivr.net/npm/tinymce@6/tinymce.min.js'


class TinyMCEWidget(forms.Textarea):
    """
    Widget TinyMCE pour les champs de texte riche.
    Utilise TinyMCE Self-Hosted via CDN jsDelivr (gratuit, sans restriction).
    """
    
    class Media:
        js = (
            TINYMCE_CDN_URL,
        )
    
    def __init__(self, attrs=None, config=None):
        default_attrs = {
            'class': 'tinymce-widget',
            'rows': 15,
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
        self.config = config or {}
    
    def render(self, name, value, attrs=None, renderer=None):
        # Rendu du textarea standard
        textarea = super().render(name, value, attrs, renderer)
        
        # ID du textarea
        final_attrs = self.build_attrs(attrs, {'name': name})
        textarea_id = final_attrs.get('id', f'id_{name}')
        
        # Configuration TinyMCE complète
        config = {
            'selector': f'#{textarea_id}',
            'language': 'fr_FR',
            'height': 400,
            'menubar': True,
            'branding': False,
            'promotion': False,
            'plugins': [
                'advlist', 'autolink', 'lists', 'link', 'image', 'charmap',
                'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                'insertdatetime', 'media', 'table', 'preview', 'help', 'wordcount',
                'emoticons'
            ],
            'toolbar': (
                'undo redo | blocks fontfamily fontsize | '
                'bold italic underline forecolor backcolor | '
                'alignleft aligncenter alignright alignjustify | '
                'bullist numlist outdent indent | '
                'link image emoticons charmap | '
                'table | removeformat code fullscreen | help'
            ),
            'entity_encoding': 'raw',
            'link_default_target': '_blank',
            'content_style': '''
                @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
                body { 
                    font-family: 'Poppins', sans-serif; 
                    font-size: 14px; 
                    line-height: 1.7;
                    color: #0B0F19;
                    padding: 15px;
                }
                h1, h2, h3, h4 { color: #0A36FF; font-weight: 600; }
                a { color: #0A36FF; }
                blockquote {
                    border-left: 4px solid #0A36FF;
                    padding: 0.5em 1em;
                    margin: 1em 0;
                    background: #F1F5F9;
                    color: #334155;
                    font-style: italic;
                }
            ''',
        }
        config.update(self.config)
        
        # Script d'initialisation
        import json
        config_json = json.dumps(config)
        
        script = f'''
        <script>
        (function() {{
            function initTinyMCE_{textarea_id.replace('-', '_')}() {{
                if (typeof tinymce !== 'undefined') {{
                    tinymce.remove('#{textarea_id}');
                    tinymce.init({config_json});
                }} else {{
                    setTimeout(initTinyMCE_{textarea_id.replace('-', '_')}, 100);
                }}
            }}
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', initTinyMCE_{textarea_id.replace('-', '_')});
            }} else {{
                initTinyMCE_{textarea_id.replace('-', '_')}();
            }}
        }})();
        </script>
        '''
        
        return mark_safe(textarea + script)
