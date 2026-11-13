# Prototipo de gráficos «nivel 2» (semirrealista)

Prueba técnica, separada del juego: **no la usa la web pública ni los reels** todavía. Sirve para decidir si
merece la pena pasar el mundo a gráficos semirrealistas.

- `index.html` + `escena.js`: valle con río, dos poblados prehistóricos iguales (marca verde y naranja), 10 personas
  animadas, zorros, hogueras, terreno y agua con texturas, cielo físico y sombras. Calidad automática (alta / media /
  baja) según lo que aguante el móvil, y medidor de FPS.
- Modo reel: `index.html?reel=1&plano=general|poblado|cerca&lado=A|B&dur=8`, con `window.paso(dt)` y `window.listo`,
  igual que la web real para `reels/fabrica.py`.
- `medir_reel.py`: graba 3 escenas de 8 s a 640x1136 y 24 fps con el mismo navegador y ajustes que la fábrica de reels,
  y dice cuántos segundos de servidor cuesta cada segundo de vídeo. Deja el vídeo en `/tmp/prueba_nivel2.mp4`.

```sh
cd /srv/miovsnuestro && sudo -u mvn .venv/bin/python prototipo/medir_reel.py
```

## Material y licencias
- Personas: muestras de [Dramatis](https://github.com/tonioloewald/dramatis3d) hechas con MakeHuman (CC0). La ropa
  original (traje, chándal) se recolorea en el código como cuero: es provisional.
- Animación de andar: Universal Animation Library de Quaternius (CC0). La postura de pie y la de sentado salen de ella.
- Zorro: glTF Sample Assets de Khronos (CC0 / CC-BY 4.0, PixelMannen y tomkranis).
- three.js r160 y sus módulos (MIT). Texturas de hierba y agua: de los ejemplos de three.js; en la versión final se cambian por texturas CC0 (Poly Haven).
- Árboles, rocas, chozas, hoguera, lanzas, secadero y banderines: hechos con código.
