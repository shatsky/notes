import os
import sys
import datetime
import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension

SOURCE_DIR = '.'
BUILD_DIR = sys.argv[1]
HEADER = '''
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-T3c6CoIi6uLrA9TneNEoa7RxnatzjcDSCmG1MXxSR1GAsXEV/Dwwykc2MPK8M2HN" crossorigin="anonymous">
  </head>
  <body>
    <div class="container py-5">
      <!--header end-->
'''
INDEX_HEADER = '''
      <p>I'm Eugene Shatsky, telecommunications&software engineer, FOSS&Linux enthusiast. This is my <s>blog</s> collection of Markdown notes (some big enough to be called articles), rendered as static HTML website (I prefer to take notes as Markdown files named `yyyy-mm-dd_title-slug`).</p>
'''
INDEX_POST = '''
      <a href="{post_url}"><h1>{post_title}</h1></a>
      <p>📅 {post_datetime}</p>
      <p>{post_summary}</p>
      <hr>
'''
POST_HEADER = '''
      <h1>{post_title}</h1>
      <p>📅 {post_datetime}</p>
      <p>{post_summary}</p>
'''
POST_FOOTER = '''
      <hr>
      <a href="index.html">Return to index</a>
'''
FOOTER = '''
    </div>
    <!--footer begin-->
  </body>
</html>
'''

assert BUILD_DIR
assert os.path.exists(BUILD_DIR)==False
os.mkdir(BUILD_DIR)
index_html_content_f = open(BUILD_DIR+'/index.html', 'w')
index_html_content_f.write(HEADER.format(title="My name is not Gde dizajn, it's Minimalism"))
#index_html_content_f.write(INDEX_HEADER)
for filename in reversed(sorted(os.listdir(SOURCE_DIR+'/posts'))):
    if not filename.endswith('.md'):
        continue
    filename_name = filename[:-3]
    post_datetime = filename[:len('yyyy-mm-dd')]
    post_md_content = open(SOURCE_DIR+'/posts/'+filename).read()
    _, post_md_content_frontmatter, post_md_content_body = post_md_content.split('---\n', 2)
    for post_md_content_frontmatter_line in post_md_content_frontmatter.split('\n'):
        if post_md_content_frontmatter_line.startswith('title: '):
            post_title = post_md_content_frontmatter_line[len('title: '):]
        if post_md_content_frontmatter_line.startswith('summary: '):
            post_summary = post_md_content_frontmatter_line[len('summary: '):]   
    index_html_content_f.write(INDEX_POST.format(post_url=filename_name+'.html', post_title=post_title, post_datetime=post_datetime, post_summary=post_summary))
    post_html_f = open(BUILD_DIR+'/'+filename_name+'.html', 'w')
    # TODO extract post title, date, substitute in header templ
    post_html_f.write(HEADER.format(title=post_title))
    post_html_f.write(POST_HEADER.format(post_title=post_title, post_datetime=post_datetime, post_summary=post_summary))
    # Problems with Markdown
    # - line breaks
    # - links
    # - strikethrough
    # - no lists, code blocks, tables, etc. within paragraph
    # - numeric lists starting with 1. even when different num used in src (ol has attr)
    # - characters unexpectedly interpreted
    post_html_content = markdown.markdown(post_md_content_body, extensions=[TableExtension(use_align_attribute=True), FencedCodeExtension()])
    post_html_content = post_html_content.replace('<table>', '<table class="table">')
    post_html_f.write(post_html_content)
    post_html_f.write(POST_FOOTER)
    post_html_f.write(FOOTER)
index_html_content_f.write(FOOTER)
