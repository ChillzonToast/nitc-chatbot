import asyncio
import aiohttp
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, Set, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikiScraper:
    def __init__(self, base_url: str = "https://wiki.fosscell.org", max_concurrent: int = 20):
        self.base_url = base_url
        self.random_url = f"{base_url}/index.php?title=Special:Random"
        self.max_concurrent = max_concurrent
        self.scraped_pages: Set[str] = set()
        self.scraped_data: List[Dict] = []
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Resume functionality
        self.checkpoint_file = "scraping_checkpoint.json"
        self.checkpoint_interval = 10  # Save checkpoint every N pages
        
    async def __aenter__(self):
        # Create session with appropriate headers
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout,
            headers=headers
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def load_checkpoint(self) -> bool:
        """Load previous scraping progress from checkpoint file"""
        if not os.path.exists(self.checkpoint_file):
            logger.info("No checkpoint file found, starting fresh")
            return False
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            self.scraped_data = checkpoint_data.get('scraped_data', [])
            scraped_urls = checkpoint_data.get('scraped_urls', [])
            self.scraped_pages = set(scraped_urls)
            
            logger.info(f"✅ Checkpoint loaded: {len(self.scraped_data)} pages already scraped")
            logger.info(f"📝 {len(self.scraped_pages)} URLs in duplicate prevention list")
            
            # Show some examples of what was previously scraped
            if self.scraped_data:
                logger.info("Recently scraped pages:")
                for page in self.scraped_data[-3:]:
                    logger.info(f"  - {page['title']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading checkpoint: {str(e)}")
            logger.info("Starting fresh due to checkpoint error")
            return False
    
    def save_checkpoint(self):
        """Save current progress to checkpoint file"""
        try:
            checkpoint_data = {
                'scraped_data': self.scraped_data,
                'scraped_urls': list(self.scraped_pages),
                'last_saved': time.time(),
                'total_pages_scraped': len(self.scraped_data)
            }
            
            # Save to temporary file first, then rename (atomic operation)
            temp_file = self.checkpoint_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_file, self.checkpoint_file)
            logger.debug(f"💾 Checkpoint saved: {len(self.scraped_data)} pages")
            
        except Exception as e:
            logger.error(f"❌ Error saving checkpoint: {str(e)}")
    
    def cleanup_checkpoint(self):
        """Remove checkpoint file after successful completion"""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
                logger.info("🧹 Checkpoint file cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up checkpoint: {str(e)}")
    
    async def get_random_page(self) -> Dict:
        """Fetch a random page and extract its content"""
        async with self.semaphore:
            try:
                # First, get the random page (this will redirect to actual page)
                async with self.session.get(self.random_url, allow_redirects=True) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch random page: {response.status}")
                        return None
                    
                    final_url = str(response.url)
                    
                    # Check if we've already scraped this page
                    if final_url in self.scraped_pages:
                        logger.debug(f"Duplicate page found: {final_url}")
                        return None
                    
                    self.scraped_pages.add(final_url)
                    html_content = await response.text()
                    
                    # Parse the HTML
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract page data
                    page_data = self.extract_page_data(soup, final_url)
                    
                    if page_data:
                        logger.info(f"📄 Scraped: {page_data['title']} ({page_data['word_count']} words)")
                        return page_data
                    
            except asyncio.TimeoutError:
                logger.error(f"Timeout while fetching random page")
            except Exception as e:
                logger.error(f"Error fetching random page: {str(e)}")
            
            return None
    
    def extract_page_data(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract relevant data from the wiki page"""
        try:
            # Extract title
            title_elem = soup.find('h1', {'id': 'firstHeading'}) or soup.find('title')
            title = title_elem.get_text().strip() if title_elem else "Unknown Title"
            
            # Extract main content
            content_div = soup.find('div', {'id': 'mw-content-text'}) or soup.find('div', {'class': 'mw-parser-output'})
            
            if not content_div:
                # Fallback to main content area
                content_div = soup.find('div', {'id': 'content'})
            
            # Extract text content
            text_content = ""
            if content_div:
                # Remove navigation elements, info boxes, etc.
                for unwanted in content_div.find_all(['div', 'table'], {'class': ['navbox', 'infobox', 'toc', 'navigation-not-searchable']}):
                    unwanted.decompose()
                
                # Get clean text
                text_content = content_div.get_text().strip()
                # Clean up whitespace
                text_content = ' '.join(text_content.split())
            
            # Extract categories
            categories = []
            category_links = soup.find_all('a', href=lambda x: x and 'Category:' in x)
            for link in category_links:
                category = link.get_text().strip()
                if category and category not in categories:
                    categories.append(category)
            
            # Extract internal links
            internal_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and href.startswith('/') and not href.startswith('//'):
                    full_url = urljoin(self.base_url, href)
                    link_text = link.get_text().strip()
                    if link_text and full_url not in [l['url'] for l in internal_links]:
                        internal_links.append({
                            'text': link_text,
                            'url': full_url
                        })
            
            # Get page metadata
            last_modified = None
            modified_elem = soup.find('li', {'id': 'footer-info-lastmod'})
            if modified_elem:
                last_modified = modified_elem.get_text().strip()
            
            return {
                'title': title,
                'url': url,
                'text_content': text_content,
                'categories': categories,
                'internal_links': internal_links[:10],  # Limit to first 10 links
                'last_modified': last_modified,
                'scraped_at': time.time(),
                'word_count': len(text_content.split()) if text_content else 0
            }
            
        except Exception as e:
            logger.error(f"Error extracting page data: {str(e)}")
            return None
    
    async def scrape_pages(self, target_pages: int = 100) -> List[Dict]:
        """Scrape multiple random pages with resume capability"""
        # Load existing progress
        self.load_checkpoint()
        
        pages_needed = target_pages - len(self.scraped_data)
        if pages_needed <= 0:
            logger.info(f"✅ Target already reached! {len(self.scraped_data)} pages already scraped")
            return self.scraped_data
        
        logger.info(f"🎯 Target: {target_pages} pages")
        logger.info(f"📊 Already have: {len(self.scraped_data)} pages")
        logger.info(f"🔄 Need to scrape: {pages_needed} more pages")
        logger.info(f"⚡ Using {self.max_concurrent} concurrent requests")
        
        pages_scraped_this_session = 0
        
        try:
            while len(self.scraped_data) < target_pages:
                # Calculate batch size
                remaining = target_pages - len(self.scraped_data)
                batch_size = min(self.max_concurrent, remaining)
                
                # Create batch of tasks
                batch_tasks = [self.get_random_page() for _ in range(batch_size)]
                
                # Execute batch
                results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process results
                new_pages_in_batch = 0
                for result in results:
                    if isinstance(result, dict) and result is not None:
                        self.scraped_data.append(result)
                        new_pages_in_batch += 1
                        pages_scraped_this_session += 1
                    elif isinstance(result, Exception):
                        logger.error(f"Task failed with exception: {result}")
                
                # Save checkpoint periodically
                if len(self.scraped_data) % self.checkpoint_interval == 0:
                    self.save_checkpoint()
                
                # Progress update
                progress_pct = (len(self.scraped_data) / target_pages) * 100
                logger.info(f"📈 Progress: {len(self.scraped_data)}/{target_pages} ({progress_pct:.1f}%) | +{new_pages_in_batch} new pages this batch")
                
                # Small delay to be respectful to the server
                await asyncio.sleep(0.5)
            
            # Final checkpoint save
            self.save_checkpoint()
            
            logger.info(f"🎉 Scraping completed!")
            logger.info(f"📊 Total pages: {len(self.scraped_data)}")
            logger.info(f"🆕 Pages scraped this session: {pages_scraped_this_session}")
            
        except Exception as e:
            logger.error(f"❌ Error during scraping: {str(e)}")
            self.save_checkpoint()  # Save progress before failing
            raise
        
        return self.scraped_data
    
    def save_data(self, filename: str = "fosscell_wiki_data.json"):
        """Save scraped data to JSON file and clean up checkpoint"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'scraped_at': time.time(),
                    'total_pages': len(self.scraped_data),
                    'pages': self.scraped_data
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Data saved to {filename}")
            
            # Also save a summary
            summary_filename = filename.replace('.json', '_summary.txt')
            with open(summary_filename, 'w', encoding='utf-8') as f:
                f.write(f"FOSSCELL Wiki Scraping Summary\n")
                f.write(f"==============================\n")
                f.write(f"Total pages scraped: {len(self.scraped_data)}\n")
                f.write(f"Scraping completed at: {time.ctime()}\n\n")
                
                f.write("Pages scraped:\n")
                for i, page in enumerate(self.scraped_data, 1):
                    f.write(f"{i:3d}. {page['title']} ({page['word_count']} words)\n")
                    f.write(f"     URL: {page['url']}\n")
                    if page['categories']:
                        f.write(f"     Categories: {', '.join(page['categories'][:3])}\n")
                    f.write("\n")
            
            logger.info(f"📋 Summary saved to {summary_filename}")
            
            # Clean up checkpoint file after successful save
            self.cleanup_checkpoint()
            
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")

async def main():
    """Main function to run the scraper"""
    # Configuration
    TARGET_PAGES = 50  # Adjust as needed
    OUTPUT_FILE = "fosscell_wiki_data.json"
    
    print("🚀 FOSSCELL Wiki Scraper with Resume Capability")
    print("=" * 50)
    
    async with WikiScraper(max_concurrent=20) as scraper:
        try:
            # Scrape pages (will resume from checkpoint if available)
            scraped_data = await scraper.scrape_pages(TARGET_PAGES)
            
            # Save final data
            scraper.save_data(OUTPUT_FILE)
            
            # Print final summary
            print(f"\n✅ Scraping completed successfully!")
            print(f"📊 Total unique pages scraped: {len(scraped_data)}")
            print(f"💾 Data saved to: {OUTPUT_FILE}")
            print(f"📋 Summary saved to: {OUTPUT_FILE.replace('.json', '_summary.txt')}")
            
            if scraped_data:
                avg_words = sum(page['word_count'] for page in scraped_data) / len(scraped_data)
                print(f"📈 Average words per page: {avg_words:.1f}")
                
                # Show categories found
                all_categories = set()
                for page in scraped_data:
                    all_categories.update(page.get('categories', []))
                if all_categories:
                    print(f"🏷️  Categories found: {len(all_categories)}")
                
        except KeyboardInterrupt:
            print(f"\n⏸️  Scraping interrupted by user")
            if scraper.scraped_data:
                scraper.save_checkpoint()
                print(f"💾 Progress saved: {len(scraper.scraped_data)} pages")
                print(f"🔄 Run the script again to resume from where you left off")
        except Exception as e:
            logger.error(f"❌ Scraping failed: {str(e)}")
            if scraper.scraped_data:
                scraper.save_checkpoint()
                print(f"💾 Progress saved despite error: {len(scraper.scraped_data)} pages")

if __name__ == "__main__":
    asyncio.run(main())