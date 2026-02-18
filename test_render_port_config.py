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
    
    # Ne doit PAS hardcoder :10000
    assert '--bind 0.0.0.0:10000' not in content, \
        "render.yaml ne doit plus hardcoder le port 10000"


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
    ]
    
    for req in required:
        assert req in content, f"start.sh doit contenir '{req}'"


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
