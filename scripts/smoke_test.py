"""Sobe os 3 projetos refatorados como servidores reais e testa todos os endpoints originais.

Uso (na raiz do repositório):
    python scripts/smoke_test.py

Cada projeto roda com banco temporário e variáveis de ambiente próprias; o log
de cada execução é salvo em docs/validation/<projeto>.log.
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "docs" / "validation"
ADMIN_TOKEN = "smoke-admin-token"
# Ignora proxies do sistema: os servidores testados são sempre locais.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(base_url, method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base_url + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with OPENER.open(req, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode()
    except OSError as err:
        return None, str(err)


def wait_for_port(port, proc, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.3)
    return False


def display(command):
    """Mostra o comando sem o caminho absoluto do interpretador."""
    return " ".join([Path(command[0]).stem, *command[1:]])


def run_project(name, cwd, command, port, env, cases, setup=None):
    lines = [f"# {name} — {datetime.now().isoformat(timespec='seconds')}"]
    full_env = {**os.environ, **env, "PYTHONIOENCODING": "utf-8"}
    if setup:
        out = subprocess.run(setup, cwd=cwd, env=full_env, capture_output=True, text=True, encoding="utf-8")
        lines.append(f"$ {display(setup)} -> exit {out.returncode}")
        if out.returncode != 0:
            lines.append(out.stderr)
    lines.append(f"$ {display(command)}")
    server_log = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
    proc = subprocess.Popen(command, cwd=cwd, env=full_env, stdout=server_log, stderr=subprocess.STDOUT)
    passed = failed = 0
    try:
        if not wait_for_port(port, proc):
            lines.append("FAIL: servidor não subiu")
            failed += 1
        else:
            lines.append(f"servidor ouvindo em http://127.0.0.1:{port}")
            base_url = f"http://127.0.0.1:{port}"
            context = {}
            for label, method, path, body, headers, expected in cases:
                if callable(path):
                    path = path(context)
                if callable(headers):
                    headers = headers(context)
                status, text = request(base_url, method, path, body, headers)
                ok = status == expected
                passed += ok
                failed += not ok
                lines.append(f"{'PASS' if ok else 'FAIL'} {status} (esperado {expected}) {method} {path} — {label}")
                if label == "login admin" and ok:
                    context["token"] = json.loads(text).get("token")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        server_log.seek(0)
        # Remove códigos de cor ANSI e o IP da rede local que o Flask imprime ao subir.
        server_output = "\n".join(
            re.sub(r"\x1b\[[0-9;]*m", "", line) for line in server_log.read().splitlines()
            if not ("Running on http://" in line and "127.0.0.1" not in line)
        )
        server_log.close()
    lines.append(f"RESULTADO: {passed} passaram, {failed} falharam")
    lines.append("--- saída do servidor ---")
    lines.append(server_output.strip())
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (LOG_DIR / f"{name}.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[: lines.index("--- saída do servidor ---")]))
    print()
    return failed == 0


def project_1(tmp):
    admin = {"X-Admin-Token": ADMIN_TOKEN}
    cases = [
        ("index", "GET", "/", None, None, 200),
        ("listar produtos", "GET", "/produtos", None, None, 200),
        ("buscar produtos", "GET", "/produtos/busca?q=mouse&preco_min=10", None, None, 200),
        ("produto por id", "GET", "/produtos/1", None, None, 200),
        ("criar produto", "POST", "/produtos", {"nome": "Produto Teste", "preco": 10, "estoque": 5}, None, 201),
        ("criar produto inválido", "POST", "/produtos", {"nome": "X", "preco": 10, "estoque": 5}, None, 400),
        ("atualizar produto", "PUT", "/produtos/11", {"nome": "Produto Teste 2", "preco": 12, "estoque": 5}, None, 200),
        ("deletar produto", "DELETE", "/produtos/11", None, None, 200),
        ("listar usuários", "GET", "/usuarios", None, None, 200),
        ("usuário por id", "GET", "/usuarios/1", None, None, 200),
        ("criar usuário", "POST", "/usuarios", {"nome": "Teste", "email": "t@t.com", "senha": "segredo"}, None, 201),
        ("login válido", "POST", "/login", {"email": "admin@loja.com", "senha": "admin123"}, None, 200),
        ("login com SQL injection", "POST", "/login", {"email": "' OR 1=1 --", "senha": "x"}, None, 401),
        ("criar pedido", "POST", "/pedidos", {"usuario_id": 2, "itens": [{"produto_id": 1, "quantidade": 1}]}, None, 201),
        ("criar pedido com quantidade negativa", "POST", "/pedidos",
         {"usuario_id": 2, "itens": [{"produto_id": 1, "quantidade": -3}]}, None, 400),
        ("listar pedidos", "GET", "/pedidos", None, None, 200),
        ("pedidos do usuário", "GET", "/pedidos/usuario/2", None, None, 200),
        ("atualizar status do pedido", "PUT", "/pedidos/1/status", {"status": "aprovado"}, None, 200),
        ("relatório de vendas", "GET", "/relatorios/vendas", None, None, 200),
        ("health", "GET", "/health", None, None, 200),
        ("/admin/query neutralizado", "POST", "/admin/query", {"sql": "DROP TABLE produtos"}, None, 410),
        ("tabela produtos intacta após DROP", "GET", "/produtos/1", None, None, 200),
        ("reset-db sem token", "POST", "/admin/reset-db", None, None, 403),
        ("reset-db com token", "POST", "/admin/reset-db", None, admin, 200),
    ]
    env = {"DATABASE_PATH": str(Path(tmp) / "loja.db"), "ADMIN_TOKEN": ADMIN_TOKEN,
           "SECRET_KEY": "smoke-secret", "PORT": "5101"}
    return run_project("code-smells-project", ROOT / "code-smells-project",
                       [sys.executable, "app.py"], 5101, env, cases)


def project_2(tmp):
    admin = {"x-admin-key": ADMIN_TOKEN}
    checkout = {"usr": "Guilherme", "eml": "gui@fullcycle.com.br", "pwd": "senhaforte", "c_id": 2,
                "card": "4111222233334444"}
    cases = [
        ("checkout aprovado", "POST", "/api/checkout", checkout, None, 200),
        ("checkout recusado", "POST", "/api/checkout", {**checkout, "eml": "joao@teste.com", "card": "5111"}, None, 400),
        ("checkout usuário novo sem senha", "POST", "/api/checkout",
         {**checkout, "eml": "novo@teste.com", "pwd": None}, None, 400),
        ("relatório financeiro sem chave", "GET", "/api/admin/financial-report", None, None, 401),
        ("relatório financeiro com chave", "GET", "/api/admin/financial-report", None, admin, 200),
        ("deletar usuário sem chave", "DELETE", "/api/users/1", None, None, 401),
        ("deletar usuário com chave", "DELETE", "/api/users/1", None, admin, 200),
    ]
    env = {"PORT": "5102", "ADMIN_API_KEY": ADMIN_TOKEN, "PAYMENT_GATEWAY_KEY": "pk_test_smoke"}
    return run_project("ecommerce-api-legacy", ROOT / "ecommerce-api-legacy",
                       ["node", "src/app.js"], 5102, env, cases)


def project_3(tmp):
    def bearer(context):
        return {"Authorization": f"Bearer {context.get('token')}"}

    cases = [
        ("index", "GET", "/", None, None, 200),
        ("health", "GET", "/health", None, None, 200),
        ("listar tasks", "GET", "/tasks", None, None, 200),
        ("task por id", "GET", "/tasks/1", None, None, 200),
        ("buscar tasks", "GET", "/tasks/search?q=a", None, None, 200),
        ("estatísticas", "GET", "/tasks/stats", None, None, 200),
        ("criar task", "POST", "/tasks", {"title": "Task de teste", "priority": 2}, None, 201),
        ("criar task com título curto", "POST", "/tasks", {"title": "ab"}, None, 400),
        ("atualizar task", "PUT", "/tasks/1", {"status": "in_progress"}, None, 200),
        ("deletar task", "DELETE", "/tasks/2", None, None, 200),
        ("listar usuários", "GET", "/users", None, None, 200),
        ("usuário por id", "GET", "/users/1", None, None, 200),
        ("criar usuário", "POST", "/users", {"name": "Teste", "email": "teste@email.com", "password": "segredo"}, None, 201),
        ("criar usuário com e-mail inválido", "POST", "/users",
         {"name": "Teste", "email": "invalido", "password": "segredo"}, None, 400),
        ("atualizar usuário", "PUT", "/users/2", {"name": "Maria S."}, None, 200),
        ("tasks do usuário", "GET", "/users/1/tasks", None, None, 200),
        ("login com senha errada", "POST", "/login", {"email": "joao@email.com", "password": "errada"}, None, 401),
        ("login admin", "POST", "/login", {"email": "joao@email.com", "password": "1234"}, None, 200),
        ("relatório resumo", "GET", "/reports/summary", None, None, 200),
        ("relatório por usuário", "GET", "/reports/user/1", None, None, 200),
        ("listar categorias", "GET", "/categories", None, None, 200),
        ("criar categoria", "POST", "/categories", {"name": "Smoke", "color": "#123456"}, None, 201),
        ("atualizar categoria", "PUT", "/categories/1", {"name": "Trabalho"}, None, 200),
        ("deletar usuário sem token", "DELETE", "/users/3", None, None, 401),
        ("deletar usuário com token admin", "DELETE", "/users/3", None, bearer, 200),
        ("deletar categoria", "DELETE", "/categories/4", None, None, 200),
    ]
    env = {"DATABASE_URL": "sqlite:///" + str(Path(tmp) / "tasks.db").replace("\\", "/"),
           "SECRET_KEY": "smoke-secret", "PORT": "5103"}
    return run_project("task-manager-api", ROOT / "task-manager-api",
                       [sys.executable, "app.py"], 5103, env, cases, setup=[sys.executable, "seed.py"])


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        results = [project_1(tmp), project_2(tmp), project_3(tmp)]
    sys.exit(0 if all(results) else 1)
