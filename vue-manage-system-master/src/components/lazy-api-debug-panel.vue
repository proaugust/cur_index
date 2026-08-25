<template>
    <el-skeleton v-if="!ready" :rows="5" animated class="lazy-panel-skeleton" />
    <Suspense v-else>
        <ApiDebugPanel
            :endpoints="visibleEndpoints"
            :intro-page-key="introPageKey"
            :intros="intros"
            @intro-saved="(key, content) => emit('intro-saved', key, content)"
        >
            <template v-for="(_, name) in $slots" :key="name" #[name]="slotProps">
                <slot :name="name" v-bind="slotProps || {}" />
            </template>
        </ApiDebugPanel>
        <template #fallback>
            <el-skeleton :rows="5" animated class="lazy-panel-skeleton" />
        </template>
    </Suspense>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import type { ApiEndpoint } from '@/config/api-endpoints';
import type { FeatureIntroMap } from '@/composables/useFeatureIntros';
import { usePermissStore } from '@/store/permiss';

const props = defineProps<{
    endpointKey: 'complaint' | 'document' | 'corpora' | 'chat';
    introPageKey?: string;
    intros?: FeatureIntroMap;
}>();

const emit = defineEmits<{
    'intro-saved': [sectionKey: string, content: string];
}>();

const MENU_CODE_MAP: Record<typeof props.endpointKey, string> = {
    complaint: '81',
    document: '82',
    corpora: '82',
    chat: '83',
};

const { t, te, locale } = useI18n();
const permiss = usePermissStore();

const ApiDebugPanel = defineAsyncComponent(() => import('@/components/api-debug-panel.vue'));

const endpoints = ref<ApiEndpoint[]>([]);
const ready = ref(false);

const menuCode = computed(() => MENU_CODE_MAP[props.endpointKey]);

const visibleEndpoints = computed(() => {
    const filtered = endpoints.value.filter((ep) => permiss.hasApi(menuCode.value, ep.id));
    if (filtered.length) return filtered;
    // 有页面权限但本地 API 码未同步时，仍展示调试面板（后端会再鉴权）
    return permiss.hasRoutePermiss(menuCode.value) ? endpoints.value : [];
});

const loadEndpoints = async () => {
    try {
        const mod = await import('@/config/api-endpoints');
        const map: Record<typeof props.endpointKey, ApiEndpoint[]> = {
            complaint: mod.complaintEndpoints,
            document: mod.getDocumentEndpoints((key) => String(t(key)), te),
            corpora: mod.getCorporaEndpoints((key) => String(t(key)), te),
            chat: mod.chatEndpoints,
        };
        endpoints.value = map[props.endpointKey];
    } catch (err) {
        console.error('加载接口列表失败', err);
        endpoints.value = [];
    } finally {
        ready.value = true;
    }
};

onMounted(loadEndpoints);
watch(() => locale.value, loadEndpoints);
</script>

<style scoped>
.lazy-panel-skeleton {
    margin-bottom: 20px;
}
</style>
