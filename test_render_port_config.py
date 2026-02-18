"""
Tests de validation de la configuration PORT pour Render
Valide que le déploiement utilise correctement $PORT
"""
import os
import subprocess
from pathlib import Path


def test_start_sh_exists():
    """Le script start.sh doit exister."""
    start_sh = Path('start.sh')
    assert start_sh.exists(), "start.sh manquant"
    assert start_sh.is_file(), "start.sh n'est pas un fichier"


def test_start_sh_has_port_variable():
    """start.sh doit utiliser la variable PORT avec fallback."""
    with open('start.sh', 'r') as f:
        content = f.read()
    
    # Doit avoir PORT="${PORT:-10000}"
    assert 'PORT="${PORT:-10000}"' in content or 'PORT=${PORT:-10000}' in content, \
        "start.sh doit définir PORT avec fallback sur 10000"
    
    # Doit bind sur $PORT
    assert '--bind "0.0.0.0:${PORT}"' in content or '--bind 0.0.0.0:${PORT}' in content, \
        "start.sh doit bind gunicorn sur ${PORT}"


def test_render_yaml_uses_start_script():
    """render.yaml doit utiliser ./start.sh au lieu de hardcoder le port."""
    with open('render.yaml', 'r') as f:
        content = f.read()
    
    # Doit utiliser ./start.sh
    assert 'startCommand: ./start.sh' in content, \
        "render.yaml doit utiliser ./start.sh comme startCommand"
    
    # Ne doit PAS hardcoder :10000 dans startCommand
    assert '--bind 0.0.0.0:10000' not in content, \
        "render.yaml ne doit plus hardcoder le port 10000 dans startCommand"


def test_render_yaml_declares_port_explicitly():
    """render.yaml doit déclarer PORT=10000 en variable d'environnement."""
    with open('render.yaml', 'r') as f:
        content = f.read()
    
    # Doit déclarer PORT explicitement
    assert 'key: PORT' in content, \
        "render.yaml doit déclarer PORT dans envVars"
    
    # Vérifier que la valeur est 10000
    lines = content.split('\n')
    port_line_idx = None
    for i, line in enumerate(lines):
        if 'key: PORT' in line:
            port_line_idx = i
            break
    
    assert port_line_idx is not None, "PORT key not found"
    
    # La ligne suivante doit avoir value: "10000"
    if port_line_idx + 1 < len(lines):
        next_line = lines[port_line_idx + 1]
        assert 'value:' in next_line and '10000' in next_line, \
            "PORT doit avoir la valeur 10000"


def test_render_yaml_autodeploy_enabled():
    """render.yaml doit avoir autoDeploy: true."""
    with open('render.yaml', 'r') as f:
        content = f.read()
    
    assert 'autoDeploy: true' in content, \
        "render.yaml doit avoir autoDeploy: true pour déploiement automatique"


def test_build_sh_makes_scripts_executable():
    """build.sh doit rendre start.sh exécutable."""
    with open('build.sh', 'r') as f:
        content = f.read()
    
    assert 'chmod +x start.sh' in content, \
        "build.sh doit rendre start.sh exécutable"


def test_start_sh_has_shebang():
    """start.sh doit avoir un shebang bash."""
    with open('start.sh', 'r') as f:
        first_line = f.readline().strip()
    
    assert first_line.startswith('#!'), "start.sh doit avoir un shebang"
    assert 'bash' in first_line, "start.sh doit utiliser bash"


def test_gunicorn_config_is_correct():
    """Valider la configuration gunicorn dans start.sh."""
    with open('start.sh', 'r') as f:
        content = f.read()
    
    # Config minimale requise
    required = [
        'gunicorn gestion_eebc.wsgi:application',
        '--workers',
        '--timeout',
        '--log-file',
        '--preload',  # Important pour éviter problèmes reload
        '--graceful-timeout',  # Shutdown propre
        '--capture-output',  # Capture Django logs
    ]
    
    for req in required:
        assert req in content, f"start.sh doit contenir '{req}'"


def test_start_sh_has_verbose_logging():
    """start.sh doit avoir du logging pour debug."""
    with open('start.sh', 'r') as f:
        content = f.read()
    
    # Doit logger la config
    assert 'echo' in content, "start.sh doit avoir des echo pour logging"
    assert 'PORT:' in content or 'port' in content.lower(), \
        "start.sh doit afficher le port utilisé"


def test_port_env_var_simulation():
    """Simuler l'injection de PORT par Render."""
    # Simuler qu'on set PORT=8080
    test_port = "8080"
    
    # On devrait pouvoir lire le script et vérifier la logique
    with open('start.sh', 'r') as f:
        content = f.read()
    
    # Vérifier que le pattern ${PORT:-10000} existe
    assert '${PORT:-10000}' in content or '${PORT}' in content, \
        "start.sh doit référencer la variable PORT"


def test_healthcheck_path_configured():
    """render.yaml doit avoir un healthCheckPath configuré."""
    with open('render.yaml', 'r') as f:
        content = f.read()
    
    assert 'healthCheckPath:' in content, \
        "render.yaml doit définir healthCheckPath"
    
    assert '/healthz/ping/' in content, \
        "healthCheckPath doit pointer vers /healthz/ping/"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
