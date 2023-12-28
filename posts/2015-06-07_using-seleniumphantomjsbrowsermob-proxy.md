---
title: Using Selenium+PhantomJS+Browsermob-proxy for AJAX scraping
summary: On solution to capture HTTP response data in automated headless web scraping setup
---
Recently I needed to write a Python script which obtains data from AJAX traffic of a website with a very good anti-robot protection. [Selenium](https://pypi.python.org/pypi/selenium) with some browser (I prefer headless [PhantomJS](http://phantomjs.org/)) is usually good for such tasks, but in this case it was not enough: I needed raw AJAX data, not webpage contents after its JS processing, and server did not accept direct requests, even with cookies which I've got with Selenium. I tried to get traffic dump from the browser; PhantomJS can generate HAR dump, but it turned out that [it still misses support for capturing contents](https://github.com/ariya/phantomjs/issues/10158). Next idea was to use a capturing proxy; [Browsermob-proxy](http://bmp.lightbody.net/) came up as a good choice. It supports HAR, too, and can be easily controlled from Python script with [this module](https://pypi.python.org/pypi/browsermob-proxy/0.6.0), just like a browser with Selenium.
 
Here is the code example:

```
# Start proxy
from browsermobproxy import Server
server = Server('/path/to/browsermob-proxy')
server.start()
proxy = server.create_proxy()

# Start browser
import selenium.webdriver
browser = selenium.webdriver.PhantomJS('/path/to/phantomjs', service_args=['--proxy={0}'.format(proxy.proxy), '--ignore-ssl-errors=true'])

# Tell browser to open webapp page
browser.get('http://web.app/page/url')

# Tell proxy to start capture
proxy.new_har(options={'captureHeaders':True, 'captureContent':True})

# Tell browser to perform some actions which should cause AJAX requests
browser.find_element_by_id('some-input-id').send_keys('some input')

# Wait for end of transmission
# Ideally, this should be implemented as wating for some browser event
from time import sleep
sleep(10)

# Process results
for entry in proxy.har['log']['entries']:
    if entry['request']['url'] == 'http://web.app/ajax/endpoint/url':
        print(entry['response']['content']['text'])

# Shutdown
browser.quit()
server.stop()
```
