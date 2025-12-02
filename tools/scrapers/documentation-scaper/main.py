#!/usr/bin/env python3
"""
Documentation Scraper - Rekursiver Web-Scraper für Dokumentationsseiten

Dieser Scraper durchsucht Dokumentationsseiten rekursiv, extrahiert den Inhalt
und konvertiert ihn in sauberes Markdown für die Verwendung mit KI-Modellen.

Unterstützte Plattformen:
- Docker Docs
- Broadcom TechDocs
- IT Glue (Kaseya)
- n8n Docs
- ReadTheDocs
- GitBook
- MkDocs
- Docusaurus
- VuePress
- Sphinx
- Confluence
- Notion
- Generic documentation sites
"""

import argparse
import hashlib
import json
import logging
import os
import re
import time
import urllib3
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import MarkdownConverter

# SSL-Warnungen unterdrücken wenn gewünscht
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Konfiguration für den Scraper."""
    base_url: str
    output_dir: str = "output"
    max_depth: int = 10
    delay: float = 1.0  # Sekunden zwischen Requests
    timeout: int = 30
    user_agent: str = "DocsScraper/1.0 (Educational Purpose)"
    include_patterns: list = field(default_factory=list)
    exclude_patterns: list = field(default_factory=list)
    single_file: bool = False  # Alle Inhalte in einer Datei
    respect_robots: bool = True
    max_pages: int = 1000  # Maximale Anzahl der Seiten
    verify_ssl: bool = True  # SSL-Zertifikate verifizieren


class CustomMarkdownConverter(MarkdownConverter):
    """Angepasster Markdown-Konverter für bessere Ausgabe."""
    
    def convert_pre(self, el, text, parent_tags=None):
        """Konvertiert <pre> Tags zu Markdown Code-Blöcken."""
        code = el.find('code')
        if code:
            # Versuche die Programmiersprache zu erkennen
            classes = code.get('class', [])
            language = ''
            for cls in classes:
                if cls.startswith('language-') or cls.startswith('lang-'):
                    language = cls.split('-', 1)[1]
                    break
                elif cls in ['python', 'javascript', 'typescript', 'bash', 'shell', 
                           'json', 'yaml', 'xml', 'html', 'css', 'sql', 'go', 
                           'rust', 'java', 'csharp', 'cpp', 'ruby', 'php']:
                    language = cls
                    break
            
            code_text = code.get_text()
            return f'\n```{language}\n{code_text}\n```\n'
        
        return f'\n```\n{text}\n```\n'
    
    def convert_code(self, el, text, parent_tags=None):
        """Konvertiert <code> Tags."""
        # Wenn es innerhalb von <pre> ist, behandelt convert_pre es
        if el.parent and el.parent.name == 'pre':
            return text
        return f'`{text}`'
    
    def convert_table(self, el, text, parent_tags=None):
        """Konvertiert <table> Tags zu Markdown Tabellen."""
        rows = el.find_all('tr')
        if not rows:
            return text
        
        markdown_rows = []
        header_processed = False
        
        for row in rows:
            cells = row.find_all(['th', 'td'])
            if not cells:
                continue
                
            cell_texts = []
            for cell in cells:
                cell_text = cell.get_text(strip=True).replace('|', '\\|')
                cell_text = ' '.join(cell_text.split())  # Normalisiere Whitespace
                cell_texts.append(cell_text)
            
            markdown_rows.append('| ' + ' | '.join(cell_texts) + ' |')
            
            # Header-Separator nach der ersten Zeile (wenn es th-Elemente gibt)
            if not header_processed and row.find('th'):
                separator = '| ' + ' | '.join(['---'] * len(cells)) + ' |'
                markdown_rows.append(separator)
                header_processed = True
        
        # Wenn keine Header gefunden wurden, füge Separator nach erster Zeile ein
        if not header_processed and len(markdown_rows) > 0:
            num_cols = markdown_rows[0].count('|') - 1
            separator = '| ' + ' | '.join(['---'] * num_cols) + ' |'
            markdown_rows.insert(1, separator)
        
        return '\n\n' + '\n'.join(markdown_rows) + '\n\n'


def md(soup, **options):
    """Konvertiert BeautifulSoup-Objekt zu Markdown."""
    return CustomMarkdownConverter(**options).convert_soup(soup)


class DocumentationScraper:
    """Hauptklasse für das Scrapen von Dokumentationsseiten."""
    
    # Elemente die entfernt werden sollen
    REMOVE_SELECTORS = [
        # Navigation
        'nav', 'header', 'footer', 'aside',
        '.nav', '.navbar', '.navigation', '.sidebar', '.sidenav',
        '.menu', '.toc', '.table-of-contents',
        '#nav', '#navbar', '#navigation', '#sidebar', '#sidenav',
        '#menu', '#toc', '#table-of-contents',
        
        # Header/Footer
        '.header', '.footer', '.site-header', '.site-footer',
        '.page-header', '.page-footer',
        '#header', '#footer', '#site-header', '#site-footer',
        
        # Werbung und Cookies
        '.ad', '.ads', '.advertisement', '.banner',
        '.cookie', '.cookie-banner', '.cookie-consent',
        '.onetrust', '#onetrust',
        '.gdpr', '.privacy-banner',
        
        # Suche
        '.search', '.search-box', '.search-container',
        '#search', '#search-box', '#search-container',
        
        # Feedback/Kommentare
        '.feedback', '.comments', '.rating',
        '#feedback', '#comments', '#rating',
        
        # Social Media
        '.social', '.share', '.social-links',
        '#social', '#share', '#social-links',
        
        # Breadcrumbs
        '.breadcrumb', '.breadcrumbs',
        '#breadcrumb', '#breadcrumbs',
        
        # Edit/GitHub Links
        '.edit-link', '.edit-this-page', '.github-link',
        '.page-actions', '.page-edit',
        
        # Pagination (am Ende der Seite)
        '.pagination', '.pager', '.prev-next',
        '#pagination', '#pager',
        
        # Scripts und Styles
        'script', 'style', 'noscript', 'iframe',
        
        # Hidden elements
        '[hidden]', '.hidden', '.d-none', '.invisible',
        '[aria-hidden="true"]',
        
        # Modal/Popup
        '.modal', '.popup', '.overlay',
        '#modal', '#popup', '#overlay',
        
        # Skip links
        '.skip-link', '.skip-to-content',
        
        # Platform-spezifisch
        # Docker
        '.topbar-button', '#buttons', '.open-kapa-widget',
        
        # Broadcom
        '.off-canvas', '.title-bar', '.central-account-wrapper',
        
        # n8n
        '.n8n-kapa-button', '.md-header', '.md-footer',
        
        # IT Glue / MadCap
        '.off-canvas-drilldown', '.title-bar-container',
    ]
    
    # CSS-Klassen die auf Hauptinhalt hinweisen
    CONTENT_SELECTORS = [
        # Allgemein
        'main', 'article', '[role="main"]',
        '.content', '.main-content', '.page-content', '.article-content',
        '.documentation', '.doc-content', '.docs-content',
        '#content', '#main-content', '#page-content', '#article-content',
        '#documentation', '#doc-content', '#docs-content',
        
        # MkDocs
        '.md-content', '.md-main',
        
        # Docusaurus
        '.docMainContainer', '.docItemContainer',
        
        # ReadTheDocs
        '.rst-content', '.document',
        
        # GitBook
        '.page-inner', '.page-wrapper',
        
        # Sphinx
        '.body', '.bodywrapper',
        
        # VuePress
        '.theme-default-content',
        
        # IT Glue / MadCap
        '[data-mc-content-body="True"]', '.body-container', '.topic-hero',
        '.home-container', '.home-section',
        
        # Docker
        '.body-container', '.flex-col',
        
        # Broadcom
        '.root', '.responsivegrid',
    ]
    
    # Link-Selektoren für Navigation
    LINK_SELECTORS = [
        # Sidebar/Navigation Links
        'nav a', '.sidebar a', '.sidenav a', '.navigation a',
        '.toc a', '.table-of-contents a', '.menu a',
        
        # MkDocs
        '.md-nav a', '.md-sidebar a',
        
        # Docusaurus
        '.menu__link', '.navbar__link',
        
        # ReadTheDocs
        '.toctree-wrapper a', '.wy-menu a',
        
        # GitBook
        '.summary a', '.book-summary a',
        
        # IT Glue / MadCap
        '.off-canvas-accordion a', '.MCXref',
        '.sidenav-container a', '.home-tiles a',
        
        # Docker
        '.section-card a', 'a.link',
        
        # Content links
        'article a', '.content a', 'main a',
        '[role="main"] a', '.documentation a',
    ]
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'de,en;q=0.9',
        })
        
        self.visited_urls: set = set()
        self.scraped_content: list = []
        self.url_to_title: dict = {}
        
        # Parse base URL
        parsed = urlparse(config.base_url)
        self.base_domain = parsed.netloc
        self.base_scheme = parsed.scheme
        self.base_path = parsed.path.rstrip('/')
        
        # Output-Verzeichnis erstellen
        self.output_path = Path(config.output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def is_valid_url(self, url: str) -> bool:
        """Prüft ob eine URL gescraped werden soll."""
        if not url:
            return False
        
        parsed = urlparse(url)
        
        # Muss http/https sein
        if parsed.scheme not in ('http', 'https', ''):
            return False
        
        # Muss zur gleichen Domain gehören (oder relative URL sein)
        if parsed.netloc and parsed.netloc != self.base_domain:
            return False
        
        # Keine Anchors oder Query-Strings für Duplikat-Check
        path = parsed.path
        
        # Dateiendungen ausschließen
        excluded_extensions = [
            '.pdf', '.zip', '.tar', '.gz', '.exe', '.dmg', '.pkg',
            '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp',
            '.mp4', '.mp3', '.avi', '.mov', '.wav',
            '.css', '.js', '.json', '.xml', '.woff', '.woff2', '.ttf', '.eot',
        ]
        if any(path.lower().endswith(ext) for ext in excluded_extensions):
            return False
        
        # Include-Patterns prüfen
        if self.config.include_patterns:
            if not any(re.search(pattern, url) for pattern in self.config.include_patterns):
                return False
        
        # Exclude-Patterns prüfen
        if self.config.exclude_patterns:
            if any(re.search(pattern, url) for pattern in self.config.exclude_patterns):
                return False
        
        return True
    
    def normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalisiert eine URL."""
        if not url:
            return None
        
        # JavaScript-Links ignorieren
        if url.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            return None
        
        # Relative URLs auflösen
        absolute_url = urljoin(base_url, url)
        
        # URL parsen und normalisieren
        parsed = urlparse(absolute_url)
        
        # Ohne Fragment und Query (für Deduplizierung)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # Trailing slash normalisieren
        if normalized.endswith('/') and len(parsed.path) > 1:
            normalized = normalized.rstrip('/')
        
        return normalized
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Lädt eine Seite herunter."""
        try:
            response = self.session.get(
                url,
                timeout=self.config.timeout,
                allow_redirects=True,
                verify=self.config.verify_ssl
            )
            response.raise_for_status()
            
            # Prüfe Content-Type
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                logger.debug(f"Skipping non-HTML content: {url}")
                return None
            
            return response.text
            
        except requests.RequestException as e:
            logger.warning(f"Fehler beim Laden von {url}: {e}")
            return None
    
    def extract_content(self, soup: BeautifulSoup, url: str) -> tuple[str, str]:
        """Extrahiert den Hauptinhalt einer Seite."""
        # Titel extrahieren
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # H1 als Fallback
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        
        # Elemente entfernen die nicht zum Inhalt gehören
        for selector in self.REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
        
        # Hauptinhalt finden
        content_element = None
        for selector in self.CONTENT_SELECTORS:
            content_element = soup.select_one(selector)
            if content_element:
                # Prüfe ob genug Inhalt vorhanden ist
                text = content_element.get_text(strip=True)
                if len(text) > 100:  # Mindestens 100 Zeichen
                    break
                content_element = None
        
        # Fallback: body
        if not content_element:
            content_element = soup.find('body')
        
        if not content_element:
            return title, ""
        
        # Zu Markdown konvertieren
        markdown = md(content_element, heading_style="ATX", bullets="-")
        
        # Markdown aufräumen
        markdown = self.clean_markdown(markdown)
        
        return title, markdown
    
    def clean_markdown(self, markdown: str) -> str:
        """Räumt das generierte Markdown auf."""
        # Mehrfache Leerzeilen reduzieren
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Leerzeichen am Ende von Zeilen entfernen
        markdown = re.sub(r' +$', '', markdown, flags=re.MULTILINE)
        
        # Leere Links entfernen
        markdown = re.sub(r'\[]\([^)]*\)', '', markdown)
        
        # Kaputte Markdown-Links reparieren
        markdown = re.sub(r'\[([^\]]+)\]\(\s*\)', r'\1', markdown)
        
        # Mehrfache Leerzeichen in einer Zeile reduzieren
        markdown = re.sub(r'  +', ' ', markdown)
        
        # Führende/nachfolgende Leerzeichen entfernen
        markdown = markdown.strip()
        
        return markdown
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> set:
        """Extrahiert alle relevanten Links aus einer Seite."""
        links = set()
        
        # Links aus verschiedenen Bereichen sammeln
        for selector in self.LINK_SELECTORS:
            for link in soup.select(selector):
                href = link.get('href')
                if href:
                    normalized = self.normalize_url(href, base_url)
                    if normalized and self.is_valid_url(normalized):
                        links.add(normalized)
        
        # Auch alle <a> Tags durchsuchen als Fallback
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            normalized = self.normalize_url(href, base_url)
            if normalized and self.is_valid_url(normalized):
                links.add(normalized)
        
        return links
    
    def scrape_page(self, url: str, depth: int = 0) -> set:
        """Scraped eine einzelne Seite und gibt gefundene Links zurück."""
        if url in self.visited_urls:
            return set()
        
        if len(self.visited_urls) >= self.config.max_pages:
            logger.warning(f"Maximale Seitenanzahl ({self.config.max_pages}) erreicht")
            return set()
        
        if depth > self.config.max_depth:
            logger.debug(f"Maximale Tiefe erreicht für {url}")
            return set()
        
        self.visited_urls.add(url)
        
        logger.info(f"[{len(self.visited_urls)}] Scraping: {url} (Tiefe: {depth})")
        
        # Seite laden
        html = self.fetch_page(url)
        if not html:
            return set()
        
        # HTML parsen
        soup = BeautifulSoup(html, 'html.parser')
        
        # Links extrahieren (vor dem Entfernen von Elementen)
        links = self.extract_links(soup, url)
        
        # Inhalt extrahieren
        title, content = self.extract_content(soup, url)
        
        if content and len(content) > 50:  # Mindestens 50 Zeichen
            self.scraped_content.append({
                'url': url,
                'title': title,
                'content': content,
                'depth': depth,
                'timestamp': datetime.now().isoformat()
            })
            self.url_to_title[url] = title
            logger.info(f"  → Extrahiert: {title[:50]}... ({len(content)} Zeichen)")
        else:
            logger.debug(f"  → Kein Inhalt gefunden oder zu kurz")
        
        # Delay zwischen Requests
        time.sleep(self.config.delay)
        
        return links
    
    def scrape(self):
        """Startet den rekursiven Scraping-Prozess."""
        logger.info(f"Starte Scraping von: {self.config.base_url}")
        logger.info(f"Output-Verzeichnis: {self.output_path}")
        
        # Startseite scrapen
        to_visit = {self.config.base_url}
        current_depth = 0
        
        while to_visit and current_depth <= self.config.max_depth:
            next_level = set()
            
            for url in to_visit:
                if len(self.visited_urls) >= self.config.max_pages:
                    break
                    
                new_links = self.scrape_page(url, current_depth)
                # Nur neue Links zur nächsten Ebene hinzufügen
                next_level.update(new_links - self.visited_urls)
            
            to_visit = next_level
            current_depth += 1
            
            logger.info(f"Tiefe {current_depth}: {len(next_level)} neue Links gefunden")
        
        logger.info(f"Scraping abgeschlossen: {len(self.scraped_content)} Seiten extrahiert")
    
    def save_results(self):
        """Speichert die Ergebnisse."""
        if not self.scraped_content:
            logger.warning("Keine Inhalte zum Speichern")
            return
        
        # Domain-Name für Dateinamen
        domain_name = self.base_domain.replace('.', '-')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if self.config.single_file:
            # Alles in eine Datei
            self._save_single_file(domain_name, timestamp)
        else:
            # Separate Dateien
            self._save_multiple_files(domain_name)
        
        # Metadaten speichern
        self._save_metadata(domain_name, timestamp)
    
    def _save_single_file(self, domain_name: str, timestamp: str):
        """Speichert alle Inhalte in einer Datei."""
        output_file = self.output_path / f"{domain_name}_{timestamp}.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"# Documentation: {self.base_domain}\n\n")
            f.write(f"Gescraped am: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Basis-URL: {self.config.base_url}\n")
            f.write(f"Anzahl Seiten: {len(self.scraped_content)}\n\n")
            f.write("---\n\n")
            
            # Inhaltsverzeichnis
            f.write("## Inhaltsverzeichnis\n\n")
            for i, page in enumerate(self.scraped_content, 1):
                title = page['title'] or f"Seite {i}"
                anchor = self._make_anchor(title)
                f.write(f"{i}. [{title}](#{anchor})\n")
            f.write("\n---\n\n")
            
            # Inhalte
            for page in self.scraped_content:
                title = page['title'] or "Unbekannter Titel"
                f.write(f"## {title}\n\n")
                f.write(f"**URL:** {page['url']}\n\n")
                f.write(page['content'])
                f.write("\n\n---\n\n")
        
        logger.info(f"Gespeichert: {output_file}")
    
    def _save_multiple_files(self, domain_name: str):
        """Speichert jede Seite in einer separaten Datei."""
        docs_dir = self.output_path / domain_name
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Index-Datei erstellen
        index_file = docs_dir / "00_INDEX.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(f"# Documentation Index: {self.base_domain}\n\n")
            f.write(f"Gescraped am: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Basis-URL: {self.config.base_url}\n")
            f.write(f"Anzahl Seiten: {len(self.scraped_content)}\n\n")
            f.write("---\n\n")
            f.write("## Seiten\n\n")
        
        for i, page in enumerate(self.scraped_content, 1):
            # Dateiname aus URL generieren
            filename = self._url_to_filename(page['url'], i)
            file_path = docs_dir / filename
            
            title = page['title'] or "Unbekannter Titel"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n")
                f.write(f"**URL:** {page['url']}\n\n")
                f.write("---\n\n")
                f.write(page['content'])
            
            # Zum Index hinzufügen
            with open(index_file, 'a', encoding='utf-8') as f:
                f.write(f"- [{title}]({filename})\n")
        
        logger.info(f"Gespeichert: {docs_dir} ({len(self.scraped_content)} Dateien)")
    
    def _save_metadata(self, domain_name: str, timestamp: str):
        """Speichert Metadaten als JSON."""
        metadata = {
            'base_url': self.config.base_url,
            'domain': self.base_domain,
            'scraped_at': datetime.now().isoformat(),
            'total_pages': len(self.scraped_content),
            'max_depth': self.config.max_depth,
            'pages': [
                {
                    'url': page['url'],
                    'title': page['title'],
                    'depth': page['depth'],
                    'content_length': len(page['content'])
                }
                for page in self.scraped_content
            ]
        }
        
        metadata_file = self.output_path / f"{domain_name}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Metadaten gespeichert: {metadata_file}")
    
    def _url_to_filename(self, url: str, index: int) -> str:
        """Generiert einen Dateinamen aus einer URL."""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if not path:
            path = "index"
        
        # Pfad zu Dateiname konvertieren
        filename = path.replace('/', '_').replace('\\', '_')
        
        # Nur erlaubte Zeichen
        filename = re.sub(r'[^a-zA-Z0-9_-]', '_', filename)
        
        # Länge begrenzen
        if len(filename) > 100:
            filename = filename[:100]
        
        # Index hinzufügen für eindeutige Sortierung
        filename = f"{index:04d}_{filename}.md"
        
        return filename
    
    def _make_anchor(self, title: str) -> str:
        """Erstellt einen Markdown-Anchor aus einem Titel."""
        anchor = title.lower()
        anchor = re.sub(r'[^a-z0-9\s-]', '', anchor)
        anchor = re.sub(r'\s+', '-', anchor)
        return anchor


def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(
        description='Dokumentations-Scraper - Scraped Dokumentationsseiten zu Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Docker Docs scrapen
  python main.py https://docs.docker.com/ -o docker_docs --depth 3
  
  # IT Glue Docs in einer Datei
  python main.py https://help.itglue.com/ -o itglue --single-file
  
  # Mit Include-Pattern (nur bestimmte Pfade)
  python main.py https://docs.n8n.io/ -o n8n --include "/nodes/" --include "/integrations/"
  
  # Mit Exclude-Pattern (bestimmte Pfade ausschließen)  
  python main.py https://docs.example.com/ -o example --exclude "/api/" --exclude "/changelog/"
        """
    )
    
    parser.add_argument(
        'url',
        help='Basis-URL der Dokumentation zum Scrapen'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='Output-Verzeichnis (Standard: output)'
    )
    
    parser.add_argument(
        '-d', '--depth',
        type=int,
        default=5,
        help='Maximale Tiefe für rekursives Scraping (Standard: 5)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Verzögerung zwischen Requests in Sekunden (Standard: 1.0)'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=500,
        help='Maximale Anzahl der zu scrapenden Seiten (Standard: 500)'
    )
    
    parser.add_argument(
        '--single-file',
        action='store_true',
        help='Alle Inhalte in einer einzelnen Markdown-Datei speichern'
    )
    
    parser.add_argument(
        '--include',
        action='append',
        default=[],
        help='URL-Pattern die eingeschlossen werden sollen (Regex)'
    )
    
    parser.add_argument(
        '--exclude',
        action='append',
        default=[],
        help='URL-Pattern die ausgeschlossen werden sollen (Regex)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Ausführliche Ausgabe'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Nur Fehler ausgeben'
    )
    
    parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='SSL-Zertifikate nicht verifizieren (für selbstsignierte Zertifikate)'
    )
    
    args = parser.parse_args()
    
    # Logging-Level setzen
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # Konfiguration erstellen
    config = ScraperConfig(
        base_url=args.url,
        output_dir=args.output,
        max_depth=args.depth,
        delay=args.delay,
        max_pages=args.max_pages,
        single_file=args.single_file,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        verify_ssl=not args.no_verify_ssl,
    )
    
    # Scraper starten
    try:
        scraper = DocumentationScraper(config)
        scraper.scrape()
        scraper.save_results()
        
        logger.info("Fertig!")
        
    except KeyboardInterrupt:
        logger.info("Abgebrochen durch Benutzer")
    except Exception as e:
        logger.error(f"Fehler: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
