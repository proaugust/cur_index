<template>
    <el-skeleton v-if="!ready" :rows="5" animated class="lazy-panel-skeleton" />
    <Suspense v-else>
        <ApiDebugPanel :endpoints="endpoints" />
        <template #fallback>
            <el-skeleton :rows="5" animated class="lazy-panel-skeleton" />
        </template>
    </Suspense>
</template>

<script setup lang="ts">
import { defineAsyncComponent, onMounted, ref } from 'vue';
import type { ApiEndpoint } from '@/config/api-endpoints';

const props = defineProps<{
    endpointKey: 'complaint' | 'document' | 'chat';
}>();

const ApiDebugPanel = defineAsyncComponent(() => import('@/components/api-debug-panel.vue'));

const endpoints = ref<ApiEndpoint[]>([]);
const ready = ref(false);

onMounted(async () => {
    const mod = await import('@/config/api-endpoints');
    const map = {
        complaint: mod.complaintEndpoints,
        document: mod.documentEndpoints,
        chat: mod.chatEndpoints,
    };
    endpoints.value = map[props.endpointKey];
    ready.value = true;
});
</script>

<style scoped>
.lazy-panel-skeleton {
    margin-bottom: 20px;
}
</style>
