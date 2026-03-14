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

    def run(self):
        """
        Override the default BaseBot.run() method.
        Since BaseBot strictly expects pywikibot.Page objects in some
        Pywikibot versions, we bypass its internal loop and handle our
        custom tuple generator manually.
        """
        if not self.generator:
            pywikibot.info("No generator found or mapping is empty. Exiting.")
            return

        pywikibot.info("Starting synchronization process...")
        
        for pair in self.generator:
            try:
                self.treat(pair)
            except KeyboardInterrupt:
                pywikibot.info("Process interrupted by the user.")
                break
            except Exception as e:
                # Catch any unexpected errors to prevent the bot from crashing completely
                pywikibot.error(f"Unexpected error while processing pair {pair}: {e}")

    def treat(self, pair):
        """
        Process a single pair of templates.
        
        @param pair: Tuple containing (source_raw_title, target_raw_title)
        @type pair: tuple
        """
        source_title, target_title = pair

        # Initialize Page objects in Template namespace (ns=10)
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
            
            # userPut handles API rate throttling automatically and safely
            self.userPut(
                target_page,
                target_page.text if target_page.exists() else "",
                source_content,
                summary=self.opt.summary,
                ignore_save_related_errors=True
            )

        except pywikibot.exceptions.Error as e:
            pywikibot.error(f"API Error processing {target_page.title()}: {e}")

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
