# Active Recon Tool v1.0

Herramienta de reconocimiento activo para bug bounty con 24 modulos de deteccion.

**SOLO para targets autorizados.** Incluye disclaimer legal obligatorio antes de cada escaneo.

## Requisitos

- Python 3.8+
- `requests`
- `dnspython`

## Instalacion

```bash
git clone https://github.com/Sebazzz88/tool-recon-active.git
cd tool-recon-active
pip install requests dnspython
```

## Uso basico

```bash
# Escaneo completo (todos los modulos)
python3 active-recon.py -t https://target.com

# Con rate limiting (10 req/seg)
python3 active-recon.py -t https://target.com --rate-limit 10

# Modulos especificos
python3 active-recon.py -t https://target.com -m portscan,sqli,xss

# Con proxy (Burp Suite)
python3 active-recon.py -t https://target.com --proxy http://127.0.0.1:8080

# Escaneo completo con rate limit y proxy
python3 active-recon.py -t https://target.com --rate-limit 10 --proxy http://127.0.0.1:8080

# Guardar reportes en carpeta especifica
python3 active-recon.py -t https://target.com -o /ruta/reportes

# Wordlist custom para directorios
python3 active-recon.py -t https://target.com -m dirbust --wordlist /ruta/wordlist.txt

# Escaneo de puertos especificos
python3 active-recon.py -t https://target.com -m portscan --ports 80,443,8080,8443

# Rango de puertos
python3 active-recon.py -t https://target.com -m portscan --ports 1-1000
```

## Modulos disponibles

| Modulo | Flag | Descripcion |
|--------|------|-------------|
| Port Scanner | `portscan` | Escaneo TCP connect |
| Service Detection | `services` | Banner grabbing |
| Directory Bruteforce | `dirbust` | Descubrimiento de directorios/archivos |
| Subdomain Bruteforce | `subbrust` | Enumeracion DNS de subdominios |
| DNS Zone Transfer | `zonetrans` | Test AXFR |
| VHost Discovery | `vhost` | Virtual hosts |
| Web Crawler | `crawl` | Spider con extraccion de forms, params, JS, emails |
| Parameter Discovery | `paramdisco` | Parametros ocultos |
| Tech Fingerprint | `techfp` | Deteccion de tecnologias |
| WAF Detection | `waf` | Fingerprinting de WAF |
| CMS Enumeration | `cmsenum` | WordPress, Joomla, Drupal |
| SSL/TLS Audit | `sslaudit` | Protocolos, ciphers, certificados |
| HTTP Methods | `httpmethods` | Metodos peligrosos (TRACE, PUT, DELETE) |
| CORS Testing | `cors` | Misconfiguraciones CORS |
| SQLi Probe | `sqli` | Deteccion SQL injection (error + blind) |
| XSS Probe | `xss` | Deteccion XSS reflejado |
| LFI Probe | `lfi` | Local File Inclusion |
| Open Redirect | `redirect` | Redireccionamientos abiertos |
| CRLF Injection | `crlf` | Inyeccion de headers |
| Host Header Injection | `hosthdr` | Manipulacion de Host header |
| Subdomain Takeover | `takeover` | Verificacion de takeover |
| Default Credentials | `defcreds` | Credenciales por defecto |
| API Discovery | `apidisco` | Endpoints REST y GraphQL |

## Opciones

```
-t, --target        URL del target (requerido)
-m, --modules       Modulos a ejecutar (default: all)
-o, --output        Directorio de reportes (default: .)
--threads           Hilos paralelos (default: 10)
--timeout           Timeout HTTP en segundos (default: 10)
--rate-limit        Max requests/segundo (default: 0 = sin limite)
--ports             top100 | rango (1-1000) | lista (80,443)
--wordlist          Wordlist custom para directorios
--sublist            Wordlist custom para subdominios
--extensions        Extensiones para dirbust (default: php,html,txt,bak,old,asp,aspx,jsp)
--crawl-depth       Profundidad de crawl (default: 3)
--crawl-pages       Max paginas a crawlear (default: 100)
--user-agent        User-Agent personalizado
--proxy             Proxy HTTP (ej: http://127.0.0.1:8080)
--cookies           Cookies (ej: 'session=abc; token=xyz')
--headers           Headers custom (separados por ;;)
--no-color          Sin colores
--skip-disclaimer   Saltar disclaimer (solo automation)
```

## Output

Genera dos archivos de reporte:
- `active_recon_<domain>_<timestamp>.txt` - Reporte legible
- `active_recon_<domain>_<timestamp>.json` - Reporte JSON para procesamiento

## Ejemplos de combinaciones utiles

```bash
# Recon rapido: puertos + tecnologias + WAF
python3 active-recon.py -t https://target.com -m portscan,techfp,waf

# Busqueda de vulns web
python3 active-recon.py -t https://target.com -m sqli,xss,lfi,redirect,crlf

# Enumeracion completa
python3 active-recon.py -t https://target.com -m subbrust,dirbust,apidisco,cmsenum

# Escaneo con autenticacion (cookies de sesion)
python3 active-recon.py -t https://target.com --cookies "session=abc123; auth=xyz"
```
