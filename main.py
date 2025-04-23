import os

import chardet
from lxml import etree

NS = {"fb": "http://www.gribuser.ru/xml/fictionbook/2.0"}


def detect_encoding(filepath):
    with open(filepath, "rb") as f:
        raw = f.read()
    result = chardet.detect(raw)
    return result["encoding"] or "utf-8"


def parse_fb2(file_path):
    encoding = detect_encoding(file_path)
    with open(file_path, "rb") as f:
        content = f.read()

    decoded = content.decode(encoding, errors="ignore")
    parser = etree.XMLParser(recover=True)
    tree = etree.fromstring(decoded.encode("utf-8"), parser)

    title = tree.findtext(".//fb:book-title", namespaces=NS) or "Без названия"
    authors = tree.findall(".//fb:author", namespaces=NS)
    author_names = []
    for a in authors:
        fn = a.findtext("fb:first-name", default="", namespaces=NS)
        ln = a.findtext("fb:last-name", default="", namespaces=NS)
        full_name = f"{fn} {ln}".strip()
        if full_name:
            author_names.append(full_name)

    author_str = ", ".join(author_names) or "Неизвестный автор"
    body = tree.find(".//fb:body", namespaces=NS)
    paragraphs = body.findall(".//fb:p", namespaces=NS) if body is not None else []

    full_text = "\n\n".join(
        [
            etree.tostring(p, method="text", encoding="unicode").strip()
            for p in paragraphs
            if p.text and p.text.strip()
        ]
    )

    return {"title": title, "author": author_str, "text": full_text}


def split_text_fixed(text, max_chars=1500):
    words = text.split()
    chunks = []
    chunk = ""

    for word in words:
        if len(chunk) + len(word) + 1 <= max_chars:
            chunk += (" " if chunk else "") + word
        else:
            chunks.append(chunk.strip())
            chunk = word

    if chunk:
        chunks.append(chunk.strip())

    return chunks


def slugify(text):
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in text)


def process_books():
    for file in os.listdir():
        if file.lower().endswith(".fb2"):
            print(f"📘 Обработка: {file}")
            try:
                data = parse_fb2(file)
                folder_name = f"{data['author']} - {data['title']}"
                folder_name = slugify(folder_name).strip()
                os.makedirs(folder_name, exist_ok=True)

                pages = split_text_fixed(data["text"], max_chars=1500)
                total = len(pages)

                for i, page in enumerate(pages, start=1):
                    md_page = page + "\n\n---\n"
                    if i > 1:
                        md_page += f"[⏮ Назад]({i - 1}.md) "
                    if i < total:
                        if i > 1:
                            md_page += "| "
                        md_page += f"[Вперёд ⏭]({i + 1}.md)"

                    with open(os.path.join(folder_name, f"{i}.md"), "w", encoding="utf-8") as f:
                        f.write(md_page.strip())

                print(f"✅ Сохранено: {total} страниц → {folder_name}")
            except Exception as e:
                print(f"❌ Ошибка при обработке {file}: {e}")


if __name__ == "__main__":
    process_books()
