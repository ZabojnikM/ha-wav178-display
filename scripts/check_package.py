"""Validate tracked public files and the app manifest without reading private files."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def validate():
    config = json.loads((ROOT / 'wav178_display/config.json').read_text(encoding='utf-8'))
    assert set(config['arch']) == {'amd64', 'aarch64'}
    assert config['homeassistant_api'] is True
    assert config['ports'] == {'6868/tcp': 6868}
    assert config['ingress'] is True and config['ingress_port'] == 8099
    assert not config.get('host_network') and not config.get('privileged')
    assert not config.get('hassio_api') and not config.get('docker_api')
    assert set(config['options']) == set(config['schema'])
    assert 'image' not in config, 'This version builds from repository during installation.'
    assert b'\r' not in (ROOT / 'wav178_display/run.sh').read_bytes()
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    assert any(tracked), 'No tracked files to validate.'
    for name in filter(None, tracked):
        assert not any(part in ('work', 'outputs', 'logs', '__pycache__', '.venv') for part in Path(name).parts), name
        assert '.local.' not in name and not name.endswith(('.apk', '.7z', '.zip', '.env')), name
        assert not name.endswith(('dashboard-live.png', 'ha-entities.json', 'ha-snapshot.json')), name
    print(f'Package OK: {len(list(filter(None, tracked)))} tracked files, no private exports.')


if __name__ == '__main__':
    validate()
