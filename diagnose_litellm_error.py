#!/usr/bin/env python3
"""
Diagnostic script for 'AsyncCompletions.create() got an unexpected keyword argument input_price_per_mtok'

À exécuter depuis le dossier racine de DeerFlow :
    python diagnose_litellm_error.py

Ou depuis n'importe où avec le bon PYTHONPATH.
"""

import subprocess
import sys
import os
import importlib
import json
from pathlib import Path

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def header(text):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")

def ok(text):
    print(f"  {GREEN}✅{RESET} {text}")

def warn(text):
    print(f"  {YELLOW}⚠️ {RESET}{text}")

def fail(text):
    print(f"  {RED}❌{RESET} {text}")

def info(text):
    print(f"  {CYAN}ℹ️ {RESET}{text}")

# ────────────────────────────────────────────────────
# 1. ENVIRONNEMENT PYTHON
# ────────────────────────────────────────────────────
header("1. ENVIRONNEMENT PYTHON")
print(f"  Python     : {sys.version}")
print(f"  Executable : {sys.executable}")
print(f"  CWD        : {os.getcwd()}")

# ────────────────────────────────────────────────────
# 2. VERSION LITELLM
# ────────────────────────────────────────────────────
header("2. VERSION LITELLM")

try:
    import litellm
    version = litellm.__version__ if hasattr(litellm, "__version__") else "unknown"
    ok(f"litellm installé — version {version}")
    print(f"  Emplacement : {litellm.__file__}")
    
    # Check if input_price_per_mtok exists in AsyncCompletions signature
    try:
        from litellm import acompletion
        import inspect
        sig = inspect.signature(litellm.acompletion)
        params = list(sig.parameters.keys())
        if "input_price_per_mtok" in params:
            fail("input_price_per_mtok EST dans la signature d'acompletion — incompatible avec DeepSeek V3")
        else:
            ok("input_price_per_mtok absent de la signature d'acompletion — cohérent avec l'erreur")
        print(f"  Paramètres acompletion : {params[:15]}...")
    except Exception as e:
        warn(f"Impossible d'inspecter acompletion : {e}")
        
except ImportError:
    fail("litellm non installé !")
    print("  → pip install litellm")

# ────────────────────────────────────────────────────
# 3. CHERCHER input_price_per_mtok DANS LE CODE
# ────────────────────────────────────────────────────
header("3. RECHERCHE 'input_price_per_mtok' DANS LE CODE")

# Chemins probables de DeerFlow
search_paths = []
cwd = Path(os.getcwd())

# Remonter pour trouver deer-flow/backend
for parent in [cwd] + list(cwd.parents):
    backend = parent / "backend"
    if backend.exists():
        search_paths.append(backend)
    deerflow = parent / "deer-flow" / "backend"
    if deerflow.exists():
        search_paths.append(deerflow)
    # Chercher aussi un dossier deerflow direct
    for d in parent.glob("**/deerflow"):
        if d.is_dir():
            search_paths.append(d)

# Ajouter les dossiers python courants
try:
    import site
    for sp in site.getsitepackages():
        search_paths.append(Path(sp))
except Exception:
    pass

found_files = []
for sp in search_paths:
    if not sp.exists():
        continue
    for py_file in sp.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "input_price_per_mtok" in content:
                found_files.append(py_file)
                # Extraire la ligne exacte
                for i, line in enumerate(content.split("\n"), 1):
                    if "input_price_per_mtok" in line:
                        found_files.append((py_file, i, line.strip()))
        except Exception:
            pass

if found_files:
    fail(f"Trouvé 'input_price_per_mtok' dans {len(found_files)} fichier(s) :")
    seen = set()
    for item in found_files:
        if isinstance(item, tuple):
            fpath, lineno, line = item
            print(f"  {RED}{fpath}:{lineno}{RESET}")
            print(f"    → {line}")
        else:
            if str(item) not in seen:
                print(f"  {RED}{item}{RESET}")
                seen.add(str(item))
    print(f"\n  {YELLOW}ACTION : Modifier/supprimer input_price_per_mtok dans ces fichiers{RESET}")
