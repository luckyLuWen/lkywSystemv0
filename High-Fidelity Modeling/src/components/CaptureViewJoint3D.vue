<template>
  <section class="joint-view" aria-label="UAV 与 UGV 联合视角三维示意">
    <div ref="sceneHost" class="joint-scene-host">
      <div v-if="renderError" class="joint-scene-error">{{ renderError }}</div>
    </div>
  </section>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

const props = defineProps({
  uavCount: { type: Number, default: 0 },
  ugvCount: { type: Number, default: 0 },
  vehicleType: { type: String, default: 'generic' }
})

const sceneHost = ref(null)
const renderError = ref('')
let scene = null
let camera = null
let renderer = null
let controls = null
let resizeObserver = null
let animationFrameId = null
let contentSphere = null
let fittedDistance = 0

const makeMaterial = (color, roughness = 0.7, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness, ...extra })

const addOrbit = (radius, height, color, markerCount) => {
  const points = Array.from({ length: 80 }, (_, index) => {
    const angle = index / 80 * Math.PI * 2
    return new THREE.Vector3(Math.cos(angle) * radius, height, Math.sin(angle) * radius)
  })
  const orbit = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineDashedMaterial({ color, dashSize: 0.25, gapSize: 0.16, transparent: true, opacity: 0.75 })
  )
  orbit.computeLineDistances()
  scene.add(orbit)

  const markerGeometry = new THREE.SphereGeometry(0.085, 10, 8)
  const markerMaterial = new THREE.MeshBasicMaterial({ color })
  for (let index = 0; index < markerCount; index += 1) {
    const angle = index / markerCount * Math.PI * 2
    const marker = new THREE.Mesh(markerGeometry, markerMaterial)
    marker.position.set(Math.cos(angle) * radius, height, Math.sin(angle) * radius)
    scene.add(marker)
  }
}

const addCameraFrustum = (position, target, color, reach = 2.2) => {
  const halfWidth = reach * 0.34
  const halfHeight = reach * 0.24
  const corners = [
    new THREE.Vector3(-halfWidth, -halfHeight, -reach),
    new THREE.Vector3(halfWidth, -halfHeight, -reach),
    new THREE.Vector3(halfWidth, halfHeight, -reach),
    new THREE.Vector3(-halfWidth, halfHeight, -reach)
  ]
  const tip = new THREE.Vector3(0, 0, 0)
  const fillGeometry = new THREE.BufferGeometry().setFromPoints([tip, ...corners])
  fillGeometry.setIndex([0, 1, 2, 0, 2, 3, 0, 3, 4, 0, 4, 1])
  fillGeometry.computeVertexNormals()

  const frustum = new THREE.Group()
  frustum.add(new THREE.Mesh(fillGeometry, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.08, side: THREE.DoubleSide, depthWrite: false })))
  const edgePoints = [
    tip, corners[0], tip, corners[1], tip, corners[2], tip, corners[3],
    corners[0], corners[1], corners[1], corners[2], corners[2], corners[3], corners[3], corners[0]
  ]
  frustum.add(new THREE.LineSegments(
    new THREE.BufferGeometry().setFromPoints(edgePoints),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.8 })
  ))
  frustum.position.copy(position)
  frustum.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, -1), target.clone().sub(position).normalize())
  scene.add(frustum)
}

const createDroneCamera = (position, target, color) => {
  const drone = new THREE.Group()
  drone.position.copy(position)
  drone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, -1), target.clone().sub(position).normalize())
  drone.add(new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.16, 0.34), makeMaterial(0xe5f5fb, 0.38)))

  for (const xDirection of [-1, 1]) {
    for (const zDirection of [-1, 1]) {
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.045, 0.045), makeMaterial(0x9ab0bf, 0.5))
      arm.position.set(xDirection * 0.27, 0, zDirection * 0.25)
      arm.rotation.y = xDirection === zDirection ? Math.PI / 4 : -Math.PI / 4
      drone.add(arm)

      const rotor = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.025, 16), makeMaterial(color, 0.45, { transparent: true, opacity: 0.68 }))
      rotor.position.set(xDirection * 0.52, 0.04, zDirection * 0.45)
      drone.add(rotor)
    }
  }

  drone.add(new THREE.Mesh(new THREE.SphereGeometry(0.095, 12, 10), makeMaterial(color, 0.35)))
  scene.add(drone)
  addCameraFrustum(position.clone().add(new THREE.Vector3(0, -0.18, 0)), target, color, 2.6)
}

