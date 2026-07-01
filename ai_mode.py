import asyncio
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

def ask_google_ai(query: str, timeout_ms: int = 120000) -> str:
    """
    Synchronous wrapper function that scrapes Google's AI Overview
    via a SOCKS5 Tor Proxy in Headless Mode using the Playwright Firefox engine.
    
    Default Tor Port: socks5://127.0.0.1:9050
    """
    
    async def _async_scraper(search_query: str) -> str:
        async with async_playwright() as p:
            
            # --- PROXY & HEADLESS CONFIGURATION ---
            # Using firefox as it provides superior native SOCKS5 routing under headless profiles
            browser = await p.firefox.launch(
                headless=False,  # Running in background mode
                proxy={
                    "server": "socks5://127.0.0.1:9050"  # Target local Tor service architecture
                }
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
            )
            page = await context.new_page()
            
            # Format and execute search query
            encoded_query = re.sub(r'\s+', '+', search_query.strip())
            target_url = f"https://google.com?q={encoded_query}&udm=50&hl=en&gl=us"
            
            try:
                # Direct navigation drops straight into the layout
                await page.goto(target_url, wait_until="domcontentloaded")
                
                # Give Google's asynchronous client-side JS time to inject the AI panel over Tor network
                await page.wait_for_timeout(timeout_ms)
                
                html_content = await page.content()
                await browser.close()
                
                # Parse the DOM structure using BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Verify if we hit a Google CAPTCHA wall (Common when using Tor)
                if soup.find('div', id='captcha-form') or "detected unusual traffic" in soup.get_text():
                    return "Blocked: Google served a CAPTCHA challenge due to Tor exit node IP reputation."
                
                # Heuristic 1: Scan for the text anchor marking the AIO block
                ai_heading = soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3', 'div'] and 'AI Overview' in tag.get_text())
                
                if not ai_heading:
                    return "No Google AI Overview block generated or visible for this query."
                
                # Traverse up to get the container scope
                ai_container = ai_heading.find_parent('div')
                for _ in range(5):
                    if ai_container and ('data-attrid' in ai_container.attrs or ai_container.find('svg')):
                        break
                    if ai_container:
                        ai_container = ai_container.find_parent('div')
                
                if not ai_container:
                    # Fallback Heuristic 2: Match recurring layout elements
                    ai_container = soup.find('div', class_='Kevs9') or soup.find('div', class_=re.compile(r'AI_Overview|AIO'))
                
                if not ai_container:
                    return "AI Overview detected, but layout container structure could not be parsed."
                
                # --- SANITIZE/CLEAN LAYER ---
                for style in ai_container.find_all('style'):
                    style.decompose()
                    
                for badge in ai_container.find_all(class_=list(re.compile(r'(wJwe6c|WTfRgd|citation|source)'))):
                    badge.decompose()
                    
                for link_block in ai_container.find_all('a'):
                    link_block.decompose()
                    
                for hidden in ai_container.find_all(attrs={"aria-hidden": "true"}):
                    hidden.decompose()

                # Extract content leaf blocks and construct clean paragraphs
                text_blocks = []
                text_elements = ai_container.find_all(['p', 'li', 'div', 'span'])
                
                for element in text_elements:
                    if element.string or (len(element.contents) == 1 and isinstance(element.contents, str)):
                        clean_chunk = element.get_text().strip()
                        if clean_chunk and clean_chunk not in text_blocks:
                            if not any(word in clean_chunk.lower() for word in ['show more', 'show less', 'feedback', 'ai overview']):
                                text_blocks.append(clean_chunk)
                
                final_text = "\n\n".join(text_blocks)
                return final_text if final_text.strip() else "Found container, but failed to isolate human-readable text strings."
                
            except Exception as e:
                await browser.close()
                return f"Error executing scraper execution: {str(e)}"
                
    return asyncio.run(_async_scraper(query))


# =====================================================================
# Production Testing Execution Block
# =====================================================================
if __name__ == "__main__":
    # Ensure your local Tor service/expert bundle is running on port 9050 before running
    result = {}
    query_string = "How does photosynthesis work summary"
    
    print(f"Calling ask_ai_mode over Tor Headless Proxy for query: '{query_string}'...")
    result["answer"] = ask_google_ai(query_string)
    
    print("\n" + "="*20 + " DICTIONARY OUTPUT " + "="*20)
    print(result["answer"])
    print("="*59)
