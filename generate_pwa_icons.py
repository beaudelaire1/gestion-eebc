"""
Script pour générer les icônes PWA placeholder.
Utilise Pillow pour créer des icônes simples avec le logo EEBC.
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Tailles d'icônes requises pour PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# Couleurs
PRIMARY_COLOR = (10, 54, 255)  # #0A36FF
WHITE = (255, 255, 255)

# Dossier de sortie
OUTPUT_DIR = 'static/icons'

def create_icon(size):
    """Crée une icône PWA de la taille spécifiée."""
    # Créer une image avec fond bleu
    img = Image.new('RGB', (size, size), PRIMARY_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Dessiner un cercle blanc au centre
    margin = size // 8
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=WHITE
    )
    
    # Ajouter le texte "EEBC"
    text = "EEBC"
    
    # Calculer la taille de police appropriée
    font_size = size // 4
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # Centrer le texte
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    draw.text((x, y), text, fill=PRIMARY_COLOR, font=font)
    
    return img

def main():
    # Créer le dossier si nécessaire
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Génération des icônes PWA...")
    
    for size in ICON_SIZES:
        filename = f"icon-{size}x{size}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        icon = create_icon(size)
        icon.save(filepath, 'PNG')
        print(f"  ✓ {filename}")
    
    print(f"\n{len(ICON_SIZES)} icônes générées dans {OUTPUT_DIR}/")
    print("\nNote: Ces icônes sont des placeholders. Remplacez-les par vos vraies icônes.")

if __name__ == '__main__':
    main()
