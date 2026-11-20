"""
Deploy controlat pe Cloudflare Workers + D1 + KV, rulat EXCLUSIV dupa revizuirea
si aprobarea utilizatorului in `clubturistic.db`.
"""

import json
import os
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CF_DIR = os.path.join(BASE_DIR, "cloudflare")
KV_NS = "36c56dede5934239a6853eb52f89195d"
LIVE_BASE = "https://clubturistic.clubturistic.workers.dev"


def load_cf_env() -> dict[str, str]:
    env = os.environ.copy()
    if os.name == "nt":
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            for name in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
                if not env.get(name):
                    try:
                        val, _ = winreg.QueryValueEx(key, name)
                        if val:
                            env[name] = str(val)
                    except OSError:
                        pass
    if not env.get("CLOUDFLARE_API_TOKEN") or not env.get("CLOUDFLARE_ACCOUNT_ID"):
        raise RuntimeError("Lipsesc CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID din User env.")
    return env


def run_step(cmd: list[str], cwd: str = BASE_DIR, env: dict[str, str] | None = None) -> None:
    print("->", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def main() -> None:
    env = load_cf_env()
    npx_prefix = ["cmd", "/c", "npx.cmd", "--yes", "wrangler"] if os.name == "nt" else ["npx", "--yes", "wrangler"]

    run_step([sys.executable, os.path.join("scripts", "build_cloudflare_bundle.py")])
    run_step([sys.executable, os.path.join("scripts", "prepare_cf_deploy.py")])

    run_step([*npx_prefix, "d1", "execute", "clubturistic-db", "--remote", "--file=schema.sql", "--yes"], cwd=CF_DIR, env=env)
    run_step([*npx_prefix, "d1", "execute", "clubturistic-db", "--remote", "--file=seed.sql", "--yes"], cwd=CF_DIR, env=env)
    run_step([*npx_prefix, "kv", "bulk", "put", "kv_static.json", f"--namespace-id={KV_NS}", "--remote"], cwd=CF_DIR, env=env)
    run_step([*npx_prefix, "deploy"], cwd=CF_DIR, env=env)

    # Verificare live automata post-deploy
    with urllib.request.urlopen(urllib.request.Request(f"{LIVE_BASE}/api/stats", headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
        assert r.status == 200
        stats = json.loads(r.read().decode("utf-8"))
        print("LIVE /api/stats:", stats)
    with urllib.request.urlopen(urllib.request.Request(f"{LIVE_BASE}/sitemap.xml", headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
        assert r.status == 200
        xml_txt = r.read().decode("utf-8")
        print("LIVE /sitemap.xml URLs:", xml_txt.count("<url>"))


if __name__ == "__main__":
    main()
