#!/usr/bin/python3
"""
This script reverses character names in wiki links based on a validation list.
Example: Changes [[Aoi Megumi]] to [[Megumi Aoi]] if valid.

It fetches a list of valid names from 'MediaWiki:CharacterList'.

Usage:
    python3 character_link_reverser.py [generator options] [-always]

    To run on a specific page:
    python3 character_link_reverser.py -page:"Page Title"

    To run on all pages in main namespace:
    python3 character_link_reverser.py -ns:0 -start:!

Options:
    -always     Don't prompt to save changes.
    -summary:   Custom edit summary.
"""

import pywikibot
import re
from pywikibot import pagegenerators, textlib
from pywikibot.bot import SingleSiteBot, CurrentPageBot

# Configuration
NAME_LIST_PAGE = "MediaWiki:CharacterList"

class CharacterLinkFixBot(SingleSiteBot, CurrentPageBot):
    """
    Bot to reverse character names in links.
    """

    def __init__(self, generator, valid_names, **kwargs):
        """
        Constructor.
        
        Args:
            generator: The page generator.
            valid_names (set): A set of valid character names (already in correct order).
        """
        self.available_options.update({
            'always': False,
            'summary': 'Bot: Reverse character name links (Standardization)',
        })
        super().__init__(site=True, generator=generator, **kwargs)
        self.valid_names = valid_names

    def reverse_name(self, name: str) -> str:
        """
        Reverses a name string.
        Example: "Aoi Megumi" -> "Megumi Aoi"
        """
        parts = name.split()
        if len(parts) >= 2:
            return ' '.join(parts[::-1])
        return name

    def replace_link(self, match):
        """
        Callback function to process each link match found by regex.
        """
        full_match = match.group(0)
        raw_target = match.group(1).strip()
        # group(2) is the pipe including |, group(3) is the text after pipe
        display_text = match.group(3) 

        # Handle anchors (e.g., [[Page#Section]])
        if '#' in raw_target:
            base_target, anchor_part = raw_target.split('#', 1)
            anchor_part = f'#{anchor_part}'
        else:
            base_target = raw_target
            anchor_part = ''

        # Calculate potential new target
        new_base_target = base_target
        reversed_candidate = self.reverse_name(base_target)

        # LOGIC CHECK: Only change if the reversed version is in the valid list
        # and it is different from the current target.
        if reversed_candidate in self.valid_names and reversed_candidate != base_target:
            new_base_target = reversed_candidate
        
        final_target = new_base_target + anchor_part

        # If no change in target, return original text
        if final_target == raw_target:
            # Cleanup: if [[Target|Target]], simplify to [[Target]]
            if display_text and display_text.strip() == base_target:
                return f'[[{final_target}]]'
            return full_match

        # Construct the new link
        if display_text:
            # If label matches the new target or old target, simplify link
            if display_text.strip() == base_target or display_text.strip() == new_base_target:
                return f'[[{final_target}]]'
            return f'[[{final_target}|{display_text}]]'
        else:
            return f'[[{final_target}]]'

    def treat_page(self):
        """
        Process a single page.
        """
        page = self.current_page
        
        # Skip Main Page
        if page.title() == self.site.siteinfo['mainpage']:
            pywikibot.info(f'Skipping Main Page: {page.title()}')
            return

        # Skip non-main namespace (redundant if generator is filtered, but safe)
        if page.namespace() != 0:
            pywikibot.info(f'Skipping non-article page: {page.title()}')
            return

        pywikibot.info(f'Processing page: {page.title()}')
        
        text = page.text
        original_text = text

        # Regex to find links: [[Target]] or [[Target|Label]]
        # Group 1: Target
        # Group 2: |Label (optional)
        # Group 3: Label (content of group 2 without pipe)
        link_pattern = re.compile(r'\[\[([^\|\]]+)(\|([^\]]+))?\]\]')

        # Use textlib.replaceExcept to safely replace text ignoring protected areas
        # (nowiki, comments, pre, source, math, etc.)
        new_text = textlib.replaceExcept(
            text,
            link_pattern,
            self.replace_link,
            ['comment', 'math', 'nowiki', 'pre', 'source', 'syntaxhighlight'],
            site=self.site
        )

        # Save changes if any
        if new_text != original_text:
            self.put_current(new_text, summary=self.opt.summary, show_diff=True)
        else:
            pywikibot.info(f'No changes required for {page.title()}')

def get_valid_names(site) -> set:
    """
    Fetches the list of valid names from the wiki page.
    """
    page = pywikibot.Page(site, NAME_LIST_PAGE)
    names = set()

    if not page.exists():
        pywikibot.warning(f"Name list page not found: {NAME_LIST_PAGE}")
        return names

    pywikibot.info(f"Loading valid names from {NAME_LIST_PAGE}...")
    for line in page.text.splitlines():
        line = line.strip()
        if line.startswith("* "):
            name = line[2:].strip()
            if name:
                names.add(name)
    
    pywikibot.info(f"Loaded {len(names)} valid names.")
    return names

def main(*args):
    """
    Main function.
    """
    local_args = pywikibot.handle_args(args)
    gen_factory = pagegenerators.GeneratorFactory()
    
    options = {}

    for arg in local_args:
        if arg == '-always':
            options['always'] = True
        elif arg.startswith('-summary:'):
            options['summary'] = arg[len('-summary:'):]
        else:
            gen_factory.handle_arg(arg)

    site = pywikibot.Site()
    
    # 1. Load valid names first
    valid_names = get_valid_names(site)
    if not valid_names:
        pywikibot.error("No valid names found. Aborting.")
        return

    # 2. Get generator
    generator = gen_factory.getCombinedGenerator()

    # NOTE: Unlike the old script, we do NOT default to ALL pages automatically for safety.
    # Users should explicitily pass -start:! or -ns:0 to run on all pages.
    if generator:
        generator = pagegenerators.PreloadingGenerator(generator)
        bot = CharacterLinkFixBot(generator=generator, valid_names=valid_names, **options)
        bot.run()
    else:
        pywikibot.bot.suggest_help(missing_generator=True)

if __name__ == '__main__':
    main()
