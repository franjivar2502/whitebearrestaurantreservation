/*
 * Fondo del sitio: un shader WebGL escrito a mano (sin Three.js ni ninguna
 * librería -- son ~4KB en vez de ~600KB, y en el plan gratis de Render cada
 * KB cuenta en el arranque en frío).
 *
 * Dibuja un amanecer brumoso en los Adirondacks: las cordilleras alejándose
 * en capas cada vez más pálidas y bancos de niebla que se desplazan muy
 * despacio. Nada más.
 *
 * La versión anterior tenía aurora boreal y estrellas sobre cielo negro, y
 * eso es lo que hacía que el sitio pareciera un local nocturno. Los
 * restaurantes de lujo de la zona (Mirror Lake Inn, Lake Placid Lodge) y las
 * referencias de alta cocina no ponen luces de colores detrás del contenido:
 * el fondo es un papel cálido y casi plano, y el color fuerte viene de las
 * fotos del restaurante. Esto es eso, con relieve.
 *
 * Si el navegador no soporta WebGL, no hace nada: el marfil del body queda
 * como fondo y el sitio se ve bien igual.
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

      // Cielo: marfil cálido arriba que se abre a un gris verdoso muy claro
      // sobre el horizonte. El rango total de luminosidad es estrecho a
      // propósito: el fondo tiene que leerse como papel, no como una imagen.
      vec3 col = mix(vec3(0.945, 0.935, 0.915), vec3(0.972, 0.965, 0.952), uv.y);

      // Cuatro cordilleras. Cada una está más lejos y, por perspectiva aérea,
      // más cerca del color del cielo: eso es lo que da la profundidad.
      vec3 far   = vec3(0.855, 0.868, 0.852);
      vec3 mid   = vec3(0.790, 0.812, 0.788);
      vec3 near  = vec3(0.712, 0.742, 0.710);
      vec3 front = vec3(0.628, 0.666, 0.624);

      float r1 = ridge(uv.x * 0.7 + 7.3, 23.0, 0.30);
      float r2 = ridge(uv.x * 0.9 + 3.1, 11.0, 0.235);
      float r3 = ridge(uv.x * 1.1 + 1.7, 47.0, 0.165);
      float r4 = ridge(uv.x * 1.4 + 9.2, 61.0, 0.085);

      if (uv.y < r1) col = mix(col, far, 0.75);
      if (uv.y < r2) col = mix(col, mid, 0.78);
      if (uv.y < r3) col = mix(col, near, 0.80);
      if (uv.y < r4) col = mix(col, front, 0.82);

      // Bancos de niebla: franjas horizontales de ruido que cruzan muy
      // despacio y aclaran la base de cada cordillera, como en la montaña a
      // primera hora.
      for (int i = 0; i < 3; i++) {
        float fi = float(i);
        float band = fbm(vec2(uv.x * 1.6 + t * (0.012 + fi * 0.006) + fi * 17.0,
                              uv.y * 3.0 + fi * 5.0));
        float centre = 0.26 - fi * 0.07;
        float width = 0.085 + fi * 0.02;
        float shape = smoothstep(width, 0.0, abs(uv.y - centre - band * 0.045));
        col = mix(col, vec3(0.975, 0.970, 0.958), shape * (0.52 - fi * 0.1));
      }

      // Calidez muy leve en el centro, para que el marfil no se vea plano.
      float warm = smoothstep(0.95, 0.1, length((uv - vec2(0.5, 0.62)) * vec2(1.0, 1.4)));
      col += vec3(0.020, 0.013, 0.004) * warm;

      gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
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
