def lin(c):
    c = c/255
    return c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4

def lum(hexs):
    hexs = hexs.lstrip('#')
    r,g,b = int(hexs[0:2],16), int(hexs[2:4],16), int(hexs[4:6],16)
    return 0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b)

def ratio(a,b):
    la,lb = lum(a), lum(b)
    l1,l2 = max(la,lb), min(la,lb)
    return (l1+0.05)/(l2+0.05)

pairs = [
 ("dark bg vs muted text", "#0a0f0e", "#9fb6ae"),
 ("light bg vs muted text", "#f4faf6", "#4b5f56"),
 ("dark bg vs body text", "#0a0f0e", "#eaf3ef"),
 ("light bg vs body text", "#f4faf6", "#0f1b16"),
 ("dark surface vs muted", "#131c1a", "#9fb6ae"),
 ("primary ink on primary btn (dark)", "#4ef08c", "#04140b"),
 ("primary ink on primary btn (light)", "#1c9c56", "#ffffff"),
 ("accent on dark bg", "#0a0f0e", "#ff8a5c"),
 ("accent-2 on light bg", "#f4faf6", "#b8860a"),
]
for name,a,b in pairs:
    print(name, round(ratio(a,b),2))
