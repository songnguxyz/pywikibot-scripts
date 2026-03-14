#!/usr/bin/python3
"""
Bot to synchronize templates from a source wiki to a target wiki
based on a mapping definition page.
"""

import pywikibot
from pywikibot import bot
from pywikibot.exceptions import Error

# Configuration constants
MAPPING_PAGE_TITLE = "MediaWiki:SyncTemplateMapping"
FAMILY_NAME = "mottrambangai"
SOURCE_LANG = "en"
TARGET_LANG = "vi"

class TemplateSyncBot(bot.BaseBot):
    """
    Bot to sync template content from source site to target site.
    """
    
    # CRITICAL FIX: Tell BaseBot we are processing tuples, not Page objects
    treat_page_type = tuple

    def __init__(self, generator, source_site, target_site, **kwargs):
        """Constructor."""
        self.available_options.update({
            'always': False,
            'summary': 'Bot: Synchronizing template content from English Wiki',
        })
        super().__init__(**kwargs)
        self.generator = generator
        self.source_site = source_site
        self.target_site = target_site

    def treat(self, pair):
        """
        Process a single pair of templates.
        
        @param pair: Tuple containing (source_raw_title, target_raw_title)
        @type pair: tuple
        """
        source_title, target_title = pair

        source_page = pywikibot.Page(self.source_site, source_title, ns=10)
        target_page = pywikibot.Page(self.target_site, target_title, ns=10)

        if not source_page.exists():
            pywikibot.warning(f"Source template does not exist: {source_page.title()}")
            return

        pywikibot.info(f"Processing: {source_page.title()} -> {target_page.title()}")

        try:
            source_content = source_page.text
            
            # Check if target exists and is identical
            if target_page.exists() and target_page.text == source_content:
                pywikibot.info(f"No changes needed for {target_page.title()}")
                return
            
            # userPut automatically handles diff display, confirmations, and rate throttling
            self.userPut(
                target_page,
                target_page.text if target_page.exists() else "",
                source_content,
                summary=self.opt.summary,
                ignore_save_related_errors=True
            )

        except Error as e:
            pywikibot.error(f"Error processing {target_page.title()}: {e}")

def load_mappings(site, mapping_page_title):
    """
    Parses the mapping page and yields tuples of (en_title, vi_title).
    """
    page = pywikibot.Page(site, mapping_page_title)
    
    if not page.exists():
        pywikibot.error(f"Mapping page not found: {mapping_page_title}")
        return

    pywikibot.info(f"Reading mappings from {mapping_page_title}...")
    
    for line in page.text.splitlines():
        if "|" in line:
            parts = line.split("|")
            src_raw = parts[0].strip().replace("Template:", "").replace("Bản mẫu:", "")
            tgt_raw = parts[1].strip().replace("Template:", "").replace("Bản mẫu:", "")

            if src_raw and tgt_raw:
                yield (src_raw, tgt_raw)

def main(*args):
    """Main execution function."""
    local_args = pywikibot.handle_args(args)
    options = {}

    for arg in local_args:
        if arg == '-always':
            options['always'] = True
        elif arg.startswith('-summary:'):
            options['summary'] = arg[len('-summary:'):]

    try:
        source_site = pywikibot.Site(SOURCE_LANG, FAMILY_NAME)
        target_site = pywikibot.Site(TARGET_LANG, FAMILY_NAME)
        
        target_site.login()
    except Error as e:
        pywikibot.error(f"Could not initialize sites: {e}")
        return

    mapping_generator = load_mappings(target_site, MAPPING_PAGE_TITLE)

    bot_instance = TemplateSyncBot(
        generator=mapping_generator,
        source_site=source_site,
        target_site=target_site,
        **options
    )
    
    bot_instance.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pywikibot.info("Script terminated by user.")
