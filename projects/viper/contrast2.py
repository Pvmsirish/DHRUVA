import contrast as c
candidates = ["#1c9c56","#178048","#146e3d","#0f7a41","#116b39","#0e6234"]
for hexv in candidates:
    print(hexv, round(c.ratio(hexv, "#ffffff"),2))
