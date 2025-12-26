import pywikibot
import re
import sys
import difflib

# Danh sách regex để xác định tên nhân vật cần đảo
REGEX_PATTERNS = [
    r'^[A-Z][a-z]+ [A-Z][a-z]+$'                     # VD: Aoi Megumi
]

# Trang chứa danh sách tên nhân vật chuẩn
NAME_LIST_PAGE = "MediaWiki:CharacterList"

def reverse_name(name: str) -> str:
    parts = name.split()
    return ' '.join(parts[::-1]) if len(parts) >= 2 else name

def should_reverse(title: str, valid_names: set) -> bool:
    return title in valid_names

def process_links(text: str, valid_names: set) -> str:
    placeholders = {}
    placeholder_id = 0

    def protect_block(match):
        nonlocal placeholder_id
        placeholder = f"__BOT_PROTECT_{placeholder_id}__"
        placeholders[placeholder] = match.group(0)
        placeholder_id += 1
        return placeholder

    protected_text = re.sub(
        r'(<nowiki>.*?</nowiki>|<!--.*?-->|<pre>.*?</pre>|<source.*?>.*?</source>|<syntaxhighlight.*?>.*?</syntaxhighlight>)',
        protect_block, text, flags=re.DOTALL | re.IGNORECASE
    )

    def replacer(match):
        full_match = match.group(0)
        raw_target = match.group(1).strip()
        display_text = match.group(3)

        if '#' in raw_target:
            base_target, anchor_part = raw_target.split('#', 1)
            anchor_part = f'#{anchor_part}'
        else:
            base_target = raw_target
            anchor_part = ''

        new_base_target = base_target
        reversed_base_candidate = reverse_name(base_target)

        if reversed_base_candidate in valid_names and reversed_base_candidate != base_target:
            new_base_target = reversed_base_candidate

        final_target = new_base_target + anchor_part

        if final_target == raw_target:
            if display_text and display_text.strip() == base_target:
                return f'[[{final_target}]]'
            return full_match

        if display_text:
            if display_text.strip() == base_target or display_text.strip() == new_base_target:
                return f'[[{final_target}]]'
            return f'[[{final_target}|{display_text}]]'
        else:
            return f'[[{final_target}]]'

    pattern = re.compile(r'\[\[([^\|\]]+)(\|([^\]]+))?\]\]')
    processed_text = pattern.sub(replacer, protected_text)

    for placeholder, original in placeholders.items():
        processed_text = processed_text.replace(placeholder, original)

    return processed_text

def get_valid_names_from_page(site) -> set:
    page = pywikibot.Page(site, NAME_LIST_PAGE)
    if not page.exists():
        print(f"Không tìm thấy trang danh sách: {NAME_LIST_PAGE}")
        return set()

    text = page.text
    lines = text.splitlines()
    names = set()
    for line in lines:
        line = line.strip()
        if line.startswith("* "):
            name = line[2:].strip()
            if name:
                names.add(name)
    return names

def reverse_links_on_page(site, page_title, valid_names, dry_run=False):
    page = pywikibot.Page(site, page_title)

    # Lấy tên Trang Chính từ thông tin của site và bỏ qua nó
    main_page_title = site.siteinfo.get('mainpage')
    if page.title() == main_page_title:
        print(f"🔒  Bỏ qua Trang Chính: {page.title()}")
        return

    if page.namespace() != 0:
        print(f"Bỏ qua trang không thuộc không gian tên chính: {page.title()}")
        return
 
    text = page.text
    new_text = process_links(text, valid_names)
 
    if new_text != text:
        print(f"✨ Phát hiện thay đổi cho trang: {page.title()}")
        
        diff = difflib.unified_diff(
            text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f'a/{page.title()}',
            tofile=f'b/{page.title()}',
        )
        print("--- Chi tiết thay đổi ---")
        sys.stdout.writelines(diff)
        print("--- Kết thúc thay đổi ---")
 
        if dry_run:
            print(f"🔩 [Dry-run] Bỏ qua lưu trang.")
        else:
            try:
                page.text = new_text
                page.save(summary="Bot: Đảo ngược liên kết nhân vật")
                print(f"✅ Đã cập nhật trang: {page.title()}")
            except Exception as e:
                print(f"❌ Lỗi khi lưu trang {page.title()}: {e}")
    else:
        print(f"👌 Không có thay đổi trên trang: {page.title()}")

def process_multiple_pages(pages, valid_names, dry_run=False):
    site = pywikibot.Site()
    site.login()
 
    for i, title in enumerate(pages):
        if i > 0:
            print("\n" + "="*50)
        try:
            reverse_links_on_page(site, title.strip(), valid_names, dry_run=dry_run)
        except Exception as e:
            print(f"Lỗi với trang '{title}': {e}")

if __name__ == "__main__":
    dry_run = '--dry-run' in sys.argv

    site = pywikibot.Site()
    site.login()

    valid_names = get_valid_names_from_page(site)

    if not valid_names:
        print("Không lấy được danh sách tên hợp lệ. Dừng script.")
        sys.exit(1)

    # Nếu không có trang nào được nhập, mặc định lấy tất cả trang trong namespace 0
    if len(sys.argv) > 1 and sys.argv[1] != '--dry-run':
        input_pages = sys.argv[1:]
    else:
        print("Không có tên trang nào được cung cấp. Sẽ xử lý tất cả các trang trong không gian tên Chính.")
        all_pages = site.allpages(namespace=0)
        input_pages = [page.title() for page in all_pages]

    if not input_pages:
        print("Không có trang nào để xử lý. Kết thúc.")
    else:
        process_multiple_pages(input_pages, valid_names, dry_run=dry_run)