else:
    ok("Aucune occurrence de 'input_price_per_mtok' trouvée dans les chemins accessibles")
    info("L'erreur vient peut-être du package litellm lui-même ou d'un endpoint distant")

# ────────────────────────────────────────────────────
# 4. VÉRIFIER LA CONFIGURATION DEEPSEEK
# ────────────────────────────────────────────────────
header("4. CONFIG DEEPSEEK / LLM")

# Vérifier les variables d'environnement
deepseek_keys = [k for k in os.environ if "DEEPSEEK" in k.upper()]
openai_keys = [k for k in os.environ if "OPENAI" in k.upper()]
litellm_keys = [k for k in os.environ if "LITELLM" in k.upper()]

if deepseek_keys:
    ok(f"Variables DeepSeek : {deepseek_keys}")
else:
    warn("Aucune variable DEEPSEEK_* trouvée")

if openai_keys:
    ok(f"Variables OpenAI : {openai_keys}")
    
# Vérifier les fichiers .env
for env_file in cwd.rglob(".env"):
    try:
        content = env_file.read_text(encoding="utf-8", errors="ignore")
        if "input_price_per_mtok" in content:
            fail(f"'input_price_per_mtok' trouvé dans .env : {env_file}")
    except:
        pass

# ────────────────────────────────────────────────────
# 5. TEST DE COMPATIBILITÉ LITELLM + DEEPSEEK
# ────────────────────────────────────────────────────
header("5. TEST LITELLM → DEEPSEEK (sans input_price_per_mtok)")

try:
    from litellm import acompletion
    import inspect
    
    # Vérifier quels kwargs sont acceptés
    sig = inspect.signature(acompletion)
    accepted_kwargs = list(sig.parameters.keys())
    
    problematic = ["input_price_per_mtok", "output_price_per_mtok", 
                   "input_cost_per_token", "output_cost_per_token"]
    
    for kw in problematic:
        if kw in accepted_kwargs:
            fail(f"{kw} est dans la signature — sera passé à DeepSeek qui ne le supporte pas")
        else:
            ok(f"{kw} absent de la signature — OK")
            
except ImportError:
    warn("litellm pas importable, test sauté")

# ────────────────────────────────────────────────────
# 6. SOLUTION PROPOSÉE
# ────────────────────────────────────────────────────
header("6. SOLUTION")

print(f"""
{BOLD}Le problème :{RESET}
  LiteLLM v1.50+ ou un middleware DeerFlow tente de passer 
  'input_price_per_mtok' à AsyncCompletions.create(), mais 
  DeepSeek V3 ne reconnaît pas ce paramètre.

{BOLD}Pistes de correction (dans l'ordre) :{RESET}

  {CYAN}1. Downgrade LiteLLM{RESET} (si le middleware l'exige)
     pip install litellm==1.48.0

  {CYAN}2. Upgrade LiteLLM{RESET} (si bug corrigé en version récente)
     pip install --upgrade litellm

  {CYAN}3. Patcher le code DeerFlow{RESET} (si trouvé en étape 3)
     Supprimer/commenter 'input_price_per_mtok' dans le fichier fautif

  {CYAN}4. Désactiver le cost-tracking DeerFlow{RESET}
     Variable d'environnement : DEERFLOW_COST_TRACKING=false
     ou modifier le .env / config.yaml
""")

# ────────────────────────────────────────────────────
# RÉSUMÉ
# ────────────────────────────────────────────────────
header("RÉSUMÉ")
print(f"  Version litellm : {version if 'version' in dir() else 'N/A'}")
print(f"  Fichiers avec input_price_per_mtok : {len(found_files)}")
print(f"  Variables DeepSeek configurées : {len(deepseek_keys)}")
