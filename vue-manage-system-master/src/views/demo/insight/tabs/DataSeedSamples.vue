<template>
    <div class="seed-panel">
        <el-alert
            :title="t('pages.insight.seed.samplesHint')"
            type="info"
            show-icon
            :closable="false"
            class="mgb20"
        />

        <el-form label-width="120px" class="seed-form">
            <el-form-item :label="t('pages.insight.seed.preset')">
                <el-radio-group v-model="preset">
                    <el-radio-button v-for="item in presets" :key="item.key" :value="item.key">
                        {{ item.key }} ({{ formatBatch(item.complaints) }})
                    </el-radio-button>
                </el-radio-group>
            </el-form-item>
            <el-form-item>
                <el-button type="primary" :loading="loading" @click="handleSeed">
                    {{ t('pages.insight.seed.startSamples') }}
                </el-button>
                <el-button :loading="previewing" @click="handlePreview">
                    {{ t('pages.insight.seed.preview') }}
                </el-button>
                <el-button :loading="resetting" @click="handleReset">
                    {{ t('pages.insight.seed.resetSamples') }}
                </el-button>
            </el-form-item>
        </el-form>

        <el-result v-if="result" icon="success" :title="t('pages.insight.seed.done')">
            <template #sub-title>
                {{ t('pages.insight.seed.samplesDone', {
                    complaints: result.complaints_inserted,
                    touchpoints: result.touchpoints_inserted,
                    ms: result.elapsed_ms,
                }) }}
            </template>
        </el-result>

        <el-divider v-if="previews.length">{{ t('pages.insight.seed.previewTitle') }}</el-divider>
        <el-card v-for="(item, idx) in previews" :key="idx" shadow="never" class="preview-card">
            <div class="preview-meta">
                <el-tag size="small">{{ item.main_category }}</el-tag>
                <el-tag size="small" type="warning">{{ item.sub_category }}</el-tag>
            </div>
            <p class="preview-text">{{ item.raw_text }}</p>
            <div class="preview-len">{{ item.raw_text.length }} {{ t('pages.insight.seed.chars') }}</div>
        </el-card>

        <el-tabs class="sample-tabs" type="border-card">
            <el-tab-pane label="问卷投诉样本">
                <TouchpointManager :key="sampleTableKey" @refresh="emit('refresh')" />
            </el-tab-pane>
            <el-tab-pane label="投诉样本">
                <ComplaintManager :key="sampleTableKey" @refresh="emit('refresh')" />
            </el-tab-pane>
        </el-tabs>
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { getInsightSeedPresets, getInsightSeedPreview, postInsightSeedResetSamples, postInsightSeedSamples } from '@/api';
import ComplaintManager from './ComplaintManager.vue';
import TouchpointManager from './TouchpointManager.vue';

defineProps<{ status: { users: number } }>();
const emit = defineEmits<{ refresh: [] }>();
const { t } = useI18n();

type Preset = 'mini' | 'dev' | 'demo' | 'full';
interface PresetInfo {
    key: Preset;
    users: number;
    complaints: number;
    touchpoints: number;
}
interface PreviewItem {
    main_category: string;
    sub_category: string;
    raw_text: string;
}

const preset = ref<Preset>('demo');
const loading = ref(false);
const previewing = ref(false);
const resetting = ref(false);
const presets = ref<PresetInfo[]>([]);
const result = ref<{ complaints_inserted: number; touchpoints_inserted: number; elapsed_ms: number } | null>(null);
const previews = ref<PreviewItem[]>([]);
const sampleTableKey = ref(0);

function formatBatch(n: number) {
    const value = n >= 10000 ? `${Math.round(n / 10000)}万` : String(n);
    return `+${value}`;
}

async function loadPresets() {
    const { data } = await getInsightSeedPresets();
    presets.value = data as PresetInfo[];
}

async function handleSeed() {
    loading.value = true;
    result.value = null;
    try {
        const { data } = await postInsightSeedSamples(preset.value);
        result.value = data as typeof result.value;
        ElMessage.success(t('pages.insight.seed.done'));
        sampleTableKey.value += 1;
        emit('refresh');
    } finally {
        loading.value = false;
    }
}

async function handlePreview() {
    previewing.value = true;
    try {
        const { data } = await getInsightSeedPreview(3);
        previews.value = (data as { items: PreviewItem[] }).items;
    } finally {
        previewing.value = false;
    }
}

async function handleReset() {
    await ElMessageBox.confirm(t('pages.insight.seed.resetSamplesConfirm'), t('common.delete'), { type: 'warning' });
    resetting.value = true;
    try {
        await postInsightSeedResetSamples();
        result.value = null;
        previews.value = [];
        ElMessage.success(t('pages.insight.seed.resetDone'));
        sampleTableKey.value += 1;
        emit('refresh');
    } catch (error: unknown) {
        const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(detail || t('pages.insight.seed.resetSamplesFailed'));
    } finally {
        resetting.value = false;
    }
}

onMounted(loadPresets);
</script>

<style scoped>
.seed-form {
    max-width: 720px;
}
.mgb20 {
    margin-bottom: 20px;
}
.preview-card {
    margin-bottom: 12px;
}
.preview-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
}
.preview-text {
    margin: 0;
    line-height: 1.7;
    color: var(--el-text-color-primary);
}
.preview-len {
    margin-top: 8px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
}
.sample-tabs {
    margin-top: 20px;
}
</style>
