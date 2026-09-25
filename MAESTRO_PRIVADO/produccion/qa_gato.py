# Valida que cada partida de gato dibujada en recados.html sea posible: turnos alternos, sin casillas repetidas,
# sin tiros después de ganar y con la raya sobre la línea ganadora. Uso: python3 qa_gato.py fuentes_html/recados.html
import re,sys
src=open(sys.argv[1]).read()
L=[[(0,0),(0,1),(0,2)],[(1,0),(1,1),(1,2)],[(2,0),(2,1),(2,2)],[(0,0),(1,0),(2,0)],[(0,1),(1,1),(2,1)],[(0,2),(1,2),(2,2)],[(0,0),(1,1),(2,2)],[(0,2),(1,1),(2,0)]]
malas = 0
for m in re.finditer(r"G\((\d+), (\d+), \d+, (\[\[.*?\]\])(?:, '([io])'(?:, \[\[(\d), (\d)\], \[(\d), (\d)\]\])?)?\)",src):
    moves=re.findall(r"\[(\d), (\d), '([OX])', '([io])'\]",m.group(3))
    b={}; prev=None; ok=True; winner=None; msg=[]
    for i,(r,c,mk,w) in enumerate(moves):
        r,c=int(r),int(c)
        if winner: msg.append('tiro después de ganar'); ok=False
        if (r,c) in b: msg.append('casilla repetida'); ok=False
        if prev==mk: msg.append('tiro doble %s'%mk); ok=False
        b[(r,c)]=mk; prev=mk
        for l in L:
            if all(b.get(p)==mk for p in l): winner=(mk,l)
    decl=None
    if m.group(5): decl=((int(m.group(5)),int(m.group(6))),(int(m.group(7)),int(m.group(8))))
    if decl:
        if not winner or (decl[0] not in winner[1] or decl[1] not in winner[1]): msg.append('raya no coincide con ganador %s'%(winner,)); ok=False
    malas += 0 if ok else 1
    print(f'partida en ({m.group(1)},{m.group(2)}):', 'OK' if ok else 'MAL', 'gana '+winner[0] if winner else ('empate' if len(moves)==9 else 'en juego'), ' '.join(msg))
print('partidas imposibles:', malas)
