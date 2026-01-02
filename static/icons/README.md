# Icônes PWA

Ce dossier doit contenir les icônes de l'application pour le PWA.

## Tailles requises

- icon-72x72.png
- icon-96x96.png
- icon-128x128.png
- icon-144x144.png
- icon-152x152.png
- icon-192x192.png
- icon-384x384.png
- icon-512x512.png

## Génération

Vous pouvez générer ces icônes à partir d'une image source (512x512 minimum) avec des outils comme :

- https://realfavicongenerator.net/
- https://www.pwabuilder.com/imageGenerator
- ImageMagick (ligne de commande)

## Exemple avec ImageMagick

```bash
# Depuis une image source icon-512x512.png
convert icon-512x512.png -resize 72x72 icon-72x72.png
convert icon-512x512.png -resize 96x96 icon-96x96.png
convert icon-512x512.png -resize 128x128 icon-128x128.png
convert icon-512x512.png -resize 144x144 icon-144x144.png
convert icon-512x512.png -resize 152x152 icon-152x152.png
convert icon-512x512.png -resize 192x192 icon-192x192.png
convert icon-512x512.png -resize 384x384 icon-384x384.png
```
