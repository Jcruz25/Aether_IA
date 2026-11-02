/**
 * Aether HUD - Renderizador 3D con Three.js
 * Orbe Cósmico / Reactor con anillos de partículas y respuesta al pulso
 */

let scene, camera, renderer;
let ringParticlesA, ringParticlesB, ringParticlesC;
let mysticCoreOuter, mysticCoreInner, backgroundStars;
let sparksParticles, sparkSpeeds, sparkLifespans;

let targetRotationX = 0, targetRotationY = 0;
let pulseMultiplier = 1.0;
let isMouseDown = false;
let previousMousePosition = { x: 0, y: 0 };

function initAetherUniverse() {
    const container = document.getElementById('aether-universe-container');
    if (!container) return;

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(60, 1, 0.1, 1000);
    camera.position.z = 5;

    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(540, 540);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Eventos de interacción con el ratón
    container.addEventListener('mousedown', (e) => {
        isMouseDown = true;
        previousMousePosition = { x: e.clientX, y: e.clientY };
        triggerPulse(2.5);
    });

    window.addEventListener('mouseup', () => { isMouseDown = false; });

    window.addEventListener('mousemove', (e) => {
        if (!isMouseDown) return;
        const deltaX = e.clientX - previousMousePosition.x;
        const deltaY = e.clientY - previousMousePosition.y;

        targetRotationY += deltaX * 0.006;
        targetRotationX += deltaY * 0.006;

        previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    // Colores
    const colorCyan = new THREE.Color(0x00f3ff);
    const colorViolet = new THREE.Color(0x8a2be2);
    const colorWhite = new THREE.Color(0xffffff);

    // Estrellas de fondo
    const starGeo = new THREE.BufferGeometry();
    const starCount = 350;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
        starPos[i] = (Math.random() - 0.5) * 12;
        starPos[i + 1] = (Math.random() - 0.5) * 12;
        starPos[i + 2] = (Math.random() - 0.5) * 12;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({
        size: 0.02,
        color: 0x00f3ff,
        transparent: true,
        opacity: 0.4
    });
    backgroundStars = new THREE.Points(starGeo, starMat);
    scene.add(backgroundStars);

    // Núcleo Místico Exterior
    const coreGeo = new THREE.IcosahedronGeometry(0.85, 2);
    const coreMat = new THREE.MeshBasicMaterial({
        color: colorCyan,
        wireframe: true,
        transparent: true,
        opacity: 0.35
    });
    mysticCoreOuter = new THREE.Mesh(coreGeo, coreMat);
    scene.add(mysticCoreOuter);

    // Núcleo Místico Interior
    const innerGeo = new THREE.IcosahedronGeometry(0.5, 3);
    const innerMat = new THREE.MeshBasicMaterial({
        color: colorViolet,
        wireframe: true,
        transparent: true,
        opacity: 0.6
    });
    mysticCoreInner = new THREE.Mesh(innerGeo, innerMat);
    scene.add(mysticCoreInner);

    // Anillo A (Cian)
    const ringCountA = 700;
    const ringGeoA = new THREE.BufferGeometry();
    const ringPosA = new Float32Array(ringCountA * 3);
    for (let i = 0; i < ringCountA; i++) {
        const theta = (i / ringCountA) * Math.PI * 2;
        const radius = 1.6 + (Math.random() - 0.5) * 0.12;
        ringPosA[i * 3] = Math.cos(theta) * radius;
        ringPosA[i * 3 + 1] = (Math.random() - 0.5) * 0.06;
        ringPosA[i * 3 + 2] = Math.sin(theta) * radius;
    }
    ringGeoA.setAttribute('position', new THREE.BufferAttribute(ringPosA, 3));
    const ringMatA = new THREE.PointsMaterial({
        size: 0.028,
        color: colorCyan,
        transparent: true,
        opacity: 0.75,
        blending: THREE.AdditiveBlending
    });
    ringParticlesA = new THREE.Points(ringGeoA, ringMatA);
    scene.add(ringParticlesA);

    // Anillo B (Violeta)
    const ringCountB = 600;
    const ringGeoB = new THREE.BufferGeometry();
    const ringPosB = new Float32Array(ringCountB * 3);
    for (let i = 0; i < ringCountB; i++) {
        const theta = (i / ringCountB) * Math.PI * 2;
        const radius = 2.0 + (Math.random() - 0.5) * 0.15;
        ringPosB[i * 3] = Math.cos(theta) * radius;
        ringPosB[i * 3 + 1] = Math.sin(theta) * radius;
        ringPosB[i * 3 + 2] = (Math.random() - 0.5) * 0.08;
    }
    ringGeoB.setAttribute('position', new THREE.BufferAttribute(ringPosB, 3));
    const ringMatB = new THREE.PointsMaterial({
        size: 0.03,
        color: colorViolet,
        transparent: true,
        opacity: 0.7,
        blending: THREE.AdditiveBlending
    });
    ringParticlesB = new THREE.Points(ringGeoB, ringMatB);
    ringParticlesB.rotation.x = Math.PI / 4;
    scene.add(ringParticlesB);

    // Anillo C (Inclinado)
    const ringCountC = 500;
    const ringGeoC = new THREE.BufferGeometry();
    const ringPosC = new Float32Array(ringCountC * 3);
    for (let i = 0; i < ringCountC; i++) {
        const theta = (i / ringCountC) * Math.PI * 2;
        const radius = 2.3 + (Math.random() - 0.5) * 0.2;
        ringPosC[i * 3] = (Math.random() - 0.5) * 0.1;
        ringPosC[i * 3 + 1] = Math.cos(theta) * radius;
        ringPosC[i * 3 + 2] = Math.sin(theta) * radius;
    }
    ringGeoC.setAttribute('position', new THREE.BufferAttribute(ringPosC, 3));
    const ringMatC = new THREE.PointsMaterial({
        size: 0.025,
        color: colorWhite,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending
    });
    ringParticlesC = new THREE.Points(ringGeoC, ringMatC);
    scene.add(ringParticlesC);

    // Destellos / Chispas
    const sparkCount = 80;
    const sparkGeo = new THREE.BufferGeometry();
    const sparkPos = new Float32Array(sparkCount * 3);
    const sparkCols = new Float32Array(sparkCount * 3);
    sparkSpeeds = [];
    sparkLifespans = [];

    for (let i = 0; i < sparkCount; i++) {
        sparkPos[i * 3] = 0;
        sparkPos[i * 3 + 1] = 0;
        sparkPos[i * 3 + 2] = 0;

        const speed = 0.015 + Math.random() * 0.03;
        const dir = new THREE.Vector3(
            Math.random() - 0.5,
            Math.random() - 0.5,
            Math.random() - 0.5
        ).normalize().multiplyScalar(speed);
        sparkSpeeds.push(dir);
        sparkLifespans.push(Math.random() * 2.0);

        let c = Math.random() > 0.3 ? colorCyan.clone() : colorWhite.clone();
        sparkCols[i * 3] = c.r;
        sparkCols[i * 3 + 1] = c.g;
        sparkCols[i * 3 + 2] = c.b;
    }

    sparkGeo.setAttribute('position', new THREE.BufferAttribute(sparkPos, 3));
    sparkGeo.setAttribute('color', new THREE.BufferAttribute(sparkCols, 3));

    const sparkMat = new THREE.PointsMaterial({
        size: 0.035,
        vertexColors: true,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    });

    sparksParticles = new THREE.Points(sparkGeo, sparkMat);
    scene.add(sparksParticles);

    animate();
}

function triggerPulse(intensity = 2.0) {
    pulseMultiplier = intensity;
}

function setHeadTrackingOffset(normX, normY) {
    if (!isMouseDown) {
        targetRotationY = normX * 0.7;
        targetRotationX = -normY * 0.45;
    }
}

function animate() {
    requestAnimationFrame(animate);

    const time = Date.now() * 0.0015;

    // Amortiguación de rotación
    scene.rotation.y += (targetRotationY - scene.rotation.y) * 0.08;
    scene.rotation.x += (targetRotationX - scene.rotation.x) * 0.08;

    // Pulso dinámico
    pulseMultiplier += (1.0 - pulseMultiplier) * 0.05;

    // Animación de chispas
    if (sparksParticles) {
        const positions = sparksParticles.geometry.attributes.position.array;
        for (let i = 0; i < sparkSpeeds.length; i++) {
            positions[i * 3] += sparkSpeeds[i].x * pulseMultiplier;
            positions[i * 3 + 1] += sparkSpeeds[i].y * pulseMultiplier;
            positions[i * 3 + 2] += sparkSpeeds[i].z * pulseMultiplier;

            sparkLifespans[i] += 0.005 * pulseMultiplier;

            const distSq = positions[i * 3]**2 + positions[i * 3 + 1]**2 + positions[i * 3 + 2]**2;
            if (distSq > 7.0 || sparkLifespans[i] > 2.5) {
                positions[i * 3] = 0;
                positions[i * 3 + 1] = 0;
                positions[i * 3 + 2] = 0;
                sparkLifespans[i] = 0;
            }
        }
        sparksParticles.geometry.attributes.position.needsUpdate = true;
    }

    if (backgroundStars) backgroundStars.rotation.y = time * 0.02;

    if (mysticCoreOuter) {
        mysticCoreOuter.rotation.y = time * 0.35;
        mysticCoreOuter.rotation.x = time * 0.2;
    }

    if (mysticCoreInner) {
        mysticCoreInner.rotation.y = -time * 0.45;
        const pulse = (1 + Math.sin(time * 3.5) * 0.08) * (pulseMultiplier > 1.4 ? 1.2 : 1.0);
        mysticCoreInner.scale.set(pulse, pulse, pulse);
    }

    if (ringParticlesA) ringParticlesA.rotation.y += 0.007;
    if (ringParticlesB) ringParticlesB.rotation.z -= 0.009;
    if (ringParticlesC) {
        ringParticlesC.rotation.y -= 0.005;
        ringParticlesC.rotation.x += 0.003;
    }

    if (renderer && scene && camera) {
        renderer.render(scene, camera);
    }
}

