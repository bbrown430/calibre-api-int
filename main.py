import requests
import time
import sys
import sqlite3
from goodreads_list import GoodreadsList

url_base = "http://100.67.69.109:8084/request/api/"
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
    for category in status_data:
        if str(id) in status_data[category]:
            return category

if __name__ == "__main__":
    # Prompt user for Goodreads list URL
    goodreads_url = input("Enter Goodreads list URL: ").strip()
    glist = GoodreadsList()
    books = glist.scrape(goodreads_url)
    if not books or len(books) == 0:
        print("No books found from Goodreads list.")
        sys.exit(1)

    # For each book, search and download
    for book_idx, book in enumerate(books):
        author = getattr(book, 'author', None)
        title = getattr(book, 'title', None)
        if not author or not title:
            print(f"Skipping book with missing author/title: {book}")
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