const createGroundCamera = (position, target, color) => {
  const rig = new THREE.Group()
  rig.position.copy(position)
  rig.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, -1), target.clone().sub(position).normalize())

  const chassis = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.25, 0.54), makeMaterial(0xc8d7df, 0.5))
  chassis.position.y = 0.28
  rig.add(chassis)
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.05, 0.46, 10), makeMaterial(0x91a6b4, 0.5))
  mast.position.y = 0.62
  rig.add(mast)
  const cameraBody = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.2, 0.2), makeMaterial(color, 0.4))
  cameraBody.position.set(0, 0.89, -0.02)
  rig.add(cameraBody)
  const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.065, 0.11, 12), makeMaterial(0x152430, 0.2))
  lens.rotation.x = Math.PI / 2
  lens.position.set(0, 0.89, -0.16)
  rig.add(lens)

  for (const x of [-0.27, 0.27]) {
    for (const z of [-0.3, 0.3]) {
      const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.1, 12), makeMaterial(0x25333d, 0.9))
      wheel.rotation.x = Math.PI / 2
      wheel.position.set(x, 0.16, z)
      rig.add(wheel)
    }
  }
  scene.add(rig)
  addCameraFrustum(position.clone().add(new THREE.Vector3(0, 1.0, 0)), target, color, 2.4)
}

const createVehicle = (vehicleType) => {
  const vehicle = new THREE.Group()
  if (vehicleType === 'oil-tanker') {
    const chassis = new THREE.Mesh(new THREE.BoxGeometry(4.35, 0.34, 1.12), makeMaterial(0x5a6470, 0.72))
    chassis.position.y = 0.66
    vehicle.add(chassis)

    const tank = new THREE.Mesh(new THREE.CylinderGeometry(0.61, 0.61, 3.25, 32), makeMaterial(0xc98b4b, 0.45, { metalness: 0.18 }))
    tank.rotation.z = Math.PI / 2
    tank.position.set(-0.28, 1.42, 0)
    vehicle.add(tank)
    for (const x of [-1.28, -0.28, 0.72]) {
      const band = new THREE.Mesh(new THREE.TorusGeometry(0.61, 0.035, 8, 24), makeMaterial(0xe2b16d, 0.4, { metalness: 0.22 }))
      band.rotation.y = Math.PI / 2
      band.position.set(x, 1.42, 0)
      vehicle.add(band)
    }

    const cab = new THREE.Mesh(new THREE.BoxGeometry(1.05, 1.12, 1.16), makeMaterial(0xb56835, 0.48))
    cab.position.set(1.62, 1.12, 0)
    vehicle.add(cab)
    const windshield = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.5, 0.88), makeMaterial(0x243e4b, 0.25, { metalness: 0.12 }))
    windshield.position.set(2.16, 1.36, 0)
    vehicle.add(windshield)

    for (const side of [-1, 1]) {
      for (const x of [-1.36, 0.55, 1.62]) {
        const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.31, 0.31, 0.16, 16), makeMaterial(0x26323a, 0.92))
        wheel.rotation.x = Math.PI / 2
        wheel.position.set(x, 0.35, side * 0.68)
        vehicle.add(wheel)
      }
    }
  } else if (vehicleType === 'coach') {
    const body = new THREE.Mesh(new THREE.BoxGeometry(4.1, 1.2, 1.35), makeMaterial(0xd4e2e8, 0.48))
    body.position.y = 1.0
    vehicle.add(body)

    const roof = new THREE.Mesh(new THREE.BoxGeometry(3.75, 0.16, 1.23), makeMaterial(0xe6eff3, 0.4))
    roof.position.y = 1.68
    vehicle.add(roof)

    const windows = makeMaterial(0x273d4a, 0.24, { metalness: 0.12 })
    for (const side of [-1, 1]) {
      const windowStrip = new THREE.Mesh(new THREE.BoxGeometry(3.25, 0.48, 0.035), windows)
      windowStrip.position.set(-0.03, 1.39, side * 0.69)
      vehicle.add(windowStrip)
      for (const x of [-1.35, 1.35]) {
        const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.16, 18), makeMaterial(0x26323a, 0.92))
        wheel.rotation.x = Math.PI / 2
        wheel.position.set(x, 0.36, side * 0.72)
        vehicle.add(wheel)
      }
    }
  } else {
    const target = new THREE.Mesh(new THREE.BoxGeometry(2.8, 1.05, 1.65), makeMaterial(0x8395a2, 0.62))
    target.position.y = 0.72
    vehicle.add(target)
    const top = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.12, 1.1), makeMaterial(0xb9c7ce, 0.5))
    top.position.y = 1.31
    vehicle.add(top)
    for (const x of [-0.9, 0.9]) {
      for (const side of [-1, 1]) {
        const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 0.14, 16), makeMaterial(0x26323a, 0.92))
        wheel.rotation.x = Math.PI / 2
        wheel.position.set(x, 0.3, side * 0.83)
        vehicle.add(wheel)
      }
    }
  }
  scene.add(vehicle)
}

