import re
html = open('index.html', encoding='utf-8').read()
html = re.sub(r'<script.*?</script>', '', html, flags=re.S)
html = re.sub(r'<style.*?</style>', '', html, flags=re.S)
text = re.sub(r'<[^>]+>', ' ', html)
words = text.split()
print("word count:", len(words))
