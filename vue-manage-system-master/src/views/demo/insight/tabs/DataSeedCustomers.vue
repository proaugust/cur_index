<template>
    <div class="seed-panel">
        <el-alert
            :title="t('pages.insight.seed.customersHint')"
            type="info"
            show-icon
            :closable="false"
            class="mgb20"
        />
        <el-alert
            title="只追加客户。user_id 按客户/样本两边最大值续号；勿与「注入样本」同时进行。合并样本 = 插入尚未存在的 user_id（1 样本 = 1 客户，带真值）"
            type="success"
            show-icon
            :closable="false"
            class="mgb20"
        />

        <el-form label-width="120px" class="seed-form">
            <el-form-item :label="t('pages.insight.seed.preset')">
                <div class="preset-row">
                    <el-radio-group v-model="preset">
                        <el-radio-button v-for="item in presets" :key="item.key" :value="item.key">
                            {{ item.key }} ({{ formatBatch(item.users) }})
                        </el-radio-button>
                    </el-radio-group>
                    <span class="count-label">{{ t('pages.insight.seed.count') }}</span>
                    <el-input
                        v-model="countText"
                        clearable
                        style="width: 240px"
                        :placeholder="countPlaceholder"
                    />
                </div>
            </el-form-item>
            <el-form-item>
                <el-button type="primary" :loading="loading" @click="handleSeed">
                    {{ t('pages.insight.seed.startCustomers') }}
                </el-button>
                <el-button type="success" :loading="promoting" @click="handlePromote">
                    合并样本到客户
                </el-button>
                <el-button :loading="resetting" @click="handleReset">
                    {{ t('pages.insight.seed.resetCustomers') }}
                </el-button>
            </el-form-item>
        </el-form>

        <el-result v-if="result" icon="success" :title="t('pages.insight.seed.done')">
            <template #sub-title>
                <template v-if="result.kind === 'seed'">
                    {{ t('pages.insight.seed.inserted', { count: result.inserted, ms: result.elapsed_ms }) }}
                </template>
                <template v-else>
                    样本合并完成：升客户 {{ result.profiles_upserted }} 名（样本 {{ result.samples_merged }} 条），耗时 {{ result.elapsed_ms }} ms
                </template>
            </template>
        </el-result>

        <CustomerManager :key="customerTableKey" @refresh="emit('refresh')" />
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import {
    getInsightSeedPresets,
    postInsightSeedPromoteSamples,
    postInsightSeedUsers,
    postInsightSeedResetUsers,
} from '@/api';
import CustomerManager from './CustomerManager.vue';

interface SeedStatus {
    users: number;
    samples: number;
    snapshots: number;
}

defineProps<{
    status: SeedStatus;
}>();
const emit = defineEmits<{ refresh: [] }>();
const { t } = useI18n();

type Preset = 'mini' | 'dev' | 'demo' | 'full';
interface PresetInfo {
    key: Preset;
    users: number;
    complaints: number;
    touchpoints: number;
}

type SeedResult =
    | { kind: 'seed'; inserted: number; elapsed_ms: number }
    | { kind: 'promote'; samples_merged: number; profiles_upserted: number; elapsed_ms: number };

const preset = ref<Preset>('demo');
const countText = ref('');
const loading = ref(false);
const promoting = ref(false);
const resetting = ref(false);
const presets = ref<PresetInfo[]>([]);
const result = ref<SeedResult | null>(null);
const customerTableKey = ref(0);

const countPlaceholder = computed(() => {
    const found = presets.value.find((item) => item.key === preset.value);
    return found ? `可空，空则追加 ${found.users} 条` : '可空，空则用上方规模';
});

function formatBatch(n: number) {
    const value = n >= 10000 ? `${Math.round(n / 10000)}万` : String(n);
    return `+${value}`;
}

async function loadPresets() {
    const { data } = await getInsightSeedPresets();
    presets.value = data as PresetInfo[];
}

async function handleSeed() {
    const raw = countText.value.trim();
    let count: number;
    if (raw) {
        const n = Number(raw);
        if (!Number.isInteger(n) || n < 1 || n > 500000) {
            ElMessage.warning('追加条数须为 1～500000 的整数');
            return;
        }
        count = n;
    } else {
        const found = presets.value.find((item) => item.key === preset.value);
        count = found?.users ?? 100;
    }
    loading.value = true;
    result.value = null;
    try {
        const { data } = await postInsightSeedUsers(preset.value, count);
        result.value = { kind: 'seed', ...(data as { inserted: number; elapsed_ms: number }) };
        ElMessage.success(t('pages.insight.seed.done'));
        customerTableKey.value += 1;
        emit('refresh');
    } catch (error: unknown) {
        const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(detail || t('pages.insight.seed.seedCustomersFailed'));
    } finally {
        loading.value = false;
    }
}

async function handlePromote() {
    promoting.value = true;
    result.value = null;
    try {
        const { data } = await postInsightSeedPromoteSamples();
        const payload = data as {
            samples_merged: number;
            profiles_upserted: number;
            elapsed_ms: number;
        };
        result.value = { kind: 'promote', ...payload };
        customerTableKey.value += 1;
        emit('refresh');
    } catch (error: unknown) {
        const err = error as {
            code?: string;
            message?: string;
            response?: { data?: { detail?: string } };
        };
        const detail = err?.response?.data?.detail;
        const timedOut = err?.code === 'ECONNABORTED' || /timeout/i.test(err?.message || '');
        ElMessage.error(
            detail || (timedOut ? '合并样本超时（请到「AI 洞察」批处理运行日志查看是否已完成）' : '合并样本到客户失败')
        );
    } finally {
        promoting.value = false;
    }
}

async function handleReset() {
    await ElMessageBox.confirm(t('pages.insight.seed.resetCustomersConfirm'), t('common.delete'), { type: 'warning' });
    resetting.value = true;
    try {
        await postInsightSeedResetUsers();
        result.value = null;
        ElMessage.success(t('pages.insight.seed.resetDone'));
        customerTableKey.value += 1;
        emit('refresh');
    } catch (error: unknown) {
        const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(detail || t('pages.insight.seed.resetCustomersFailed'));
    } finally {
        resetting.value = false;
    }
}

onMounted(loadPresets);
</script>

<style scoped>
.seed-form {
    max-width: 960px;
}
.preset-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
}
.count-label {
    color: var(--el-text-color-regular);
    white-space: nowrap;
}
.mgb20 {
    margin-bottom: 20px;
}
</style>
