$flutterRoot = "$env:USERPROFILE\dev\flutter"
$flutterBin = Join-Path $flutterRoot "bin"

if (-not (Test-Path (Join-Path $flutterBin "flutter.bat"))) {
    Write-Error "Flutter introuvable dans $flutterBin. Installez-le d'abord dans $flutterRoot."
    exit 1
}

$env:PATH = "$flutterBin;$env:PATH"
Write-Host "Flutter activé pour cette session: $flutterBin" -ForegroundColor Green
flutter --version
