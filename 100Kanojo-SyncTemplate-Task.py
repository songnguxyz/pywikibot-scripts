import pywikibot

# Cấu hình
MAPPING_PAGE_TITLE = "MediaWiki:SyncTemplateMapping"  # Trang chứa ánh xạ bản mẫu
FAMILY = "mottrambangai"

# Khởi tạo site
source_site = pywikibot.Site("en", FAMILY)
target_site = pywikibot.Site("vi", FAMILY)

def parse_mapping_page(title):
    """Đọc trang ánh xạ và trả về danh sách (en_title, vi_title)"""
    page = pywikibot.Page(target_site, title)
    mappings = []

    for line in page.text.splitlines():
        if "|" in line:
            parts = line.split("|")
            en_raw = parts[0].strip()
            vi_raw = parts[1].strip()

            # Làm sạch tiêu đề
            en_title = en_raw.replace("Template:", "").replace("Bản mẫu:", "").strip()
            vi_title = vi_raw.replace("Bản mẫu:", "").strip()

            if en_title and vi_title:
                mappings.append((en_title, vi_title))

    return mappings

def sync_template(en_title, vi_title):
    en_page = pywikibot.Page(source_site, f"Template:{en_title}")
    vi_page = pywikibot.Page(target_site, f"Bản mẫu:{vi_title}")

    if not en_page.exists():
        print(f"[!] Không tìm thấy Template:{en_title} trên enwiki")
        return

    try:
        content = en_page.get()
        summary = f"Đồng bộ nội dung từ Template:{en_title} (enwiki) bằng bot"
        vi_page.put(content, summary=summary, minor=False)
        print(f"[✓] Đã cập nhật Bản mẫu:{vi_title}")
    except Exception as e:
        print(f"[X] Lỗi khi cập nhật {vi_title}: {e}")

def main():
    mappings = parse_mapping_page(MAPPING_PAGE_TITLE)
    print(f"Đã tìm thấy {len(mappings)} ánh xạ")

    for en_title, vi_title in mappings:
        sync_template(en_title, vi_title)

if __name__ == "__main__":
    main()
