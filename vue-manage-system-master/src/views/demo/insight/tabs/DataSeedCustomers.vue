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
            v-if="!canResetCustomers"
            :title="t('pages.insight.seed.resetCustomersBlocked')"
            type="warning"
            show-icon
            :closable="false"
            class="mgb20"
        />

        <el-form label-width="120px" class="seed-form">
            <el-form-item :label="t('pages.insight.seed.preset')">
                <el-radio-group v-model="preset">
                    <el-radio-button v-for="item in presets" :key="item.key" :value="item.key">
                        {{ item.key }} ({{ formatBatch(item.users) }})
                    </el-radio-button>
                </el-radio-group>
            </el-form-item>
            <el-form-item>
                <el-button type="primary" :loading="loading" @click="handleSeed">
                    {{ t('pages.insight.seed.startCustomers') }}
                </el-button>
                <el-button
                    :loading="resetting"
                    :disabled="!canResetCustomers"
                    @click="handleReset"
                >
                    {{ t('pages.insight.seed.resetCustomers') }}
                </el-button>
            </el-form-item>
        </el-form>

        <el-result v-if="result" icon="success" :title="t('pages.insight.seed.done')">
            <template #sub-title>
                {{ t('pages.insight.seed.inserted', { count: result.inserted, ms: result.elapsed_ms }) }}
            </template>
        </el-result>

        <CustomerManager :key="customerTableKey" @refresh="emit('refresh')" />
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { getInsightSeedPresets, postInsightSeedUsers, postInsightSeedResetUsers } from '@/api';
import CustomerManager from './CustomerManager.vue';

interface SeedStatus {
    users: number;
    samples: number;
    snapshots: number;
}

const props = defineProps<{
    status: SeedStatus;
}>();
const emit = defineEmits<{ refresh: [] }>();
const { t } = useI18n();

const canResetCustomers = computed(
    () => props.status.samples === 0 && props.status.snapshots === 0
);

type Preset = 'mini' | 'dev' | 'demo' | 'full';
interface PresetInfo {
    key: Preset;
    users: number;
    complaints: number;
    touchpoints: number;
}

const preset = ref<Preset>('demo');
const loading = ref(false);
const resetting = ref(false);
const presets = ref<PresetInfo[]>([]);
const result = ref<{ inserted: number; elapsed_ms: number } | null>(null);
const customerTableKey = ref(0);

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
        const { data } = await postInsightSeedUsers(preset.value);
        result.value = data as { inserted: number; elapsed_ms: number };
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

async function handleReset() {
    if (!canResetCustomers.value) {
        ElMessage.warning(t('pages.insight.seed.needClearSamplesFirst'));
        return;
    }
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
    max-width: 720px;
}
.mgb20 {
    margin-bottom: 20px;
}
</style>
