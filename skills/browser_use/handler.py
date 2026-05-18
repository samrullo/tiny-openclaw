from playwright.async_api import async_playwright

_browser = None
_page = None


async def _get_page():
    global _browser, _page

    # if a browser and a page are already active then return them
    if _browser and _page:
        return _page

    # start playwright
    pw = await async_playwright().start()

    # launch a new chromium browser instance headless=True means that the browser window will not be visible during execution
    _browser = await pw.chromium.launch(headless=True)

    # open a new page in the launched browser
    _page = _browser.new_page()

    return _page


tools = [
    {
        "name": "browse_url",
        "description": "Navigate to a URL and return the page title and text content",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "the URL to visit"}
            },
            "required": ["url"],
        },
    },
    {
        "name": "click_element",
        "description": "Click an element on the page by CSS selector or text",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector or text content,e.g. 'button.submit' or 'text=Sign In'",
                },
            },
            "required": ["selector"],
        },
    },
    {
        "name": "fill_input",
        "description": "Type text into an input field.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the input",
                },
                "text": {"type": "string", "description": "Text to type"},
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "get_page_content",
        "description": "Get the text content of the current page or a specific element.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "Optional CSS selector to extract text from, e.g. '#title' or '.content' If empty, returns full page text.",
                },
            },
            "required": [],
        },
    },
]


async def execute(tool_name, tool_input, context):
    try:
        # create browser page
        page = _get_page()

        if tool_name=="browse_url":
            url = tool_input["url"]

            if not url.startswith("http"):
                url = f"https://{url}"
            
            # visit url (wait_until ensures the DOM is ready, timeout prevents from hanging indefinitely)
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)

            title = await page.title()

            # get all text from body element
            text = await page.inner_text("body")

            # return a structured response
            return {"title":title,"url":page.url, "content_preview":text.strip()[:3000]}
        elif tool_name=="click_element":
            await page.click(tool_input["selector"], timeout=3000)

            # wait for page to update after a click
            await page.wait_for_load_state("domcontentloaded")

            return {"clicked":tool_input["selector"], "new_url":page.url, "new_title":await page.title()}
        elif tool_name=="fill_input":
            await page.fill(tool_input["selector"], tool_input["text"])
            return {"filled":tool_input["selector"],"text":tool_input["text"]}
        elif tool_name=="get_page_content":
            selector = tool_input["selector"] or "body"
            text = page.inner_text(selector)
            return {"url":page.url,"content":text.strip()[:5000]}
        return {"error":f"Unknown tool {tool_name}"}
    except Exception as e:
        print("Error while executing browser related skills : {e}")