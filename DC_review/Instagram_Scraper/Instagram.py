
import time
from datetime import datetime
import requests
import base64
import random
import os
import json
from datetime import datetime, timezone
import re
import pickle


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import JavascriptException, WebDriverException

class InstagramScraper:
    def __init__(self, username, password, chromedriver_path, tag, target_post_count=200, data_file=None):
        self.username = username
        self.password = password
        self.tag = tag
        self.chromedriver_path = chromedriver_path
        self.target_post_count = target_post_count

        self.data_file = data_file or f"instagram_off_data_{tag}.json"
        self.links_file = f"instagram_off_links_{tag}.json"

        self.scraped_data = []
        self.processed_links = set()
        self.unique_links = set()

        self._load_existing_data()
        self.driver = self._setup_driver()
        self._load_cookies()
        self._load_existing_links()



    def _random_sleep(self, a, b):
        sleep_time = random.uniform(a, b)
        print(f"[DEBUG] Sleeping for {sleep_time:.2f} seconds")
        time.sleep(sleep_time)

    def _load_existing_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.scraped_data = json.load(f)
                self.processed_links = {entry["link"] for entry in self.scraped_data}
                print(f"[DEBUG] Resuming from previous progress. Already processed {len(self.scraped_data)} posts.")
        else:
            print("[DEBUG] No previous data found. Starting fresh.")
    
    def _load_existing_links(self):
        if os.path.exists(self.links_file):
            with open(self.links_file, "r", encoding="utf-8") as f:
                self.unique_links = set(json.load(f))
                print(f"[DEBUG] Loaded {len(self.unique_links)} previously collected links.")
        else:
            print("[DEBUG] No previously collected links found.")

    def _setup_driver(self):
        print("[DEBUG] Setting up Chrome options")
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
        service = Service(self.chromedriver_path)
        return webdriver.Chrome(service=service, options=options)
    def _load_cookies(self):
        try:
            self.driver.get("https://www.instagram.com/")
            cookie_path = "instagram_cookies.pkl"
            if os.path.exists(cookie_path):
                with open(cookie_path, "rb") as f:
                    cookies = pickle.load(f)
                for cookie in cookies:
                    if "sameSite" in cookie:
                        del cookie["sameSite"]
                    self.driver.add_cookie(cookie)
                print("[DEBUG] Session cookies loaded.")
                self.driver.get("https://www.instagram.com/")
                self._random_sleep(5, 10)
            else:
                print("[DEBUG] No cookies file found. Proceeding to login manually.")
        except Exception as e:
            print(f"[DEBUG] Failed to load cookies: {e}")


    def login(self):
        print("[DEBUG] Navigating to Instagram login page")
        self.driver.get("https://www.instagram.com/accounts/login/")
        self._random_sleep(10, 20)

        try:
            cookies_button = self.driver.find_element(By.XPATH, "//button[text()='Only allow essential cookies']")
            print("[DEBUG] Found cookies acceptance button, clicking it...")
            cookies_button.click()
            self._random_sleep(10, 20)
        except Exception as e:
            print(f"[DEBUG] No cookies prompt detected: {e}")

        print("[DEBUG] Entering credentials")
        self.driver.find_element(By.NAME, "username").send_keys(self.username)
        password_input = self.driver.find_element(By.NAME, "password")
        password_input.send_keys(self.password)
        password_input.send_keys(Keys.RETURN)
        self._random_sleep(10, 20)
        with open("instagram_cookies.pkl", "wb") as f:
            pickle.dump(self.driver.get_cookies(), f)
        print("[DEBUG] Cookies saved to instagram_cookies.pkl")
        self._random_sleep(0,30)
    
    def _save_links(self):
        with open(self.links_file, "w", encoding="utf-8") as f:
            json.dump(list(self.unique_links), f, indent=2, ensure_ascii=False)

    def scroll_and_collect_links(self):
        tag_url = f"https://www.instagram.com/delhicapitals/"
        print(f"[DEBUG] Navigating to tag page of Delhi Capitals")
        self.driver.get(tag_url)
        self._random_sleep(10, 20)

        print("[DEBUG] Starting post collection with scrolling...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        retry_count = 0

        while len(self.unique_links) < self.target_post_count:
            posts = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
            new_links_found = False

            for post in posts:
                href = post.get_attribute("href")
                if href and href not in self.unique_links:
                    self.unique_links.add(href)
                    new_links_found = True

            if new_links_found:
                self._save_links()
                print(f"[DEBUG] Unique posts collected: {len(self.unique_links)}")

            if len(self.unique_links) >= self.target_post_count:
                break

            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            except JavascriptException:
                print("[DEBUG] JS scroll failed, retrying...")

            self._random_sleep(10, 20)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                retry_count += 1
                print(f"[DEBUG] No height change (retry {retry_count}/5)")
                if retry_count >= 5:
                    print("[DEBUG] Giving up after too many retries.")
                    break
                self.driver.execute_script("window.scrollBy(0, -100);")
                self._random_sleep(2, 12)
            else:
                retry_count = 0
                last_height = new_height

            self._random_sleep(0, 5)

        self.unique_links = list(self.unique_links)[:self.target_post_count]
        self._save_links()  # Final save

    # Make sure to have these imports at the top of your file


    def scrape_posts(self):
        long_break_every = random.randint(20, 40)
        
        cutoff_date_naive = datetime(2025, 6, 4)
        cutoff_date_utc = datetime(2025, 6, 4, tzinfo=timezone.utc)

        for index, link in enumerate(self.unique_links):
            if link in self.processed_links:
                print(f"⏭️ Skipping post {index + 1}, already scraped.")
                continue

            print(f"\n🔍 Visiting post #{index + 1}: {link}")
            loaded = False
            for attempt in range(1, 6):
                try:
                    self.driver.get(link)
                    loaded = True
                    print(f"✅ Loaded successfully on attempt {attempt}")
                    break
                except WebDriverException as e:
                    print(f"⚠️ Attempt {attempt} failed for {link}: {e}")
                    self._random_sleep(5, 15)

            if not loaded:
                print(f"❌ Failed to load post {link} after 5 attempts. Skipping.")
                self.processed_links.add(link)
                continue

            self._random_sleep(1.5, 4.5)

            # --- START OF FIX ---
            # 1. Get the raw time string from the page FIRST
            posting_time_raw = self._get_posting_time()

            if not posting_time_raw:
                print(f"⚠️ Could not find posting time for {link}. Skipping.")
                self.processed_links.add(link)
                continue

            # 2. Try parsing the two known formats
            posting_time = None
            try:
                # Try parsing ISO format (e.g., 2025-05-24T14:30:48.000Z)
                if posting_time_raw.endswith('Z'):
                    posting_time = datetime.fromisoformat(posting_time_raw.replace('Z', '+00:00'))
                else:
                    # Raise error to fall into the next `except` block for non-Z ISO formats
                    raise ValueError("Not a Z-terminated ISO string")
            except ValueError:
                # If ISO format fails, try the simple format (e.g., 2025-05-24 14:30:48)
                try:
                    posting_time = datetime.strptime(posting_time_raw, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"⚠️ Couldn't parse posting_time '{posting_time_raw}' with any known format. Skipping.")
                    self.processed_links.add(link)
                    continue

            # 3. Choose the correct cutoff date (aware vs. naive) for a safe comparison
            comparison_cutoff_date = cutoff_date_utc if posting_time.tzinfo else cutoff_date_naive
            if posting_time >= comparison_cutoff_date:
                print(f"🚫 Skipping post #{index + 1}, posted on {posting_time.date()} (on or after cutoff).")
                self.processed_links.add(link)
                continue
            # --- END OF FIX ---
            
            data = {
                "link": link,
                "posting_time": posting_time_raw, # Use the original raw string for data
                "likes": self._get_likes(),
                "caption": "",
                "hashtags": [],
                "images": self._get_images()
            }

            caption, hashtags = self._get_caption_and_hashtags()
            data["caption"] = caption
            data["hashtags"] = hashtags

            if caption:
                read_time = min(8, max(2, len(caption.split()) / 5))
                self._random_sleep(read_time - 1, read_time + 1)

            self.scraped_data.append(data)
            self.processed_links.add(link)
            self._save_data()

            print(f"💾 Saved post #{index + 1}. Total collected so far: {len(self.scraped_data)}")

            if (index + 1) % long_break_every == 0:
                break_time = random.uniform(30, 60)
                print(f"☕ Taking a short break ({break_time:.1f}s) to look less suspicious...")
                time.sleep(break_time)
                long_break_every = random.randint(20, 40)

            self._random_sleep(3, 10)


    def _get_posting_time(self):
        try:
            time_element = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "time"))
            )
            return time_element.get_attribute("datetime")
        except Exception as e:
            print(f"[DEBUG] Failed to get posting time: {e}")
            return None
    
    def _get_images(self):
        try:
            images = []
            img_elements = self.driver.find_elements(By.TAG_NAME, "img")
            for img in img_elements:
                src = img.get_attribute("src")
                if src and "instagram.f" in src:
                    # Download the image
                    try:
                        response = requests.get(src)
                        if response.status_code == 200:
                            # Encode as base64
                            b64 = base64.b64encode(response.content).decode('utf-8')
                            # Save as data URL (which Groq API accepts)
                            data_url = f"data:image/jpeg;base64,{b64}"
                            images.append(data_url)
                        else:
                            print(f"[DEBUG] Failed to download image: {src}")
                    except Exception as img_err:
                        print(f"[DEBUG] Exception downloading image: {img_err}")
                    if len(images) == 1:
                        break
            return images
        except Exception as e:
            print(f"[DEBUG] Failed to get images: {e}")
            return []
        

        except Exception as e:
            print(f"[DEBUG] Failed to get comments: {e}")
            return []





    def _get_likes(self):
        try:
            for span in self.driver.find_elements(By.TAG_NAME, "span"):
                text = span.text.strip()
                if text.endswith("likes"):
                    for inner in span.find_elements(By.TAG_NAME, "span"):
                        inner_text = inner.text.strip()
                        if re.match(r"^[\d,]+$", inner_text):
                            return inner_text
            print("[DEBUG] Likes not found in any span ending with 'likes'.")
            return None
        except Exception as e:
            print(f"[DEBUG] Exception while parsing likes: {e}")
            return None

    def _get_caption_and_hashtags(self):
        try:
            # 1. Try fetching <h1> caption with known class
            caption_elements = self.driver.find_elements(By.CSS_SELECTOR, "h1._ap3a._aaco._aacu._aacx._aad7._aade")
            for el in caption_elements:
                caption_text = el.text.strip()
                if caption_text:
                    break
            else:
                caption_text = ""

            # 2. Look for hashtags (in <a> tags inside <span> or anywhere relevant)
            tags = []
            spans = self.driver.find_elements(By.TAG_NAME, "span")
            for span in spans:
                a_tags = span.find_elements(By.TAG_NAME, "a")
                for a in a_tags:
                    href = a.get_attribute("href")
                    if href and "/explore/tags/" in href:
                        tags.append(a.text)

            # Optional: remove hashtags from caption if present in same text
            for tag in tags:
                caption_text = caption_text.replace(tag, "")

            return caption_text.strip(), tags
        except Exception as e:
            print(f"[DEBUG] Failed to extract caption and hashtags: {e}")
            return "", []


    def _save_data(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.scraped_data, f, indent=2, ensure_ascii=False)

    def close(self):
        print("[DEBUG] Script finished. Press Enter to close the browser.")
        input()
        self.driver.quit()

# === MAIN EXECUTION ===
if __name__ == "__main__":
    scraper = InstagramScraper(
        username="username",
        password="password",
        chromedriver_path="driver_path",
        tag="DC"
    )
    try:
        # If no cookies file, do login
        if not os.path.exists("instagram_cookies.pkl"):
            scraper.login()
        scraper.scroll_and_collect_links()
        scraper.scrape_posts()
    finally:
        scraper.close()