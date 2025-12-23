import os
import sys
import datetime
import subprocess

SOURCE_DIR = '.'
BUILD_DIR = sys.argv[1]
BRANCH = sys.argv[2] if len(sys.argv)>2 else None
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
      <p>DISCLAIMER: these notes reflect my knowledge and understanding of subjects, not the ultimate truth. Most are written in process of learning things. Corrections are welcome</p>
      <hr>
      <!--header end-->
'''
INDEX_HEADER = '''
      <p>I'm Eugene Shatsky, telecommunications&software engineer, FOSS&Linux enthusiast. This is my <s>blog</s> collection of Markdown notes (some big enough to be called articles), rendered as static HTML website (I prefer to take notes as Markdown files named `yyyy-mm-dd_title-slug`).</p>
'''
INDEX_POST = '''
      <a href="{post_url}"><h1>{post_title}</h1></a>
      <p>📅 {post_datetime} <a href="{source_url}">📄 source</a></p>
      <p>{post_summary}</p>
      <hr>
'''
POST_HEADER = '''
      <h1>{post_title}</h1>
      <p>📅 {post_datetime} <a href="{source_url}">📄 source</a></p>
      <p>{post_summary}</p>
'''
POST_FOOTER = '''
      <hr>
      <p>Comments are not implemented, but you can create issue on GitHub or check existing ones</p>
      <a href="index.html">Return to index</a>
'''
FOOTER = '''
    </div>
    <!--footer begin-->
  </body>
</html>
'''

# quick&dirty markdown preprocess function to turn urls into links
# TODO do this properly after html rendering (html markup inside <code>/<pre> blocks is interpreted as usual)
def preprocess(md_content):
    multiline_parts = md_content.split('```')
    flag_multiline_code = True
    for multiline_part_i in range(len(multiline_parts)):
        if not (multiline_part_i>0 and multiline_parts[multiline_part_i-1].endswith('\\')):
            flag_multiline_code = not flag_multiline_code
        if flag_multiline_code:
            continue
        lines = multiline_parts[multiline_part_i].split('\n')
        for line_i in range(len(lines)):
            inline_parts = lines[line_i].split('`')
            flag_inline_code = True
            for inline_part_i in range(len(inline_parts)):
                if not (inline_part_i>0 and inline_parts[inline_part_i-1].endswith('\\')):
                    flag_inline_code = not flag_inline_code
                if flag_inline_code:
                    continue
                words = inline_parts[inline_part_i].split(' ')
                for word_i in range(len(words)):
                    if words[word_i].startswith('http://') or words[word_i].startswith('https://'):
                        words[word_i] = '[' + words[word_i] + '](' + words[word_i] + ')'
                inline_parts[inline_part_i] = ' '.join(words)
            lines[line_i] = '`'.join(inline_parts)
        multiline_parts[multiline_part_i] = '\n'.join(lines)
    md_content = '```'.join(multiline_parts)
    return md_content

assert BUILD_DIR
assert os.path.exists(BUILD_DIR)==False
os.mkdir(BUILD_DIR)
index_html_content_f = open(BUILD_DIR+'/index.html', 'w')
index_html_content_f.write(HEADER.format(title="My name is not Gde dizajn, it's Minimalism"))
#index_html_content_f.write(INDEX_HEADER)
post_md_filenames = (
    reversed(sorted(os.listdir(SOURCE_DIR+'/src'))) if BRANCH is None
    else reversed(sorted([path[len('src/'):] for path in subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BRANCH]).decode().split('\n')
                          if path.startswith('src/')])))
for post_md_filename in post_md_filenames:
    if not post_md_filename:
        continue
    print(post_md_filename)
    if not post_md_filename.endswith('.md'):
        continue
    filename_name = post_md_filename[:-3]
    post_datetime = post_md_filename[:len('yyyy-mm-dd')]
    post_md_content = (open(SOURCE_DIR+'/src/'+post_md_filename).read() if BRANCH is None
        else subprocess.check_output(['git', 'show', BRANCH+':src/'+post_md_filename]).decode())
    if not post_md_content.startswith('---'):
        continue
    _, post_md_content_frontmatter, post_md_content_body = post_md_content.split('---\n', 2)
    for post_md_content_frontmatter_line in post_md_content_frontmatter.split('\n'):
        if post_md_content_frontmatter_line.startswith('title: '):
            post_title = post_md_content_frontmatter_line[len('title: '):]
        if post_md_content_frontmatter_line.startswith('summary: '):
            post_summary = post_md_content_frontmatter_line[len('summary: '):]
    index_html_content_f.write(INDEX_POST.format(post_url=filename_name+'.html', post_title=post_title, post_datetime=post_datetime, source_url='https://github.com/shatsky/notes/blob/main/src/'+post_md_filename, post_summary=post_summary))
    post_html_f = open(BUILD_DIR+'/'+filename_name+'.html', 'w')
    # TODO extract post title, date, substitute in header templ
    post_html_f.write(HEADER.format(title=post_title))
    post_html_f.write(POST_HEADER.format(post_title=post_title, post_datetime=post_datetime, source_url='https://github.com/shatsky/notes/blob/main/src/'+post_md_filename, post_summary=post_summary))
    # Problems with Python-Markdown
    # - line breaks
    # - links
    # - strikethrough
    # - no lists, code blocks, tables, etc. within paragraph
    # - numeric lists starting with 1. even when different num used in src (ol has attr)
    # - characters unexpectedly interpreted
    post_md_content_body = preprocess(post_md_content_body)
    post_html_content = subprocess.run('cmark-gfm -e table -e strikethrough --hardbreaks'.split(' '), input=post_md_content_body.encode(), capture_output=True).stdout.decode()
    post_html_content = post_html_content.replace('<table>', '<table class="table">')
    post_html_f.write(post_html_content)
    post_html_f.write(POST_FOOTER)
    post_html_f.write(FOOTER)
index_html_content_f.write(FOOTER)
