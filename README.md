# Active Recon Tool v2.0

Herramienta avanzada de reconocimiento activo para bug bounty con **44 modulos** de deteccion.

**SOLO para targets autorizados.** Incluye disclaimer legal obligatorio con consecuencias legales detalladas.

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

## Uso

### Simple (recomendado)

Solo necesitas la URL. El script te pedira el modo de velocidad interactivamente:

```bash
python3 active-recon.py https://target.com
```

### Con modo predefinido

```bash
python3 active-recon.py https://target.com --mode slow
python3 active-recon.py https://target.com --mode medium
python3 active-recon.py https://target.com --mode high
```

### Modulos especificos

```bash
python3 active-recon.py https://target.com -m sqli,xss,lfi,ssrf
```

### Con proxy (Burp Suite)

```bash
python3 active-recon.py https://target.com --proxy http://127.0.0.1:8080
```

## Modos de velocidad

Los 3 modos ejecutan EXACTAMENTE los mismos modulos con la misma efectividad. Solo cambia la velocidad:

| Modo | Delay | Hilos | User-Agent | Orden | Deteccion |
|------|-------|-------|------------|-------|-----------|
| **SLOW** | 2-5s | 2 | Rotativo | Aleatorio | Casi indetectable |
| **MEDIUM** | 0.3-1s | 5 | Rotativo | Aleatorio | Moderada |
| **HIGH** | Sin delay | 15 | Fijo | Secuencial | Alta |

## Modulos (44)

### Reconocimiento de red
| Modulo | Flag | Descripcion |
|--------|------|-------------|
| Port Scanner | `portscan` | Escaneo TCP connect (100+ puertos) |
| Service Detection | `services` | Banner grabbing con SSL |
| DNS Zone Transfer | `zonetrans` | Test AXFR |
| DNS Recon | `dnsrecon` | Records A/AAAA/MX/TXT/NS/SOA/CNAME/SRV/CAA + SPF/DMARC/DKIM |

### Descubrimiento web
| Modulo | Flag | Descripcion |
|--------|------|-------------|
| Directory Bruteforce | `dirbust` | 200+ rutas con extensiones |
| Subdomain Bruteforce | `subbrust` | 100+ subdominios |
| VHost Discovery | `vhost` | Virtual hosts |
| Web Crawler | `crawl` | Spider: forms, params, JS, emails |
| Parameter Discovery | `paramdisco` | 60+ parametros comunes |
| API Discovery | `apidisco` | 50+ endpoints REST/GraphQL |
| Sensitive Files | `sensitive` | Archivos expuestos (.env, .git, configs) |
| Backup Discovery | `backup` | Archivos de backup (.sql, .zip, .tar.gz) |

### Fingerprinting
| Modulo | Flag | Descripcion |
|--------|------|-------------|
| Tech Fingerprint | `techfp` | 30+ tecnologias/frameworks |
| WAF Detection | `waf` | 14 WAFs conocidos |
| CMS Enumeration | `cmsenum` | WordPress, Joomla, Drupal |

### Seguridad de infraestructura
| Modulo | Flag | Descripcion |
|--------|------|-------------|
| SSL/TLS Audit | `sslaudit` | Protocolos, ciphers, certificados, SANs |
| HTTP Methods | `httpmethods` | Metodos peligrosos (TRACE, PUT, DELETE) |
| Security Headers | `secheaders` | 11 headers de seguridad + info disclosure |
| Cookie Security | `cookies` | Flags Secure/HttpOnly/SameSite |
| CSP Analysis | `csp` | Directivas peligrosas, missing directives |
| Clickjacking | `clickjack` | X-Frame-Options + frame-ancestors |
| CORS Testing | `cors` | Origin reflection, wildcard, null |

### Deteccion de vulnerabilidades
| Modulo | Flag | Descripcion |
|--------|------|-------------|
| CSRF Detection | `csrf` | Formularios sin tokens CSRF |
| SQL Injection | `sqli` | Error-based + blind boolean + time-based + POST |
| XSS Probe | `xss` | Reflected + DOM sinks + POST |
| LFI Probe | `lfi` | Path traversal + PHP wrappers + log poisoning |
| RFI Probe | `rfi` | Remote File Inclusion |
| Open Redirect | `redirect` | 13 tecnicas de bypass |
| CRLF Injection | `crlf` | Header injection |
| Host Header Injection | `hosthdr` | X-Forwarded-Host, X-Original-URL |
| SSRF Detection | `ssrf` | AWS/GCP/Azure metadata + internal services |
| SSTI Detection | `ssti` | Jinja2, Twig, Freemarker, ERB, EL |
| Command Injection | `cmdi` | Time-based + output-based |
| XXE Detection | `xxe` | XML External Entity |
| HTTP Param Pollution | `hpp` | Parametros duplicados |

### Modulos avanzados
| Modulo | Flag | Descripcion |
|--------|------|-------------|
| Subdomain Takeover | `takeover` | 15 providers (GitHub, Heroku, S3, etc.) |
| Default Credentials | `defcreds` | 30+ pares user/pass en login panels |
| JWT Analysis | `jwt` | Algoritmo none, secretos debiles, datos sensibles |
| GraphQL Testing | `graphql` | Introspection, batching, SQLi |
| WebSocket Testing | `websocket` | Endpoints + validacion de Origin |
| Rate Limit Testing | `ratelimit` | Login brute-force + API rate limiting |
| Info Disclosure | `infodiscl` | Stack traces, debug info, paths |
| Email Header Injection | `emailinj` | Inyeccion Bcc/Cc en formularios |
| Cloud Metadata | `cloudmeta` | SSRF a metadata AWS/GCP/Azure/DO/Oracle |

## Opciones

```
target                URL del target (argumento posicional)
-t, --target-flag     URL del target (alternativa con flag)
--mode                Modo: slow | medium | high
-m, --modules         Modulos a ejecutar (default: todos)
-o, --output          Directorio de reportes (default: .)
--threads             Override hilos
--timeout             Timeout HTTP (default: 10)
--ports               top100 | rango (1-1000) | lista (80,443)
--wordlist            Wordlist custom para directorios
--sublist             Wordlist custom para subdominios
--extensions          Extensiones para dirbust
--crawl-depth         Profundidad de crawl (default: 3)
--crawl-pages         Max paginas (default: 100)
--user-agent          User-Agent custom
--proxy               Proxy HTTP (ej: http://127.0.0.1:8080)
--cookies             Cookies (ej: 'session=abc; token=xyz')
--headers             Headers custom (separados por ;;)
--no-color            Sin colores
--skip-disclaimer     Saltar disclaimer (solo automation)
```

## Output

Genera dos reportes:
- `active_recon_<domain>_<timestamp>.txt` - Reporte legible con hallazgos por severidad
- `active_recon_<domain>_<timestamp>.json` - JSON para procesamiento automatizado

## Ejemplos

```bash
# Escaneo completo stealth
python3 active-recon.py https://target.com --mode slow

# Solo vulnerabilidades web
python3 active-recon.py https://target.com -m sqli,xss,lfi,ssrf,ssti,cmdi

# Reconocimiento de superficie
python3 active-recon.py https://target.com -m portscan,services,subbrust,dirbust,techfp

# Con Burp Suite y cookies de sesion
python3 active-recon.py https://target.com --proxy http://127.0.0.1:8080 --cookies "session=abc123"

# Modo agresivo con puertos custom
python3 active-recon.py https://target.com --mode high --ports 1-1000
```
