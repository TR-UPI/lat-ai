"""Run the supplied, unchanged Django project against an isolated local database."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

PROJECT = Path(__file__).resolve().parents[1]
BACKEND = PROJECT / "backend"
workspace_runtime = PROJECT.parent.parent / "work" / "runtime"
RUNTIME = Path(os.environ.get("LAT_RUNTIME_DIR", str(workspace_runtime if (workspace_runtime / "python-env" / "python.exe").exists() else PROJECT / ".runtime"))).resolve()
STATE = RUNTIME / "lat-ai-local"
PYTHON = RUNTIME / "python-env" / "python.exe"
PG_BIN = RUNTIME / "postgres16" / "Library" / "bin"


def settings():
    STATE.mkdir(parents=True, exist_ok=True)
    location = STATE / "private-settings.json"
    if location.exists():
        data = json.loads(location.read_text(encoding="utf-8"))
    else:
        data = {
            "database": "lat_ai_demo", "db_user": "lat_ai_demo", "db_port": 55432,
            "db_password": secrets.token_urlsafe(32), "admin_password": secrets.token_urlsafe(32),
            "secret_key": secrets.token_urlsafe(64),
            "demo_email": "demo@lat-ai.local", "demo_password": "LatAI-Demo-2026!",
        }
        location.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if data["database"] != "lat_ai_demo" or data["db_user"] != "lat_ai_demo" or data["db_port"] != 55432:
        raise RuntimeError("This launcher only uses its isolated lat_ai_demo database on port 55432.")
    return data


def environment(data):
    env = os.environ.copy()
    archived_packages = RUNTIME / "archive-env" / ".venv" / "Lib" / "site-packages"
    python_path = [str(BACKEND)]
    if archived_packages.is_dir():
        python_path.insert(0, str(archived_packages))
    env.update({
        "DJANGO_SETTINGS_MODULE": "config.settings", "PYTHONPATH": os.pathsep.join(python_path),
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "DEBUG": "True",
        "SECRET_KEY": data["secret_key"], "ALLOWED_HOSTS": "127.0.0.1,localhost",
        "DB_NAME": data["database"], "DB_USER": data["db_user"],
        "DB_PASSWORD": data["db_password"], "DB_HOST": "127.0.0.1", "DB_PORT": str(data["db_port"]),
        "CORS_ALLOWED_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173",
        "MEDIA_ROOT": str(STATE / "media"), "HF_HOME": str(RUNTIME / "model-cache"),
        "HF_HUB_DISABLE_SYMLINKS_WARNING": "1", "TOKENIZERS_PARALLELISM": "false",
        "LAT_DEMO_EMAIL": data["demo_email"], "LAT_DEMO_PASSWORD": data["demo_password"],
        "LAT_API_BASE": "http://127.0.0.1:8000/api/v1",
    })
    env["PATH"] = str(PG_BIN) + os.pathsep + str(PYTHON.parent / "Library" / "bin") + os.pathsep + env.get("PATH", "")
    if (RUNTIME / "model-cache" / ".lat-ai-e5-ready.json").is_file():
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
    return env


def run(args, env, cwd=BACKEND):
    subprocess.run([str(arg) for arg in args], cwd=cwd, env=env, check=True)


def port_open(port):
    with socket.socket() as connection:
        connection.settimeout(.3)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def start_database(data, env):
    cluster = STATE / "postgres-data"
    if not (cluster / "PG_VERSION").exists():
        password_file = STATE / "init-password.txt"
        password_file.write_text(data["admin_password"], encoding="utf-8")
        try:
            run([PG_BIN / "initdb.exe", "-D", cluster, "-U", "postgres", "-A", "scram-sha-256", "--pwfile", password_file, "--encoding=UTF8", "--locale=C"], env)
        finally:
            password_file.unlink(missing_ok=True)
    status = subprocess.run([str(PG_BIN / "pg_ctl.exe"), "-D", str(cluster), "status"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if status.returncode:
        if port_open(data["db_port"]):
            raise RuntimeError("Port 55432 is occupied by another database. It was not changed.")
        run([PG_BIN / "pg_ctl.exe", "-D", cluster, "-l", STATE / "postgres.log", "-o", "-h 127.0.0.1 -p 55432", "-w", "start"], env)
    admin_env = {**env, "PGPASSWORD": data["admin_password"], "PGCLIENTENCODING": "UTF8"}
    def sql(query, database="postgres"):
        result = subprocess.run([str(PG_BIN / "psql.exe"), "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", "55432", "-U", "postgres", "-d", database], input=query, text=True, encoding="utf-8", capture_output=True, env=admin_env, check=True)
        return result.stdout.strip()
    actual = Path(sql("SHOW data_directory;")).resolve()
    if actual != cluster.resolve():
        raise RuntimeError("The database is not this launcher's isolated cluster.")
    if not sql("SELECT 1 FROM pg_roles WHERE rolname='lat_ai_demo';"):
        password_literal = "'" + data["db_password"].replace("'", "''") + "'"
        sql("CREATE ROLE lat_ai_demo LOGIN PASSWORD " + password_literal + ";")
    if not sql("SELECT 1 FROM pg_database WHERE datname='lat_ai_demo';"):
        sql("CREATE DATABASE lat_ai_demo OWNER lat_ai_demo;")
    sql("CREATE EXTENSION IF NOT EXISTS vector;", data["database"])
    version = sql("SELECT extversion FROM pg_extension WHERE extname='vector';", data["database"])
    print("PostgreSQL ready on 127.0.0.1:55432; pgvector " + version, flush=True)


def launch(args, log_name, env, cwd):
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    with (STATE / log_name).open("ab") as log:
        process = subprocess.Popen([str(arg) for arg in args], cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, creationflags=flags)
    return process.pid


def start_servers(env):
    if not port_open(8000):
        pid = launch([PYTHON, "-m", "django", "runserver", "127.0.0.1:8000", "--noreload"], "django.log", env, BACKEND)
        (STATE / "django.pid").write_text(str(pid), encoding="ascii")
    for _ in range(90):
        try:
            with urlopen("http://127.0.0.1:8000/health/", timeout=2) as response:
                if json.load(response).get("status") == "ok":
                    break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("Django did not become ready. See " + str(STATE / "django.log"))
    if not port_open(5173):
        launch(["node", PROJECT / "server.cjs"], "frontend.log", env, PROJECT)
    print("Frontend: http://localhost:5173/\nBackend: http://127.0.0.1:8000/health/", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["database", "migrate", "seed", "warmup", "start", "prepare", "verify"])
    args = parser.parse_args()
    if not PYTHON.exists() or not (PG_BIN / "initdb.exe").exists():
        raise RuntimeError("Run tools/setup-runtime.ps1 first to install the local Python and PostgreSQL runtime.")
    data = settings()
    env = environment(data)
    if args.command in ["database", "prepare", "start"]:
        start_database(data, env)
    if args.command in ["migrate", "prepare"]:
        run([PYTHON, "-m", "django", "check"], env)
        run([PYTHON, "-m", "django", "migrate", "--noinput"], env)
    if args.command in ["seed", "prepare"]:
        run([PYTHON, PROJECT / "tools" / "seed_learning.py", "--isolated-database"], env)
    if args.command in ["warmup", "prepare"]:
        run([PYTHON, "-c", "from documents.embedding_service import generate_query_embedding; v=generate_query_embedding('Проверка учебных материалов'); assert len(v)==384; print('Semantic search model ready: 384 dimensions')"], env)
    if args.command in ["start", "prepare"]:
        start_servers(env)
    if args.command == "verify":
        run([PYTHON, PROJECT / "tools" / "verify_real_api.py"], env)


if __name__ == "__main__":
    main()
