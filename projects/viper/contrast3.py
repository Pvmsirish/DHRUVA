import contrast as c
print("light muted text vs bg", round(c.ratio("#f4faf6","#45594f"),2))
print("light primary text (link) vs bg", round(c.ratio("#f4faf6","#0e6234"),2))
print("light primary-ink on primary btn", round(c.ratio("#0e6234","#ffffff"),2))
print("light accent-2 vs bg", round(c.ratio("#f4faf6","#8a6207"),2))
print("light accent vs bg", round(c.ratio("#f4faf6","#c14a1c"),2))