const resizeScene = () => {
  if (!sceneHost.value || !renderer || !camera) return
  const width = Math.max(sceneHost.value.clientWidth, 1)
  const height = Math.max(sceneHost.value.clientHeight, 1)
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  if (contentSphere && controls) {
    const halfVerticalFov = THREE.MathUtils.degToRad(camera.fov / 2)
    const halfHorizontalFov = Math.atan(Math.tan(halfVerticalFov) * camera.aspect)
    const distance = contentSphere.radius * 1.08 / Math.sin(Math.min(halfVerticalFov, halfHorizontalFov))
    const direction = camera.position.clone().sub(controls.target).normalize()
    const zoomRatio = fittedDistance ? camera.position.distanceTo(controls.target) / fittedDistance : 1
    controls.maxDistance = Math.max(24, distance * 2)
    camera.position.copy(controls.target).addScaledVector(direction, Math.max(controls.minDistance, Math.min(controls.maxDistance, distance * zoomRatio)))
    camera.far = Math.max(80, distance * 6)
    scene.fog.near = distance * 1.1
    scene.fog.far = distance * 3
    fittedDistance = distance
    controls.update()
  }
  camera.updateProjectionMatrix()
}

const renderFrame = () => {
  if (!renderer || !scene || !camera) return
  controls?.update()
  renderer.render(scene, camera)
  animationFrameId = requestAnimationFrame(renderFrame)
}

const initScene = () => {
  const host = sceneHost.value
  if (!host) return
  try {
    scene = new THREE.Scene()
    scene.background = new THREE.Color(0x081421)
    scene.fog = new THREE.Fog(0x081421, 14, 32)
    camera = new THREE.PerspectiveCamera(42, 1, 0.1, 80)
    camera.position.set(12, 9, 12)

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.05
    renderer.domElement.setAttribute('aria-label', 'UAV 与 UGV 相机联合视角三维示意图')
    host.appendChild(renderer.domElement)

    controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(0, 1, 0)
    controls.enableDamping = true
    controls.dampingFactor = 0.07
    controls.minDistance = 7
    controls.maxDistance = 24
    controls.maxPolarAngle = Math.PI * 0.48

    scene.add(new THREE.HemisphereLight(0xc4e2f4, 0x14212b, 1.7))
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.1)
    keyLight.position.set(6, 10, 7)
    scene.add(keyLight)
    const grid = new THREE.GridHelper(20, 20, 0x31536a, 0x1c3040)
    grid.position.y = 0.005
    scene.add(grid)

    createVehicle(props.vehicleType)
    const uavColor = 0x46d7ef
    const ugvColor = 0xf3bd68
    addOrbit(6.2, 5.5, uavColor, Math.max(3, Math.min(18, Math.round(Math.sqrt(props.uavCount || 1)))))
    addOrbit(5.2, 1.0, ugvColor, Math.max(3, Math.min(14, Math.round(Math.sqrt(props.ugvCount || 1)))))
    createDroneCamera(new THREE.Vector3(-4.1, 5.5, 4.6), new THREE.Vector3(0, 0.8, 0), uavColor)
    createGroundCamera(new THREE.Vector3(0.6, 0, 5.0), new THREE.Vector3(0, 1.0, 0), ugvColor)

    // Fit the vehicle, camera rigs and complete paths, excluding the decorative ground grid.
    const contentBounds = new THREE.Box3()
    scene.children.filter(object => !object.isLight && object !== grid).forEach(object => contentBounds.expandByObject(object))
    contentSphere = contentBounds.getBoundingSphere(new THREE.Sphere())
    controls.target.copy(contentSphere.center)

    resizeObserver = new ResizeObserver(resizeScene)
    resizeObserver.observe(host)
    resizeScene()
    renderFrame()
  } catch {
    renderError.value = '当前浏览器无法启用交互三维视角。'
    resizeObserver?.disconnect()
    controls?.dispose()
    scene?.traverse(object => {
      object.geometry?.dispose()
      if (Array.isArray(object.material)) object.material.forEach(material => material.dispose())
      else object.material?.dispose()
    })
    scene = null
    renderer?.dispose()
    renderer?.domElement?.remove()
    renderer = null
    controls = null
    resizeObserver = null
  }
}

onMounted(async () => {
  await nextTick()
  initScene()
})

onBeforeUnmount(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  resizeObserver?.disconnect()
  controls?.dispose()
  scene?.traverse(object => {
    object.geometry?.dispose()
    if (Array.isArray(object.material)) object.material.forEach(material => material.dispose())
    else object.material?.dispose()
  })
  renderer?.dispose()
  renderer?.domElement?.remove()
  scene = null
  renderer = null
  controls = null
})
</script>

<style scoped>
.joint-view { display: flex; width: 100%; height: 100%; min-width: 0; min-height: 0; flex: 1 1 auto; flex-direction: column; }
.joint-scene-host { box-sizing: border-box; position: relative; width: 100%; min-width: 0; flex: 1; min-height: 260px; overflow: hidden; border: 1px solid rgba(83, 159, 186, 0.25); border-radius: 9px; background: #081421; }
.joint-scene-host :deep(canvas) { display: block; width: 100%; height: 100%; }
.joint-scene-error { display: grid; width: 100%; height: 100%; min-height: 260px; place-items: center; padding: 18px; color: #91aaba; font-size: 11px; text-align: center; }
</style>
