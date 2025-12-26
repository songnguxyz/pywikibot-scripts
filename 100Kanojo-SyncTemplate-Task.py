#!/usr/bin/python3
"""
This script synchronizes templates from a source wiki (en) to a target wiki (vi)
based on a mapping definition page.

Mapping Page Format (MediaWiki:SyncTemplateMapping):
    English Template Name | Vietnamese Template Name
    Infobox Character     | Thông tin nhân vật

Usage:
    python3 template_sync_bot.py [-always] [-simulate]
"""

import pywikibot
from pywikibot import bot

# Configuration constants
MAPPING_PAGE_TITLE = "MediaWiki:SyncTemplateMapping"
FAMILY_NAME = "mottrambangai" # Ensure this family is defined in your user-config.py
SOURCE_LANG = "en"
TARGET_LANG = "vi"

class TemplateSyncBot(bot.BaseBot):
    """
    Bot to sync template content from source site to target site.
    """

    def __init__(self, generator, source_site, target_site, **kwargs):
        """
        Constructor.

        Args:
            generator: Iterator yielding tuples of (source_title, target_title).
            source_site: The Pywikibot Site object for the source (en).
            target_site: The Pywikibot Site object for the target (vi).
        """
        # Set default options
        self.available_options.update({
            'always': False,  # If True, accepts all changes without prompting
            'summary': 'Bot: Synchronizing template content from English Wiki',
        })
        
        super().__init__(**kwargs)
        self.generator = generator
        self.source_site = source_site
        self.target_site = target_site

    def treat(self, pair):
        """
        Process a single pair of templates.
        """
        source_title, target_title = pair

        # Initialize Page objects in Template namespace (ns=10)
        source_page = pywikibot.Page(self.source_site, source_title, ns=10)
        target_page = pywikibot.Page(self.target_site, target_title, ns=10)

        # 1. Check if source exists
        if not source_page.exists():
            pywikibot.warning(f"Source template does not exist: {source_page.title(as_link=True)}")
            return

        pywikibot.info(f"Processing: {source_page.title()} -> {target_page.title()}")

        try:
            # 2. Get content
            source_content = source_page.text
            
            # 3. Check if target exists and compare content
            if target_page.exists():
                if target_page.text == source_content:
                    pywikibot.info(f"No changes needed for {target_page.title()}")
                    return
            
            # 4. Save changes using userPut (handles diff display and confirmation)
            self.userPut(
                target_page,
                target_page.text,
                source_content,
                summary=self.opt.summary,
                ignore_save_related_errors=True
            )

        except pywikibot.exceptions.Error as e:
            pywikibot.error(f"Error processing {target_page.title()}: {e}")

def load_mappings(site, mapping_page_title):
    """
    Parses the mapping page and yields tuples of (en_title, vi_title).
    
    Args:
        site: The site where the mapping page is located.
        mapping_page_title: Title of the mapping page.
        
    Yields:
        tuple: (source_template_name, target_template_name)
    """
    page = pywikibot.Page(site, mapping_page_title)
    
    if not page.exists():
        pywikibot.error(f"Mapping page not found: {mapping_page_title}")
        return

    pywikibot.info(f"Reading mappings from {mapping_page_title}...")
    
    lines = page.text.splitlines()
    count = 0
    
    for line in lines:
        if "|" in line:
            parts = line.split("|")
            # Strip namespaces if user accidentally included them in the mapping list
            # We enforce namespace 10 in the bot class, so we just need the base name here.
            src_raw = parts[0].strip().replace("Template:", "").replace("Bản mẫu:", "")
            tgt_raw = parts[1].strip().replace("Template:", "").replace("Bản mẫu:", "")

            if src_raw and tgt_raw:
                count += 1
                yield (src_raw, tgt_raw)
    
    pywikibot.info(f"Loaded {count} mappings.")

def main(*args):
    """
    Main function to parse args and run the bot.
    """
    local_args = pywikibot.handle_args(args)
    options = {}

    for arg in local_args:
        if arg == '-always':
            options['always'] = True
        elif arg.startswith('-summary:'):
            options['summary'] = arg[len('-summary:'):]

    # Initialize sites
    try:
        source_site = pywikibot.Site(SOURCE_LANG, FAMILY_NAME)
        target_site = pywikibot.Site(TARGET_LANG, FAMILY_NAME)
        
        # Login is usually required for the target site to edit
        target_site.login()
        
    except Exception as e:
        pywikibot.error(f"Could not initialize sites: {e}")
        return

    # Create generator from mapping page
    # Assuming mapping page is on the target wiki (vi), change if it's on source
    mapping_generator = load_mappings(target_site, MAPPING_PAGE_TITLE)

    # Initialize and run bot
    bot_instance = TemplateSyncBot(
        generator=mapping_generator,
        source_site=source_site,
        target_site=target_site,
        **options
    )
    
    bot_instance.run()

if __name__ == "__main__":
    main()
