import requests
import time
import sys
from dotenv import load_dotenv
import os
import argparse
import sqlite3
from fuzzywuzzy import fuzz

from goodreads_list import GoodreadsList

# Get API IP from environment variable, fallback to default
api_ip = os.environ.get("CALIBRE_API_IP", "100.67.69.109")
url_base = f"http://{api_ip}:8084/request/api/"
query_ending = "&lang=en&format=epub&format=mobi&format=azw3&format=fb2&format=djvu&format=cbz&format=cbr"

def get_response(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None

def get_book_status(id):
    status_url = url_base + "status"
    status_data = get_response(status_url)
    if not status_data:
        return "error"
    for category in status_data:
        if str(id) in status_data[category]:
            return category

if __name__ == "__main__":
    # Load environment variables from .env file if present, but allow direct env usage
    load_dotenv(override=False)
    metadata_path = os.environ.get("METADATA_DB")
    goodreads_urls_env = os.environ.get("GOODREADS_URLS", "")
    goodreads_urls = [url.strip() for url in goodreads_urls_env.split(",") if url.strip()]
    if not metadata_path or not goodreads_urls:
        print("Error: METADATA_DB or GOODREADS_URLS not set in environment variables or .env file.")
        sys.exit(1)
    conn = sqlite3.connect(metadata_path)
    cursor = conn.cursor()

    for goodreads_url in goodreads_urls:
        print(f"Processing Goodreads URL: {goodreads_url}")
        glist = GoodreadsList()
        books = glist.scrape(goodreads_url)
        if not books or len(books) == 0:
            print(f"No books found from Goodreads list: {goodreads_url}")
            continue

        for book_idx, book in enumerate(books):
            author = getattr(book, 'author', None)
            title = getattr(book, 'title', None)
            if not author or not title:
                print(f"Skipping book with missing author/title: {book}")
                continue

            # Fuzzy match for title and author
            cursor.execute("""
                SELECT books.title, authors.name FROM books
                JOIN books_authors_link ON books.id = books_authors_link.book
                JOIN authors ON books_authors_link.author = authors.id
            """)
            matches = cursor.fetchall()
            found_fuzzy = False
            for db_title, db_author in matches:
                title_score = fuzz.token_set_ratio(title.lower(), db_title.lower())
                author_score = fuzz.token_set_ratio(author.lower(), db_author.lower())
                if title_score > 90 and author_score > 90:
                    found_fuzzy = True
                    break
            if found_fuzzy:
                print(f"Skipping '{title}' by '{author}' (fuzzy match found in metadata.db)")
                continue

            print(f"\nBook {book_idx+1}: '{title}' by '{author}'")
            search_url = f"{url_base}search?author={author}&title={title}{query_ending}"
            data = get_response(search_url)
            if not (isinstance(data, list) and len(data) > 0 and 'id' in data[0]):
                print(f"No valid search result for '{title}' by '{author}'. Skipping.")
                continue

            found = False
            for attempt_idx, result in enumerate(data):
                book_id = result.get('id')
                print(f"  Attempt {attempt_idx+1}: Trying book ID {book_id}")
                download_url = url_base + f"download?id={book_id}"
                print(f"    Requesting download: {download_url}")
                download_response = get_response(download_url)

                poll = 1
                while True:
                    status = get_book_status(book_id)
                    print(f"      Poll {poll}: Book '{title}' (ID: {book_id}) status: {status}")
                    if status == "done":
                        print(f"Book '{title}' (ID: {book_id}) download completed successfully.")
                        found = True
                        break
                    elif status == "error":
                        print(f"Book '{title}' (ID: {book_id}) encountered an error. Trying next search result if available.")
                        break
                    time.sleep(5)
                    poll += 1
                if found:
                    break

    conn.close()