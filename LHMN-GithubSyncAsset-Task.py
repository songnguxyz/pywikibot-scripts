"""
Synchronize text assets between a GitHub repository and a MediaWiki site.

Target Wiki: lophocmatngu.wiki
Target Repo: wikilophocmatngu/assets
Mapping rules:
- MediaWiki/filename.ext -> MediaWiki:filename.ext
- Module/filename.lua -> Module:filename
"""

import os

import requests

import pywikibot
from pywikibot import exceptions


# Broken down to respect the 80-character line limit
GITHUB_API_BASE = 'https://api.github.com/repos/wikilophocmatngu'
GITHUB_API_URL = f'{GITHUB_API_BASE}/assets/contents/'
LOCAL_SYNC_DIR = './local_wiki_sync'
SYNC_DIRS = ['MediaWiki', 'Module']


def convert_path_to_title(file_path: str) -> str:
    """
    Convert a GitHub repository file path to a Wiki page title.

    :param file_path: The path of the file in the repository
    :type file_path: str
    :return: The formatted wiki page title
    :rtype: str
    """
    parts = file_path.split('/')
    if len(parts) != 2:
        return ''

    folder, filename = parts[0], parts[1]

    if folder == 'MediaWiki':
        return f'MediaWiki:{filename}'

    if folder == 'Module':
        if filename.endswith('.lua'):
            filename = filename[:-4]
        return f'Module:{filename}'

    return ''


def convert_title_to_path(page_title: str) -> str:
    """
    Convert a Wiki page title to a local or GitHub repository file path.

    :param page_title: The title of the page on the wiki
    :type page_title: str
    :return: The corresponding file path in the repository
    :rtype: str
    """
    parts = page_title.split(':')
    if len(parts) != 2:
        return ''

    namespace, title = parts[0], parts[1]

    if namespace == 'MediaWiki':
        return f'MediaWiki/{title}'

    if namespace == 'Module':
        return f'Module/{title}.lua'

    return ''


def fetch_github_directory_contents(directory_path: str) -> list:
    """
    Fetch the list of files in a specific directory using the GitHub API.

    :param directory_path: The path of the directory to fetch
    :type directory_path: str
    :return: A list of dictionaries containing file metadata
    :rtype: list
    """
    try:
        url = f'{GITHUB_API_URL}{directory_path}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as error:
        pywikibot.error(f'Failed to fetch {directory_path}: {error}')
        return []


def sync_github_to_wiki(site: pywikibot.Site) -> None:
    """
    Fetch text files from GitHub based on predefined directories.

    :param site: The Pywikibot Site object representing the target wiki
    :type site: pywikibot.Site
    """
    pywikibot.output('--- Starting GitHub to Wiki Sync ---')

    for directory in SYNC_DIRS:
        files = fetch_github_directory_contents(directory)

        for file_info in files:
            if file_info.get('type') != 'file':
                continue

            github_filepath = file_info.get('path')
            download_url = file_info.get('download_url')
            page_title = convert_path_to_title(github_filepath)

            if not page_title or not download_url:
                continue

            try:
                content_response = requests.get(download_url, timeout=10)
                content_response.raise_for_status()
                github_content = content_response.text

                page = pywikibot.Page(site, page_title)

                if page.exists() and page.text == github_content:
                    pywikibot.output(f'Skip {page_title}: No changes detected.')
                    continue

                page.text = github_content
                page.save(
                    summary='Bot: Synchronizing code asset from GitHub',
                    botflag=True
                )
                pywikibot.output(f'Updated {page_title} successfully.')

            except requests.exceptions.RequestException as error:
                pywikibot.error(f'Network error on {github_filepath}: {error}')
            except exceptions.LockedPageError:
                pywikibot.error(f'Cannot edit {page_title}: Page is locked.')
            except exceptions.PywikibotException as error:
                pywikibot.error(f'Pywikibot error on {page_title}: {error}')


def sync_wiki_to_local(site: pywikibot.Site) -> None:
    """
    Fetch specific namespaces from the wiki and save them locally.

    :param site: The Pywikibot Site object representing the target wiki
    :type site: pywikibot.Site
    """
    pywikibot.output('--- Starting Wiki to Local Sync ---')

    namespaces_to_sync = [8, 828]

    for ns in namespaces_to_sync:
        for page in site.allpages(namespace=ns):
            try:
                page_title = page.title()
                local_filepath = convert_title_to_path(page_title)

                if not local_filepath:
                    continue

                full_path = os.path.join(LOCAL_SYNC_DIR, local_filepath)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, 'w', encoding='utf-8') as file:
                    file.write(page.text)

                pywikibot.output(f'Saved {page_title} to {full_path}.')

            except OSError as error:
                pywikibot.error(f'File error saving {local_filepath}: {error}')
            except Exception as error:
                pywikibot.error(f'Error processing {page.title()}: {error}')


def main(*args: str) -> None:
    """
    Run the main execution loop for synchronization.

    :param args: Command line arguments
    :type args: tuple
    """
    local_args = pywikibot.handle_args(args)

    site = pywikibot.Site()
    site.login()

    pywikibot.config.put_throttle = 5

    sync_github_to_wiki(site)
    sync_wiki_to_local(site)

    pywikibot.output('Synchronization process completed!')


if __name__ == '__main__':
    main()
