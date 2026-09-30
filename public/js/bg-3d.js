/*
 * Fondo 3D del sitio de clientes: un shader WebGL escrito a mano (sin
 * Three.js ni ninguna librería -- son ~4KB en vez de ~600KB, y en el plan
 * gratis de Render cada KB cuenta en el arranque en frío).
 *
 * Dibuja una noche en Lake Placid: aurora boreal sobre la silueta de las
 * montañas, estrellas y nieve cayendo. Los colores salen de la marca real
 * del restaurante (borgoña y verde bosque) sobre azul noche.
 *
 * Si el navegador no soporta WebGL, no hace nada: el degradado CSS que ya
 * tiene el body queda como fondo y el sitio se ve bien igual.
 */
(function () {
  const canvas = document.getElementById("bg-3d");
  if (!canvas) return;

  const gl = canvas.getContext("webgl", { antialias: false, alpha: true });
  if (!gl) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const VERT = `
    attribute vec2 position;
    void main() { gl_Position = vec4(position, 0.0, 1.0); }
  `;

  const FRAG = `
    precision mediump float;
    uniform vec2 u_res;
    uniform float u_time;

    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
    }

    float noise(vec2 p) {
      vec2 i = floor(p);
      vec2 f = fract(p);
      f = f * f * (3.0 - 2.0 * f);
      float a = hash(i);
      float b = hash(i + vec2(1.0, 0.0));
      float c = hash(i + vec2(0.0, 1.0));
      float d = hash(i + vec2(1.0, 1.0));
      return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
    }

    float fbm(vec2 p) {
      float v = 0.0;
      float amp = 0.5;
      for (int i = 0; i < 5; i++) {
        v += amp * noise(p);
        p *= 2.02;
        amp *= 0.5;
      }
      return v;
    }

    // Silueta de montaña procedural
    float ridge(float x, float seed, float height) {
      float h = fbm(vec2(x * 1.8 + seed, seed));
      return height + h * 0.16;
    }

    void main() {
      vec2 uv = gl_FragCoord.xy / u_res.xy;
      float t = u_time;

      // Cielo: azul noche profundo, más oscuro abajo
      vec3 col = mix(vec3(0.016, 0.026, 0.063), vec3(0.035, 0.047, 0.11), uv.y);

      // Estrellas (solo en la mitad superior, se desvanecen hacia abajo)
      vec2 sp = gl_FragCoord.xy / max(u_res.y, 1.0);
      vec2 cell = floor(sp * 140.0);
      float star = hash(cell);
      if (star > 0.985) {
        float twinkle = 0.55 + 0.45 * sin(t * 1.6 + star * 90.0);
        float fade = smoothstep(0.18, 0.85, uv.y);
        col += vec3(0.85, 0.9, 1.0) * twinkle * fade * 0.5;
      }

      // Aurora: bandas de ruido que fluyen, en verde bosque y borgoña
      float aur = 0.0;
      for (int i = 0; i < 3; i++) {
        float fi = float(i);
        float band = fbm(vec2(uv.x * 2.4 + t * (0.05 + fi * 0.02) + fi * 4.0, uv.y * 1.4 - t * 0.03));
        float centre = 0.68 - fi * 0.07;
        float width = 0.16 + fi * 0.03;
        float shape = smoothstep(width, 0.0, abs(uv.y - centre - band * 0.16));
        aur += shape * (0.5 - fi * 0.12);
      }
      float auroraFade = smoothstep(0.32, 0.95, uv.y);
      vec3 auroraCol = mix(vec3(0.29, 0.40, 0.25), vec3(0.48, 0.14, 0.19), 0.35 + 0.35 * sin(uv.x * 2.2 + t * 0.18));
      col += auroraCol * aur * auroraFade * 1.15;

      // Resplandor cálido en el horizonte (las luces del restaurante)
      float glow = smoothstep(0.42, 0.0, abs(uv.y - 0.20)) * smoothstep(1.0, 0.25, abs(uv.x - 0.5) * 1.7);
      col += vec3(0.88, 0.64, 0.20) * glow * 0.14;

      // Montañas: dos capas para dar profundidad
      float far = ridge(uv.x + 3.1, 11.0, 0.20);
      float near = ridge(uv.x * 0.8, 47.0, 0.11);
      if (uv.y < far) col = mix(col, vec3(0.045, 0.055, 0.10), 0.88);
      if (uv.y < near) col = mix(col, vec3(0.020, 0.026, 0.050), 0.94);

      // Nieve cayendo (tres capas a distinta velocidad = profundidad)
      for (int i = 0; i < 3; i++) {
        float fi = float(i);
        float scale = 26.0 + fi * 18.0;
        float speed = 0.035 + fi * 0.022;
        vec2 gp = vec2(uv.x * scale, uv.y * scale + t * speed * scale);
        vec2 gi = floor(gp);
        vec2 gf = fract(gp);
        float rnd = hash(gi + fi * 31.0);
        if (rnd > 0.965) {
          vec2 centre = vec2(0.5 + 0.28 * sin(t * 0.7 + rnd * 40.0), 0.5);
          float d = length(gf - centre);
          float flake = smoothstep(0.13 - fi * 0.02, 0.0, d);
          col += vec3(0.92, 0.95, 1.0) * flake * (0.42 - fi * 0.1);
        }
      }

      // Viñeta suave para que el contenido de arriba respire
      float vig = smoothstep(1.25, 0.25, length(uv - vec2(0.5, 0.55)));
      col *= 0.62 + 0.38 * vig;

      gl_FragColor = vec4(col, 1.0);
    }
  `;

  function compile(type, src) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, src);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  }

  const vs = compile(gl.VERTEX_SHADER, VERT);
  const fs = compile(gl.FRAGMENT_SHADER, FRAG);
  if (!vs || !fs) return;

  const program = gl.createProgram();
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;
  gl.useProgram(program);

  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const posLoc = gl.getAttribLocation(program, "position");
  gl.enableVertexAttribArray(posLoc);
  gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

  const uRes = gl.getUniformLocation(program, "u_res");
  const uTime = gl.getUniformLocation(program, "u_time");

  function resize() {
    // Se renderiza a media resolución: el shader es suave, nadie nota la
    // diferencia, y baja mucho el costo en celulares.
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5) * 0.7;
    const w = Math.floor(window.innerWidth * dpr);
    const h = Math.floor(window.innerHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      gl.viewport(0, 0, w, h);
    }
  }

  function draw(timeMs) {
    resize();
    gl.uniform2f(uRes, canvas.width, canvas.height);
    gl.uniform1f(uTime, timeMs * 0.001);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  if (reduceMotion) {
    // Sin animación: un solo fotograma fijo, igual de bonito y sin movimiento.
    draw(8000);
    window.addEventListener("resize", () => draw(8000));
    return;
  }

  let running = true;
  function loop(ts) {
    if (!running) return;
    draw(ts);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);

  // No gastar batería ni GPU cuando la pestaña no está visible.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      running = false;
    } else if (!running) {
      running = true;
      requestAnimationFrame(loop);
    }
  });
})();
