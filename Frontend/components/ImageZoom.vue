<template>
  <img 
    ref="imgRef" 
    :src="src" 
    :alt="alt" 
    class="zoomable-image"
  />
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import mediumZoom from 'medium-zoom'

const props = defineProps({
  src: { type: String, required: true },
  alt: { type: String, default: '' },
  options: { type: Object, default: () => ({}) }
})

const imgRef = ref(null)
let zoom = null

onMounted(() => {
  // 初始化 medium-zoom
  // background: 設定背景遮罩顏色
  // margin: 圖片放大後保留的邊距
  zoom = mediumZoom(imgRef.value, {
    background: 'rgba(0, 0, 0, 0.6)',
    margin: 24,
    ...props.options
  })
})

// 當圖片來源改變時 (例如切換聊天室)，重新 attach
watch(() => props.src, () => {
  if (zoom) {
    zoom.detach()
    zoom.attach(imgRef.value)
  }
})

onUnmounted(() => {
  if (zoom) zoom.detach()
})
</script>

<style scoped>
.zoomable-image {
  /* 這裡可以放原本圖片的樣式，例如圓角、大小限制 */
  max-width: 100%;
  min-width: 100px;
  max-height: 300px;
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
  cursor: zoom-in;
}
</style>