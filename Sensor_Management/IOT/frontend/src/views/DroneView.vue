<template>
  <div class="drone-page">

    <div class="header">
      <h2>无人机实时图传</h2>

      <div class="status">
        <span :class="{ live: isPlaying }"></span>
        {{ statusText }}
      </div>
    </div>

    <div class="video-wrapper">
      <video
        ref="videoEl"
        autoplay
        muted
        playsinline
        class="video"
      ></video>

      <div v-if="!isPlaying" class="placeholder">
        点击连接开始 WebRTC 图传
      </div>
    </div>

    <div class="controls">
      <button @click="toggle">
        {{ isPlaying ? "断开" : "连接" }}
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from "vue"

const videoEl = ref(null)
const isPlaying = ref(false)
const statusText = ref("未连接")

let pc = null
let reconnectTimer = null
let iceTimer = null

const STREAM_URL = "http://192.168.0.242:8889/drone/whep"

function logStatus(msg) {
  statusText.value = msg
  console.log("[WebRTC]", msg)
}

async function createPeer() {
  pc = new RTCPeerConnection({
    iceServers: []
  })

  pc.addTransceiver("video", { direction: "recvonly" })

  pc.ontrack = (event) => {
    logStatus("收到视频流")
    videoEl.value.srcObject = event.streams[0]
  }

  pc.onconnectionstatechange = () => {
    logStatus("连接状态: " + pc.connectionState)

    if (pc.connectionState === "failed" || pc.connectionState === "disconnected") {
      reconnect()
    }
  }

  pc.oniceconnectionstatechange = () => {
    logStatus("ICE: " + pc.iceConnectionState)

    if (pc.iceConnectionState === "failed") {
      reconnect()
    }
  }

  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)

  const res = await fetch(STREAM_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/sdp"
    },
    body: offer.sdp
  })

  if (!res.ok) throw new Error("SDP failed")

  const answer = await res.text()
  await pc.setRemoteDescription({
    type: "answer",
    sdp: answer
  })

  logStatus("已连接")
}

async function start() {
  try {
    isPlaying.value = true
    await createPeer()
  } catch (e) {
    console.error(e)
    logStatus("连接失败，重试中...")
    reconnect()
  }
}

function stop() {
  isPlaying.value = false

  if (pc) {
    pc.close()
    pc = null
  }

  if (videoEl.value) {
    videoEl.value.srcObject = null
  }

  clearTimeout(reconnectTimer)
}

function reconnect() {
  stop()

  reconnectTimer = setTimeout(() => {
    logStatus("重连中...")
    start()
  }, 1500)
}

function toggle() {
  isPlaying.value ? stop() : start()
}

onBeforeUnmount(() => stop())
</script>

<style scoped>
.video {
  width: 100%;
  height: 400px;
  background: black;
  object-fit: contain;
}

.placeholder {
  color: #999;
  text-align: center;
  padding: 40px;
}

.status span {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: gray;
  margin-right: 6px;
}

.status .live {
  background: green;
}
</style>