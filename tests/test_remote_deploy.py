import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "remote-deploy.sh"

FAKE_DOCKER = r"""#!/usr/bin/env bash
echo "docker $*" >> "$FASOSEARCH_DIR/docker.log"
tag=$(grep -E '^IMAGE_TAG=' "$FASOSEARCH_DIR/.env" | tail -1 | cut -d= -f2-)
case "$1" in
  inspect) if [ "$tag" = "bad" ]; then echo unhealthy; else echo healthy; fi ;;
  images) printf '%s\n' old1 old2 good latest ;;
esac
exit 0
"""


@pytest.fixture
def env(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    docker = bindir / "docker"
    docker.write_text(FAKE_DOCKER)
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
    e = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", FASOSEARCH_DIR=str(tmp_path),
             HEALTH_TIMEOUT="2", HEALTH_INTERVAL="1")
    (tmp_path / "docker-compose.prod.yml").write_text("services: {}\n")
    return tmp_path, e


def run(env_tuple, *args):
    d, e = env_tuple
    return subprocess.run(["bash", str(SCRIPT), *args], env=e, capture_output=True, text=True)


def read_env(d):
    return dict(l.split("=", 1) for l in (d / ".env").read_text().split() if "=" in l)


def test_deploy_healthy_records_tags_and_cleans(env):
    d, _ = env
    (d / ".env").write_text("IMAGE_TAG=old1\n")
    r = run(env, "deploy", "good")
    assert r.returncode == 0, r.stderr
    assert read_env(d) == {"IMAGE_TAG": "good", "PREV_IMAGE_TAG": "old1"}
    log = (d / "docker.log").read_text()
    assert "compose" in log and "pull" in log and "up -d" in log
    assert "rmi ghcr.io/abdazz/fasosearch:old2" in log
    assert "rmi ghcr.io/abdazz/fasosearch:old1" not in log      # version précédente gardée


def test_deploy_unhealthy_rolls_back(env):
    d, _ = env
    (d / ".env").write_text("IMAGE_TAG=good\n")
    r = run(env, "deploy", "bad")
    assert r.returncode != 0
    assert read_env(d)["IMAGE_TAG"] == "good"
    assert "retour" in r.stderr.lower()


def test_first_deploy_failure_without_previous_fails_cleanly(env):
    d, _ = env
    r = run(env, "deploy", "bad")          # pas de .env : aucune version précédente réelle
    assert r.returncode != 0
    assert "aucune version" in r.stderr.lower()


def test_rollback_command(env):
    d, _ = env
    (d / ".env").write_text("IMAGE_TAG=good2\nPREV_IMAGE_TAG=good\n")
    r = run(env, "rollback")
    assert r.returncode == 0, r.stderr
    assert read_env(d)["IMAGE_TAG"] == "good"


def test_usage_error(env):
    assert run(env).returncode == 2
