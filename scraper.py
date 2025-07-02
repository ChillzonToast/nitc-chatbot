import asyncio
import aiohttp
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from typing import Dict, Set, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikiScraper:
    def __init__(self, max_concurrent: int = 50):
        self.base_url = "https://wiki.fosscell.org"
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
        
        # Data variable
        self.data = {
            "pages": [],
            "total_pages": 0,
            "last_updated": time.time(),
            "last_oldid": 0  # Track progress
        }
        
        self.json_file = "wiki_data.json"
        
        # Range: 1 to 2606 (included)
        self.start_oldid = 1
        self.end_oldid = 2606
        
    async def __aenter__(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def load_data(self):
        """Load JSON data from saved file if exists"""
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                
                self.data["pages"] = saved_data.get("pages", [])
                self.data["total_pages"] = len(self.data["pages"])
                self.data["last_oldid"] = saved_data.get("last_oldid", 0)
                
                print(f"✅ Loaded {self.data['total_pages']} pages from {self.json_file}")
                print(f"📍 Last scraped oldid: {self.data['last_oldid']}")
                return True
            except Exception as e:
                print(f"❌ Error loading {self.json_file}: {e}")
                return False
        else:
            print(f"📁 No existing {self.json_file} found, starting fresh")
            return False
    
    def save_data(self):
        """Overwrite JSON file with data in variable"""
        try:
            self.data["total_pages"] = len(self.data["pages"])
            self.data["last_updated"] = time.time()
            
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved {self.data['total_pages']} pages to {self.json_file} (last oldid: {self.data['last_oldid']})")
            
        except Exception as e:
            print(f"❌ Error saving to {self.json_file}: {e}")
    
    async def scrape_oldid(self, oldid: int):
        """Scrape specific oldid"""
        async with self.semaphore:
            try:
                url = f"{self.base_url}/index.php?oldid={oldid}"
                
                async with self.session.get(url) as response:
                    if response.status != 200:
                        print(f"❌ Failed to fetch oldid {oldid}: HTTP {response.status}")
                        return None
                    
                    final_url = str(response.url)
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract title
                    title_elem = soup.find('h1', {'id': 'firstHeading'}) or soup.find('title')
                    title = title_elem.get_text().strip() if title_elem else f"Page {oldid}"
                    
                    # Extract content
                    content_div = soup.find('div', {'id': 'mw-content-text'})
                    if content_div:
                        # Remove unwanted elements
                        for unwanted in content_div.find_all(['div', 'table'], {'class': ['navbox', 'infobox', 'toc']}):
                            unwanted.decompose()
                        content = content_div.get_text().strip()
                        content = ' '.join(content.split())
                    else:
                        content = ""
                    
                    # Extract categories
                    categories = []
                    for link in soup.find_all('a', href=lambda x: x and 'Category:' in x):
                        cat = link.get_text().strip()
                        if cat and cat not in categories:
                            categories.append(cat)
                    
                    # Create page data
                    page_data = {
                        'oldid': oldid,
                        'title': title,
                        'url': final_url,
                        'content': content,
                        'categories': categories,
                        'word_count': len(content.split()) if content else 0,
                        'scraped_at': time.time()
                    }
                    
                    print(f"📄 oldid {oldid}: {title} ({page_data['word_count']} words)")
                    return page_data
                    
            except Exception as e:
                print(f"❌ Error scraping oldid {oldid}: {e}")
                return None
    
    async def run_systematic(self):
        """Scrape systematically from 1 to 2606"""
        # Load existing data
        self.load_data()
        
        # Determine starting point
        start_from = self.data["last_oldid"] + 1
        
        print(f"🚀 Starting systematic scraping")
        print(f"📊 Range: oldid {self.start_oldid} to {self.end_oldid} (total: {self.end_oldid} pages)")
        print(f"📍 Starting from oldid: {start_from}")
        print(f"⚡ Concurrent requests: {self.max_concurrent}")
        print(f"💾 Will save every 50 pages")
        print("-" * 60)
        
        pages_since_last_save = 0
        
        try:
            # Process in batches
            for batch_start in range(start_from, self.end_oldid + 1, self.max_concurrent):
                batch_end = min(batch_start + self.max_concurrent - 1, self.end_oldid)
                batch_oldids = list(range(batch_start, batch_end + 1))
                
                print(f"🔄 Processing batch: oldid {batch_start} to {batch_end}")
                
                # Create tasks for this batch
                tasks = [self.scrape_oldid(oldid) for oldid in batch_oldids]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(results):
                    current_oldid = batch_oldids[i]
                    
                    if isinstance(result, dict):
                        # Append new page into the dict
                        self.data["pages"].append(result)
                        pages_since_last_save += 1
                    
                    # Update last_oldid regardless of success/failure
                    self.data["last_oldid"] = current_oldid
                
                # Save every 50 pages
                if pages_since_last_save >= 50:
                    self.save_data()
                    pages_since_last_save = 0
                
                # Progress update
                progress = ((batch_end - self.start_oldid + 1) / self.end_oldid) * 100
                print(f"📈 Progress: {progress:.1f}% | Total pages collected: {len(self.data['pages'])}")
                
                # Small delay
                await asyncio.sleep(0.5)
                
        except KeyboardInterrupt:
            print(f"\n⏸️  Stopped by user at oldid {self.data['last_oldid']}")
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")
        finally:
            # Final save
            print(f"💾 Final save...")
            self.save_data()
            
            if self.data['last_oldid'] >= self.end_oldid:
                print(f"🎉 COMPLETED! All pages from oldid 1 to {self.end_oldid} processed")
            else:
                print(f"⏸️  Stopped at oldid {self.data['last_oldid']}, run again to continue")
            
            print(f"✅ Total pages collected: {len(self.data['pages'])}")

async def main():
    print("🌟 FOSSCELL Wiki Systematic Scraper")
    print("📋 Scraping oldid 1 to 2606")
    print("=" * 40)
    
    async with WikiScraper(max_concurrent=50) as scraper:
        await scraper.run_systematic()

if __name__ == "__main__":
    asyncio.run(main())