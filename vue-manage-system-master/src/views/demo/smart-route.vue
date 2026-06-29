<template>
    <div class="container smart-route-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.smartRoute.title') }}</span>
                    <FeatureIntroIcon
                        page-key="smart-route"
                        section-key="page"
                        :intros="intros"
                        :title="t('pages.smartRoute.title')"
                        @saved="setIntro"
                    />
                </div>
            </template>

            <div class="quick-section">
                <div class="section-label">{{ t('pages.smartRoute.quickAsk') }}</div>
                <div class="quick-buttons">
                    <el-button
                        v-for="item in quickQuestions"
                        :key="item"
                        :disabled="loading"
                        @click="handleQuick(item)"
                    >
                        {{ item }}
                    </el-button>
                </div>
            </div>

            <div class="input-section">
                <div class="section-label">{{ t('pages.smartRoute.customQuestion') }}</div>
                <el-input
                    v-model="question"
                    type="textarea"
                    :rows="3"
                    :placeholder="t('pages.smartRoute.placeholder')"
                    :disabled="loading"
                    @keydown.ctrl.enter="handleDispatch"
                />
                <div class="action-bar">
                    <el-button type="primary" :loading="loading" :disabled="!question.trim()" @click="handleDispatch">
                        {{ t('pages.smartRoute.dispatch') }}
                    </el-button>
                    <el-button :disabled="loading || !question" @click="handleClear">{{ t('common.clear') }}</el-button>
                </div>
            </div>

            <el-divider />

            <div class="output-section">
                <div class="section-label">{{ t('pages.smartRoute.result') }}</div>
                <div v-if="routeMessage" class="result-box">
                    <el-tag v-if="routeIntent" :type="intentTagType" size="small" class="intent-tag">
                        {{ intentLabel }}
                    </el-tag>
                    <span class="route-message">{{ routeMessage }}</span>
                </div>
                <div v-if="routeEmployees.length" class="employee-list">
                    <div v-for="item in routeEmployees" :key="item.user_id" class="employee-card">
                        <el-avatar :size="72" :src="getEmployeePhotoUrl(item)" class="employee-avatar">
                            {{ item.user_id.slice(0, 1) }}
                        </el-avatar>
                        <div class="employee-info">
                            <div class="employee-name">{{ item.user_id }}</div>
                            <div class="employee-meta">{{ t('pages.smartRoute.registeredAt') }}{{ formatDateTime(item.created_at) }}</div>
                            <div class="employee-meta">{{ t('pages.smartRoute.punchCount') }}{{ item.punch_count }}</div>
                            <div class="employee-meta">
                                {{ t('pages.smartRoute.lastPunch') }}{{ item.last_punch_at ? formatDateTime(item.last_punch_at) : t('common.none') }}
                            </div>
                        </div>
                    </div>
                </div>
                <el-empty v-if="!routeMessage && !routeEmployees.length" :description="t('pages.smartRoute.empty')" :image-size="80" />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-smart-route">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';
import { useCachedRef } from '@/composables/useFormCache';
import { smartRouteDispatch } from '@/api';
import { loadAttendancePersonPhoto } from '@/utils/authPhoto';

const { t, tm, locale } = useI18n();
const { intros, setIntro } = useFeatureIntros('smart-route');

interface SmartRouteEmployee {
    user_id: string;
    created_at: string;
    punch_count: number;
    has_reference_image: boolean;
    photo_url: string | null;
    last_punch_at: string | null;
}

const quickQuestions = computed(() => tm('pages.smartRoute.quickQuestions') as string[]);

const question = useCachedRef('smart-route:question', '');
const routeMessage = ref('');
const routeIntent = ref('');
const routeEmployees = ref<SmartRouteEmployee[]>([]);
const employeePhotoUrls = ref<Record<string, string>>({});
const loading = ref(false);

const intentMap = computed(() => ({
    weather: { label: t('pages.smartRoute.intentWeather'), type: 'success' as const },
    employee: { label: t('pages.smartRoute.intentEmployee'), type: 'warning' as const },
    email: { label: t('pages.smartRoute.intentEmail'), type: 'info' as const },
    unknown: { label: t('pages.smartRoute.intentUnknown'), type: 'danger' as const },
}));

const intentLabel = computed(() => intentMap.value[routeIntent.value as keyof typeof intentMap.value]?.label ?? routeIntent.value);
const intentTagType = computed(() => intentMap.value[routeIntent.value as keyof typeof intentMap.value]?.type ?? 'info');

void locale;

const formatDateTime = (value: string) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

const getEmployeePhotoUrl = (item: SmartRouteEmployee) =>
    item.has_reference_image ? employeePhotoUrls.value[item.user_id] || '' : '';

const syncEmployeePhotos = async () => {
    await Promise.all(
        routeEmployees.value
            .filter((item) => item.has_reference_image)
            .map(async (item) => {
                try {
                    employeePhotoUrls.value[item.user_id] = await loadAttendancePersonPhoto(item.user_id);
                } catch {
                    delete employeePhotoUrls.value[item.user_id];
                }
            }),
    );
};

const handleDispatch = async () => {
    const q = question.value.trim();
    if (!q) return;

    loading.value = true;
    routeMessage.value = '';
    routeIntent.value = '';
    routeEmployees.value = [];
    employeePhotoUrls.value = {};
    try {
        const res = await smartRouteDispatch({ question: q });
        const data = res.data as {
            message?: string;
            intent?: string;
            employees?: SmartRouteEmployee[];
        };
        routeMessage.value = data.message ?? '';
        routeIntent.value = data.intent ?? '';
        routeEmployees.value = Array.isArray(data.employees) ? data.employees : [];
        await syncEmployeePhotos();
    } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(typeof msg === 'string' ? msg : '路由判断失败，请稍后重试');
    } finally {
        loading.value = false;
    }
};

const handleQuick = (text: string) => {
    question.value = text;
    handleDispatch();
};

const handleClear = () => {
    question.value = '';
    routeMessage.value = '';
    routeIntent.value = '';
    routeEmployees.value = [];
    employeePhotoUrls.value = {};
};
</script>

<style scoped>
.smart-route-page .page-header {
    display: inline-flex;
    align-items: center;
}

.smart-route-page .page-title {
    font-size: 16px;
    font-weight: 600;
}

.section-label {
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 500;
}

.quick-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.input-section {
    margin-top: 20px;
}

.action-bar {
    margin-top: 12px;
    display: flex;
    gap: 8px;
}

.result-box {
    min-height: 80px;
    padding: 16px;
    border: 1px solid var(--el-border-color-light);
    border-radius: 4px;
    background: var(--el-fill-color-blank);
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 16px;
}

.route-message {
    font-weight: 500;
}

.employee-list {
    margin-top: 16px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
}

.employee-card {
    display: flex;
    gap: 14px;
    padding: 16px;
    border: 1px solid var(--el-border-color-light);
    border-radius: 8px;
    background: var(--el-fill-color-blank);
}

.employee-avatar {
    flex-shrink: 0;
}

.employee-name {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 8px;
}

.employee-meta {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    line-height: 1.6;
}
</style>
